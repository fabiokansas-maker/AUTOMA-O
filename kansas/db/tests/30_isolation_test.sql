-- =====================================================================
-- Testes de isolamento. Cada teste TENTA DELIBERADAMENTE violar a fronteira.
-- Falha em qualquer um = psql aborta (ON_ERROR_STOP=1) = build vermelho.
-- =====================================================================
\set A '''aaaaaaaa-0000-0000-0000-00000000000a'''
\set B '''bbbbbbbb-0000-0000-0000-00000000000b'''

-- ---------- FRONTEIRA 1: usuário ----------
select kansas_test.ok(
  kansas_test.count_as(:A::uuid,'invoices','select * from kansas.agent_threads') = 1,
  'A vê só a própria thread de faturas');

select kansas_test.ok(
  kansas_test.count_as(:A::uuid,'invoices',
    'select * from kansas.agent_threads where user_id = ' || quote_literal(:B) ) = 0,
  'A NÃO lê thread do B nem pedindo pelo user_id dele');

select kansas_test.ok(
  kansas_test.count_as(:A::uuid,'invoices','select * from kansas.agent_messages') = 1,
  'A NÃO lê mensagem do B');

select kansas_test.ok(
  kansas_test.count_as(:A::uuid,'invoices',
    'select * from kansas.agent_memories where user_id = ' || quote_literal(:B)) = 0,
  'A NÃO lê memória do B');

select kansas_test.ok(
  kansas_test.affected_as(:A::uuid,'invoices',
    'update kansas.agent_memories set value_json = ''"hackeado"'' where user_id = ' || quote_literal(:B)) = 0,
  'A NÃO consegue ALTERAR memória do B');

select kansas_test.ok(
  kansas_test.affected_as(:A::uuid,'invoices',
    'delete from kansas.agent_threads where user_id = ' || quote_literal(:B)) = 0,
  'A NÃO consegue APAGAR thread do B');

select kansas_test.ok(
  kansas_test.errcode_as(:A::uuid,'invoices',
    'insert into kansas.agent_threads (user_id, agent_id, title) values (' || quote_literal(:B) || ',''invoices'',''forjada'')') = '42501',
  'A NÃO consegue CRIAR linha em nome do B (with check barra)');

select kansas_test.ok(
  kansas_test.count_as(:A::uuid,'invoices',
    'select * from kansas.shared_user_facts where user_id = ' || quote_literal(:B)) = 0,
  'A NÃO lê fato compartilhado do B');

-- ---------- Sem sessão autenticada ----------
select kansas_test.ok(
  kansas_test.count_as(null,'invoices','select * from kansas.agent_threads') = 0,
  'Requisição sem usuário autenticado não enxerga nada');

select kansas_test.ok(
  kansas_test.count_as(null,null,'select * from kansas.agent_memories') = 0,
  'Sem JWT e sem agente: zero memória');

-- ---------- FRONTEIRA 2: agente ----------
select kansas_test.ok(
  kansas_test.count_as(:A::uuid,'invoices','select * from kansas.agent_memories') = 1,
  'Agente de Faturas vê só a memória de faturas (e não a expirada)');

select kansas_test.ok(
  kansas_test.count_as(:A::uuid,'goals','select * from kansas.agent_memories') = 1,
  'Agente de Metas vê só a memória de metas');

select kansas_test.ok(
  kansas_test.count_as(:A::uuid,'invoices',
    'select * from kansas.agent_memories where agent_id = ''goals''') = 0,
  'Faturas NÃO lê memória de Metas do MESMO usuário');

select kansas_test.ok(
  kansas_test.count_as(:A::uuid,'invoices',
    'select * from kansas.agent_messages where agent_id = ''goals''') = 0,
  'Faturas NÃO lê a conversa de Metas');

select kansas_test.ok(
  kansas_test.count_as(:A::uuid,null,'select * from kansas.agent_memories') = 0,
  'Sem agente no contexto, memória privada fica invisível');

select kansas_test.ok(
  kansas_test.errcode_as(:A::uuid,'invoices',
    'insert into kansas.agent_memories (user_id, agent_id, key, value_json) values (' || quote_literal(:A) || ',''goals'',''priority_goal'',''"sequestrada"'')') = '42501',
  'Faturas NÃO consegue escrever na memória de Metas');

select kansas_test.ok(
  kansas_test.errcode_as(:A::uuid,'invoices',
    'insert into kansas.agent_memories (user_id, agent_id, key, value_json) values (' || quote_literal(:A) || ',''invoices'',''chave_fora_do_escopo'',''1'')') = '42501',
  'Agente não escreve chave fora do writable_memory_scope do registry');

-- ---------- Memória expirada ----------
select kansas_test.ok(
  kansas_test.count_as(:A::uuid,'invoices',
    'select * from kansas.agent_memories where key = ''last_invoice_analysis''') = 0,
  'Memória expirada não é devolvida');

-- ---------- Fatos compartilhados filtrados pelo allowlist ----------
select kansas_test.ok(
  kansas_test.count_as(:A::uuid,'invoices',
    'select * from kansas.shared_user_facts where key = ''recurring_income_summary''') = 0,
  'Faturas NÃO lê recurring_income_summary (não está no allowlist dele)');

select kansas_test.ok(
  kansas_test.count_as(:A::uuid,'goals',
    'select * from kansas.shared_user_facts where key = ''recurring_income_summary''') = 1,
  'Metas LÊ recurring_income_summary (está no allowlist dele)');

select kansas_test.ok(
  kansas_test.count_as(:A::uuid,'invoices','select * from kansas.shared_user_facts') = 2,
  'Faturas vê apenas locale e currency');

-- ---------- Eventos entre agentes ----------
select kansas_test.ok(
  kansas_test.count_as(:A::uuid,'balance','select * from kansas.agent_events') = 1,
  'Saldo recebe o evento de compromisso publicado por Faturas');

select kansas_test.ok(
  kansas_test.count_as(:A::uuid,'transactions','select * from kansas.agent_events') = 0,
  'Transações NÃO recebe evento que não foi endereçado a ele');

select kansas_test.ok(
  kansas_test.count_as(:B::uuid,'balance','select * from kansas.agent_events') = 0,
  'B não recebe evento do A');

select kansas_test.ok(
  kansas_test.errcode_as(:A::uuid,'balance',
    'insert into kansas.agent_events (user_id, source_agent, type, payload, visible_to) values (' || quote_literal(:A) || ',''invoices'',''forjado'',''{}'',array[''planning''])') = '42501',
  'Saldo NÃO consegue publicar evento se passando por Faturas');

-- ---------- Agente inexistente ----------
select kansas_test.ok(
  kansas_test.errcode_as(:A::uuid,null,'select kansas.set_agent(''superagente_root'')') = '42501',
  'set_agent recusa agente que não está no registry');

-- ---------- Sem SQL livre para o cliente ----------
select kansas_test.ok(
  kansas_test.errcode_as(:A::uuid,'invoices','create table kansas.porta_dos_fundos (x int)') <> '00000',
  'Role authenticated não consegue criar tabela');

select kansas_test.ok(
  kansas_test.errcode_as(:A::uuid,'invoices','select * from kansas.audit_events') <> '00000',
  'Cliente não lê a trilha de auditoria');

-- ---------- Exclusão de dados ----------
select kansas_test.ok(
  (kansas_test.count_as(:B::uuid,'invoices','select * from kansas.agent_threads')) = 1,
  'B ainda tem a thread dele antes do purge do A');
