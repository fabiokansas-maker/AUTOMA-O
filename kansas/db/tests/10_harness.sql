-- Helpers de teste: asserts que EXPLODEM (psql com ON_ERROR_STOP encerra).
create schema if not exists kansas_test;

create or replace function kansas_test.ok(cond boolean, msg text)
returns void language plpgsql as $$
begin
  if cond then
    raise notice 'PASS  %', msg;
  else
    raise exception 'FAIL  %', msg;
  end if;
end $$;

-- Executa SQL como o usuário X, opcionalmente no contexto do agente Y,
-- e devolve a contagem de linhas visíveis.
create or replace function kansas_test.count_as(
  p_user uuid, p_agent text, p_sql text
) returns int
language plpgsql as $$
declare v int;
begin
  perform set_config('request.jwt.claim.sub', coalesce(p_user::text,''), true);
  perform set_config('kansas.agent_id', coalesce(p_agent,''), true);
  set local role authenticated;
  execute 'select count(*) from (' || p_sql || ') q' into v;
  reset role;
  return v;
end $$;

-- Executa SQL como o usuário X e devolve o SQLSTATE do erro ('00000' se passou).
create or replace function kansas_test.errcode_as(
  p_user uuid, p_agent text, p_sql text
) returns text
language plpgsql as $$
declare v_state text := '00000';
begin
  perform set_config('request.jwt.claim.sub', coalesce(p_user::text,''), true);
  perform set_config('kansas.agent_id', coalesce(p_agent,''), true);
  begin
    set local role authenticated;
    execute p_sql;
  exception when others then
    v_state := sqlstate;
  end;
  reset role;
  return v_state;
end $$;

-- Quantas linhas um UPDATE/DELETE conseguiu tocar sob RLS.
create or replace function kansas_test.affected_as(
  p_user uuid, p_agent text, p_sql text
) returns int
language plpgsql as $$
declare v int;
begin
  perform set_config('request.jwt.claim.sub', coalesce(p_user::text,''), true);
  perform set_config('kansas.agent_id', coalesce(p_agent,''), true);
  set local role authenticated;
  execute p_sql;
  get diagnostics v = row_count;
  reset role;
  return v;
end $$;
