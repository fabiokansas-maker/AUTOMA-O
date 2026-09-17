-- =====================================================================
-- Kansas IA Financeira — RLS + API estreita (migration ADITIVA)
--
-- Regra que este arquivo implementa e o teste prova:
--   "O modelo de IA NÃO é a barreira de segurança."
--   Nenhuma policy consulta prompt, nome de agente vindo do cliente ou
--   metadata enviada pelo app. Só auth.uid() (JWT) e o GUC do backend.
-- =====================================================================

alter table kansas.agents                    enable row level security;
alter table kansas.agent_threads             enable row level security;
alter table kansas.agent_messages            enable row level security;
alter table kansas.agent_memories            enable row level security;
alter table kansas.shared_user_facts         enable row level security;
alter table kansas.agent_events              enable row level security;
alter table kansas.agent_feedback            enable row level security;
alter table kansas.account_deletion_requests enable row level security;
alter table kansas.audit_events              enable row level security;

-- Registry: leitura para usuário logado, escrita só backend (service_role).
drop policy if exists agents_read on kansas.agents;
create policy agents_read on kansas.agents
  for select to authenticated
  using (enabled);

-- ---------------------------------------------------------------------
-- THREADS — fronteira de usuário + fronteira de agente
-- ---------------------------------------------------------------------
drop policy if exists threads_rw on kansas.agent_threads;
create policy threads_rw on kansas.agent_threads
  for all to authenticated
  using (
    auth.uid() is not null
    and auth.uid() = user_id
    and (kansas.current_agent() is null or kansas.current_agent() = agent_id)
  )
  with check (
    auth.uid() is not null
    and auth.uid() = user_id
    and (kansas.current_agent() is null or kansas.current_agent() = agent_id)
  );

-- ---------------------------------------------------------------------
-- MENSAGENS — idem. Conversa de um agente não vaza para outro.
-- ---------------------------------------------------------------------
drop policy if exists messages_rw on kansas.agent_messages;
create policy messages_rw on kansas.agent_messages
  for all to authenticated
  using (
    auth.uid() is not null
    and auth.uid() = user_id
    and (kansas.current_agent() is null or kansas.current_agent() = agent_id)
  )
  with check (
    auth.uid() is not null
    and auth.uid() = user_id
    and (kansas.current_agent() is null or kansas.current_agent() = agent_id)
  );

-- ---------------------------------------------------------------------
-- MEMÓRIA PRIVADA — aqui a fronteira de agente é OBRIGATÓRIA.
-- Sem agente setado, ninguém lê memória privada de ninguém.
-- ---------------------------------------------------------------------
drop policy if exists memories_rw on kansas.agent_memories;
create policy memories_rw on kansas.agent_memories
  for all to authenticated
  using (
    auth.uid() is not null
    and auth.uid() = user_id
    and kansas.current_agent() is not null
    and kansas.current_agent() = agent_id
    and (expires_at is null or expires_at > now())
  )
  with check (
    auth.uid() is not null
    and auth.uid() = user_id
    and kansas.current_agent() is not null
    and kansas.current_agent() = agent_id
    -- só escreve dentro do escopo declarado no registry
    and exists (
      select 1 from kansas.agents a
      where a.id = kansas.current_agent()
        and (a.writable_memory_scope = '{}' or key = any(a.writable_memory_scope))
    )
  );

-- ---------------------------------------------------------------------
-- FATOS COMPARTILHADOS — leitura filtrada pelo allowlist do agente.
-- O agente de Faturas não enxerga um fato que o registry não liberou.
-- ---------------------------------------------------------------------
drop policy if exists shared_facts_read on kansas.shared_user_facts;
create policy shared_facts_read on kansas.shared_user_facts
  for select to authenticated
  using (
    auth.uid() is not null
    and auth.uid() = user_id
    and (expires_at is null or expires_at > now())
    and (
      kansas.current_agent() is null   -- contexto de Configurações do app
      or exists (
        select 1 from kansas.agents a
        where a.id = kansas.current_agent()
          and key = any(a.readable_shared_keys)
      )
    )
  );

-- Escrita de fato compartilhado: só fora de contexto de agente
-- (tela de preferências do usuário) ou pelo backend.
drop policy if exists shared_facts_write on kansas.shared_user_facts;
create policy shared_facts_write on kansas.shared_user_facts
  for all to authenticated
  using (auth.uid() is not null and auth.uid() = user_id and kansas.current_agent() is null)
  with check (auth.uid() is not null and auth.uid() = user_id and kansas.current_agent() is null);

-- ---------------------------------------------------------------------
-- EVENTOS — o agente só lê o que foi endereçado a ele.
-- ---------------------------------------------------------------------
drop policy if exists events_read on kansas.agent_events;
create policy events_read on kansas.agent_events
  for select to authenticated
  using (
    auth.uid() is not null
    and auth.uid() = user_id
    and (expires_at is null or expires_at > now())
    and kansas.current_agent() is not null
    and kansas.current_agent() = any(visible_to)
  );

drop policy if exists events_write on kansas.agent_events;
create policy events_write on kansas.agent_events
  for insert to authenticated
  with check (
    auth.uid() is not null
    and auth.uid() = user_id
    and kansas.current_agent() is not null
    and kansas.current_agent() = source_agent
  );

-- ---------------------------------------------------------------------
-- FEEDBACK / DENÚNCIA e EXCLUSÃO DE CONTA
-- ---------------------------------------------------------------------
drop policy if exists feedback_rw on kansas.agent_feedback;
create policy feedback_rw on kansas.agent_feedback
  for all to authenticated
  using (auth.uid() is not null and auth.uid() = user_id)
  with check (auth.uid() is not null and auth.uid() = user_id);

drop policy if exists deletion_rw on kansas.account_deletion_requests;
create policy deletion_rw on kansas.account_deletion_requests
  for all to authenticated
  using (auth.uid() is not null and auth.uid() = user_id)
  with check (auth.uid() is not null and auth.uid() = user_id);

-- audit_events: sem policy para `authenticated` = ninguém lê pelo cliente.
-- Só service_role (que faz bypass de RLS) grava e lê.

-- ---------------------------------------------------------------------
-- GRANTS — o cliente nunca recebe DDL nem SQL livre
-- ---------------------------------------------------------------------
grant usage on schema kansas to authenticated, service_role;
grant select on kansas.agents to authenticated;
grant select, insert, update, delete on
  kansas.agent_threads, kansas.agent_messages, kansas.agent_memories,
  kansas.shared_user_facts, kansas.agent_feedback,
  kansas.account_deletion_requests to authenticated;
grant select, insert on kansas.agent_events to authenticated;
grant all on all tables in schema kansas to service_role;
grant usage, select on all sequences in schema kansas to service_role;

-- ---------------------------------------------------------------------
-- API ESTREITA (SECURITY INVOKER: roda sob as policies acima de propósito)
-- ---------------------------------------------------------------------

-- Fatos compartilhados que ESTE agente pode ver, já achatados.
create or replace function kansas.shared_facts()
returns jsonb
language sql
stable
security invoker
as $$
  select coalesce(jsonb_object_agg(key, value_json), '{}'::jsonb)
  from kansas.shared_user_facts
$$;

-- Memória privada do agente corrente, já sem o que expirou.
create or replace function kansas.recall()
returns jsonb
language sql
stable
security invoker
as $$
  select coalesce(jsonb_object_agg(key, value_json), '{}'::jsonb)
  from kansas.agent_memories
$$;

-- Grava um fato na memória privada do agente corrente.
create or replace function kansas.remember(
  p_key text,
  p_value jsonb,
  p_sensitivity text default 'normal',
  p_ttl interval default null
) returns void
language plpgsql
security invoker
as $$
begin
  insert into kansas.agent_memories
    (user_id, agent_id, key, value_json, sensitivity, expires_at, updated_at)
  values
    (auth.uid(), kansas.current_agent(), p_key, p_value, p_sensitivity,
     case when p_ttl is null then null else now() + p_ttl end, now())
  on conflict (user_id, agent_id, key) do update
    set value_json  = excluded.value_json,
        sensitivity = excluded.sensitivity,
        expires_at  = excluded.expires_at,
        updated_at  = now();
end;
$$;

-- Publica um resumo estruturado para outros agentes.
create or replace function kansas.publish_event(
  p_type text,
  p_payload jsonb,
  p_visible_to text[],
  p_ttl interval default interval '30 days'
) returns uuid
language plpgsql
security invoker
as $$
declare v_id uuid;
begin
  insert into kansas.agent_events
    (user_id, source_agent, type, payload, visible_to, expires_at)
  values
    (auth.uid(), kansas.current_agent(), p_type, p_payload, p_visible_to,
     now() + p_ttl)
  returning id into v_id;
  return v_id;
end;
$$;

-- Eventos endereçados ao agente corrente, filtrados pelos tipos do registry.
create or replace function kansas.inbox(p_limit int default 20)
returns setof kansas.agent_events
language sql
stable
security invoker
as $$
  select e.* from kansas.agent_events e
  join kansas.agents a on a.id = kansas.current_agent()
  where a.readable_event_types = '{}' or e.type = any(a.readable_event_types)
  order by e.created_at desc
  limit greatest(1, least(p_limit, 100))
$$;

-- Apaga TUDO que o usuário tem no núcleo de agentes. Usada pelos três
-- botões do produto: limpar conversa / limpar memória / excluir conta.
create or replace function kansas.purge_user_agent_data(
  p_scope text default 'all',      -- 'threads' | 'memories' | 'all'
  p_agent text default null
) returns jsonb
language plpgsql
security definer
set search_path = kansas, pg_catalog
as $$
declare
  v_uid uuid := auth.uid();
  v_threads int := 0;
  v_mem int := 0;
  v_events int := 0;
  v_shared int := 0;
begin
  if v_uid is null then
    raise exception 'sem usuário autenticado' using errcode = '42501';
  end if;

  if p_scope in ('threads','all') then
    delete from kansas.agent_threads
      where user_id = v_uid and (p_agent is null or agent_id = p_agent);
    get diagnostics v_threads = row_count;
  end if;

  if p_scope in ('memories','all') then
    delete from kansas.agent_memories
      where user_id = v_uid and (p_agent is null or agent_id = p_agent);
    get diagnostics v_mem = row_count;
    delete from kansas.agent_events
      where user_id = v_uid and (p_agent is null or source_agent = p_agent);
    get diagnostics v_events = row_count;
  end if;

  if p_scope = 'all' and p_agent is null then
    delete from kansas.shared_user_facts where user_id = v_uid;
    get diagnostics v_shared = row_count;
    delete from kansas.agent_feedback where user_id = v_uid;
  end if;

  return jsonb_build_object(
    'threads_deleted', v_threads,
    'memories_deleted', v_mem,
    'events_deleted', v_events,
    'shared_facts_deleted', v_shared
  );
end;
$$;

revoke all on function kansas.purge_user_agent_data(text, text) from public;
grant execute on function kansas.purge_user_agent_data(text, text) to authenticated;
-- set_agent é executável por `authenticated` porque o backend TROCA de role
-- (`set local role authenticated`) dentro da própria transação antes de
-- consultar. Quem segura a conexão SQL é só o backend: o schema `kansas`
-- NÃO deve entrar em "Exposed schemas" do Supabase, então o PostgREST não
-- serve nenhuma dessas tabelas para o app. O app fala só com a Edge Function.
grant execute on function kansas.set_agent(text) to authenticated, service_role;
grant execute on function kansas.current_agent() to authenticated, service_role;
grant execute on function kansas.shared_facts() to authenticated;
grant execute on function kansas.recall() to authenticated;
grant execute on function kansas.remember(text, jsonb, text, interval) to authenticated;
grant execute on function kansas.publish_event(text, jsonb, text[], interval) to authenticated;
grant execute on function kansas.inbox(int) to authenticated;
