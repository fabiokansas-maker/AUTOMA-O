-- Fixtures: dois usuários reais, cada um com dados nos dois agentes.
-- Inseridos como owner (RLS bypass) de propósito: é o "estado do mundo".
truncate kansas.agent_events, kansas.agent_messages, kansas.agent_memories,
         kansas.shared_user_facts, kansas.agent_feedback, kansas.agent_threads cascade;

insert into kansas.agent_threads (id, user_id, agent_id, title) values
  ('11111111-1111-1111-1111-111111111111','aaaaaaaa-0000-0000-0000-00000000000a','invoices','Fatura de setembro'),
  ('22222222-2222-2222-2222-222222222222','aaaaaaaa-0000-0000-0000-00000000000a','goals','Viagem'),
  ('33333333-3333-3333-3333-333333333333','bbbbbbbb-0000-0000-0000-00000000000b','invoices','Fatura do Bruno');

insert into kansas.agent_messages (thread_id, user_id, agent_id, role, blocks) values
  ('11111111-1111-1111-1111-111111111111','aaaaaaaa-0000-0000-0000-00000000000a','invoices','user','[{"type":"text","text":"por que subiu?"}]'),
  ('33333333-3333-3333-3333-333333333333','bbbbbbbb-0000-0000-0000-00000000000b','invoices','user','[{"type":"text","text":"segredo do Bruno"}]');

insert into kansas.agent_memories (user_id, agent_id, key, value_json, expires_at) values
  ('aaaaaaaa-0000-0000-0000-00000000000a','invoices','preferred_card','"Nubank"', null),
  ('aaaaaaaa-0000-0000-0000-00000000000a','goals','priority_goal','"Viagem Japão"', null),
  ('aaaaaaaa-0000-0000-0000-00000000000a','invoices','last_invoice_analysis','"antiga"', now() - interval '1 day'),
  ('bbbbbbbb-0000-0000-0000-00000000000b','invoices','preferred_card','"Itau do Bruno"', null);

insert into kansas.shared_user_facts (user_id, key, value_json) values
  ('aaaaaaaa-0000-0000-0000-00000000000a','locale','"pt-BR"'),
  ('aaaaaaaa-0000-0000-0000-00000000000a','currency','"BRL"'),
  ('aaaaaaaa-0000-0000-0000-00000000000a','recurring_income_summary','"R$ 7.000 dia 5"'),
  ('bbbbbbbb-0000-0000-0000-00000000000b','locale','"en-US"');

insert into kansas.agent_events (user_id, source_agent, type, payload, visible_to) values
  ('aaaaaaaa-0000-0000-0000-00000000000a','invoices','upcoming_financial_commitment',
   '{"amount":2180.45,"currency":"BRL","due_date":"2026-09-25"}', array['balance','planning','goals']);
