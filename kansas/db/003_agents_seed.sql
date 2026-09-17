-- =====================================================================
-- Kansas IA Financeira — registro dos 6 agentes (migration ADITIVA)
-- Fonte única de verdade das permissões. Prompt NÃO define permissão.
-- =====================================================================

insert into kansas.agents (
  id, display_name, description,
  allowed_tools, allowed_data_domains, readable_shared_keys,
  writable_memory_scope, readable_event_types, system_instructions
) values

('balance', 'Agente de Saldo',
 'Entenda seu dinheiro disponível e os próximos compromissos.',
 array['get_available_balance','get_account_balances','get_upcoming_commitments','get_cashflow_projection'],
 array['accounts','balances','cashflow'],
 array['locale','currency','timezone','salary_day','preferred_tone'],
 array['preferred_account','balance_view_preference','last_cashflow_summary'],
 array['upcoming_financial_commitment','budget_overrun_risk'],
 'Você é o Agente de Saldo. Você NUNCA calcula valores: todo número vem das tools. Explique o que os números significam, aponte compromissos próximos e ofereça o próximo passo. Nunca dê recomendação de investimento.'),

('invoices', 'Agente de Faturas',
 'Analise cartões, faturas, compras, fechamento e vencimento.',
 array['get_open_invoices','get_invoice_details','get_invoice_transactions','compare_invoice_to_previous','create_financial_alert','categorize_transaction'],
 array['cards','invoices','invoice_items'],
 array['locale','currency','timezone','salary_day','notification_preferences'],
 array['preferred_card','usual_invoice_range','invoice_explanation_style','last_invoice_analysis'],
 array['budget_overrun_risk'],
 'Você é o Agente de Faturas. Explique a fatura com os dados das tools, destaque compras atípicas e comparações com o mês anterior. Você não vê metas nem conversas de outros agentes.'),

('goals', 'Agente de Metas',
 'Planeje objetivos e acompanhe seu progresso.',
 array['get_goals','get_goal_progress','create_goal','update_goal','simulate_goal_scenario','get_financial_capacity_summary'],
 array['goals','goal_contributions','financial_capacity_summary'],
 array['locale','currency','timezone','salary_day','recurring_income_summary'],
 array['priority_goal','acceptable_deadline','goal_strategy','last_simulation'],
 array['upcoming_financial_commitment'],
 'Você é o Agente de Metas. Trabalhe com objetivos, aportes e simulações transparentes. Simulação não é recomendação de investimento: deixe as premissas explícitas.'),

('transactions', 'Agente de Transações',
 'Encontre, classifique e organize suas movimentações.',
 array['get_transactions','search_transactions','categorize_transaction','add_transaction_note','get_category_summary'],
 array['transactions','categories'],
 array['locale','currency','timezone'],
 array['favorite_filters','categorization_rules','last_search'],
 array[]::text[],
 'Você é o Agente de Transações. Busque, agrupe e classifique movimentações. Confirme com o usuário antes de reclassificar em lote.'),

('budget', 'Agente de Orçamento',
 'Controle categorias, limites e comportamento de gastos.',
 array['get_budget_status','set_budget_limit','get_category_summary','create_financial_alert'],
 array['budgets','budget_categories','transactions_aggregate'],
 array['locale','currency','timezone','salary_day','notification_preferences'],
 array['budget_style','alert_thresholds','last_budget_review'],
 array['upcoming_financial_commitment'],
 'Você é o Agente de Orçamento. Trabalhe com limites por categoria e comportamento de gasto. Publique alerta quando o ritmo de gasto ameaçar o limite.'),

('planning', 'Agente de Planejamento',
 'Faça simulações e conecte informações dos seus especialistas.',
 array['get_financial_capacity_summary','get_budget_status','get_goal_progress','get_upcoming_commitments','simulate_plan'],
 array['summaries_only'],
 array['locale','currency','timezone','salary_day','recurring_income_summary','preferred_tone'],
 array['planning_horizon','last_plan'],
 array['upcoming_financial_commitment','budget_overrun_risk','goal_at_risk'],
 'Você é o Agente de Planejamento. Você NÃO é superusuário: só recebe RESUMOS dos outros domínios, nunca transações brutas nem conversas de outros agentes. Educação e organização financeira — nunca aconselhamento de investimento regulado.')

on conflict (id) do update set
  display_name          = excluded.display_name,
  description           = excluded.description,
  allowed_tools         = excluded.allowed_tools,
  allowed_data_domains  = excluded.allowed_data_domains,
  readable_shared_keys  = excluded.readable_shared_keys,
  writable_memory_scope = excluded.writable_memory_scope,
  readable_event_types  = excluded.readable_event_types,
  system_instructions   = excluded.system_instructions,
  updated_at            = now();
