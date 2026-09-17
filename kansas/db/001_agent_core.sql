-- =====================================================================
-- Kansas IA Financeira — núcleo agent-first (migration ADITIVA)
-- Alvo: PostgreSQL 15+ / Supabase (usa auth.uid() e os roles do Supabase)
--
-- NÃO altera, renomeia ou apaga nenhuma tabela existente.
-- Tudo vive no schema `kansas`. Rollback = DROP SCHEMA kansas CASCADE.
--
-- Duas fronteiras, ambas impostas pelo BANCO (não pelo prompt do LLM):
--   1) fronteira de USUÁRIO  -> auth.uid() = user_id   (vem do JWT, o modelo
--      não escolhe e não consegue forjar)
--   2) fronteira de AGENTE   -> agent_id = kansas.current_agent()
--      (GUC `kansas.agent_id`, setado pelo backend por transação; o cliente
--      não fala SQL direto, só RPC)
-- =====================================================================

create schema if not exists kansas;

-- ---------------------------------------------------------------------
-- Contexto da requisição: qual agente está falando NESTA transação.
-- O backend chama kansas.set_agent('invoices') logo após autenticar.
-- ---------------------------------------------------------------------
create or replace function kansas.current_agent()
returns text
language sql
stable
as $$
  select nullif(current_setting('kansas.agent_id', true), '')
$$;

create or replace function kansas.set_agent(p_agent text)
returns void
language plpgsql
security definer
set search_path = kansas, pg_catalog
as $$
begin
  if p_agent is not null and not exists (
    select 1 from kansas.agents where id = p_agent and enabled
  ) then
    raise exception 'agente desconhecido ou desabilitado: %', p_agent
      using errcode = '42501';
  end if;
  -- `true` = escopo de transação: não vaza para a próxima query do pool
  perform set_config('kansas.agent_id', coalesce(p_agent, ''), true);
end;
$$;

-- ---------------------------------------------------------------------
-- Registro central de agentes. É configuração, não dado de usuário.
-- ---------------------------------------------------------------------
create table if not exists kansas.agents (
  id                      text primary key,
  display_name            text not null,
  description             text not null,
  allowed_tools           text[] not null default '{}',
  allowed_data_domains    text[] not null default '{}',
  readable_shared_keys    text[] not null default '{}',
  writable_memory_scope   text[] not null default '{}',
  readable_event_types    text[] not null default '{}',
  system_instructions     text not null default '',
  enabled                 boolean not null default true,
  updated_at              timestamptz not null default now()
);

-- ---------------------------------------------------------------------
-- Conversas e mensagens
-- ---------------------------------------------------------------------
create table if not exists kansas.agent_threads (
  id           uuid primary key default gen_random_uuid(),
  user_id      uuid not null,
  agent_id     text not null references kansas.agents(id),
  title        text,
  created_at   timestamptz not null default now(),
  updated_at   timestamptz not null default now(),
  archived_at  timestamptz
);
create index if not exists agent_threads_user_agent_idx
  on kansas.agent_threads (user_id, agent_id, updated_at desc);

create table if not exists kansas.agent_messages (
  id          uuid primary key default gen_random_uuid(),
  thread_id   uuid not null references kansas.agent_threads(id) on delete cascade,
  user_id     uuid not null,
  agent_id    text not null references kansas.agents(id),
  role        text not null check (role in ('user','agent','system','tool')),
  -- blocos TIPADOS e validados; o modelo não desenha UI livre
  blocks      jsonb not null default '[]'::jsonb,
  tool_calls  jsonb not null default '[]'::jsonb,
  created_at  timestamptz not null default now()
);
create index if not exists agent_messages_thread_idx
  on kansas.agent_messages (thread_id, created_at);

-- ---------------------------------------------------------------------
-- Memória PRIVADA do agente (user + agent)
-- ---------------------------------------------------------------------
create table if not exists kansas.agent_memories (
  id          uuid primary key default gen_random_uuid(),
  user_id     uuid not null,
  agent_id    text not null references kansas.agents(id),
  key         text not null,
  value_json  jsonb not null,
  source      text not null default 'agent_extraction',
  sensitivity text not null default 'normal'
                check (sensitivity in ('low','normal','high','financial')),
  expires_at  timestamptz,
  updated_at  timestamptz not null default now(),
  unique (user_id, agent_id, key)
);
create index if not exists agent_memories_lookup_idx
  on kansas.agent_memories (user_id, agent_id, key);

-- ---------------------------------------------------------------------
-- Memória COMPARTILHADA — só fatos realmente transversais
-- ---------------------------------------------------------------------
create table if not exists kansas.shared_user_facts (
  id          uuid primary key default gen_random_uuid(),
  user_id     uuid not null,
  key         text not null,
  value_json  jsonb not null,
  source      text not null default 'user_setting',
  confidence  numeric(3,2) not null default 1.00 check (confidence between 0 and 1),
  sensitivity text not null default 'normal'
                check (sensitivity in ('low','normal','high','financial')),
  expires_at  timestamptz,
  updated_at  timestamptz not null default now(),
  unique (user_id, key)
);

-- ---------------------------------------------------------------------
-- Eventos entre agentes: resumo estruturado, nunca a conversa inteira
-- ---------------------------------------------------------------------
create table if not exists kansas.agent_events (
  id           uuid primary key default gen_random_uuid(),
  user_id      uuid not null,
  source_agent text not null references kansas.agents(id),
  type         text not null,
  payload      jsonb not null,
  visible_to   text[] not null default '{}',
  created_at   timestamptz not null default now(),
  expires_at   timestamptz
);
create index if not exists agent_events_user_idx
  on kansas.agent_events (user_id, created_at desc);

-- ---------------------------------------------------------------------
-- Feedback / denúncia de resposta de IA
-- Exigência do Google Play: app que gera conteúdo com IA precisa de
-- mecanismo DENTRO do app para reportar conteúdo ofensivo.
-- ---------------------------------------------------------------------
create table if not exists kansas.agent_feedback (
  id          uuid primary key default gen_random_uuid(),
  user_id     uuid not null,
  message_id  uuid references kansas.agent_messages(id) on delete set null,
  agent_id    text references kansas.agents(id),
  verdict     text not null check (verdict in ('helpful','not_helpful','report')),
  category    text check (category in
                ('incorreto','ofensivo','perigoso','privacidade','outro')),
  reason      text,
  created_at  timestamptz not null default now()
);
create index if not exists agent_feedback_open_reports_idx
  on kansas.agent_feedback (created_at desc) where verdict = 'report';

-- ---------------------------------------------------------------------
-- Exclusão de conta/dados (exigência do Play para apps com conta)
-- ---------------------------------------------------------------------
create table if not exists kansas.account_deletion_requests (
  id            uuid primary key default gen_random_uuid(),
  user_id       uuid not null,
  requested_at  timestamptz not null default now(),
  status        text not null default 'pending'
                  check (status in ('pending','processing','done','failed')),
  completed_at  timestamptz,
  detail        jsonb not null default '{}'::jsonb
);

-- ---------------------------------------------------------------------
-- Trilha de autorização: toda chamada de tool negada fica registrada
-- ---------------------------------------------------------------------
create table if not exists kansas.audit_events (
  id          bigserial primary key,
  user_id     uuid,
  agent_id    text,
  tool        text,
  decision    text not null check (decision in ('allow','deny')),
  reason      text,
  args_digest text,
  created_at  timestamptz not null default now()
);
create index if not exists audit_events_deny_idx
  on kansas.audit_events (created_at desc) where decision = 'deny';
