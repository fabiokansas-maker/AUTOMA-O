/**
 * Strings externalizadas. O app roda em mais de um país: nada de texto
 * cravado em tela. Idioma sem tradução cai no inglês, não quebra.
 */
export type Idioma = 'pt' | 'en' | 'es';

type Dicionario = Record<string, string>;

const pt: Dicionario = {
  'app.name': 'Kansas IA Financeira',
  'home.greeting': 'Olá, {name}',
  'home.ask_title': 'O que você quer resolver hoje?',
  'home.ask_placeholder': 'Pergunte à Kansas...',
  'home.ask_a11y': 'Campo de pergunta para a Kansas',
  'home.specialists': 'Seus especialistas',
  'home.alerts': 'Alertas dos seus agentes',
  'agent.input_placeholder': 'Escreva sua pergunta',
  'agent.input_a11y': 'Campo de mensagem para o agente',
  'agent.send': 'Enviar',
  'agent.running_tool': 'consultando {tool}...',
  'agent.empty': 'Pergunte qualquer coisa sobre este assunto.',
  'common.retry': 'tentar de novo',
  'common.cancel': 'Cancelar',
  'common.confirm': 'Confirmar',
  'error.rede': 'Sem conexão agora.',
  'error.timeout': 'Demorou demais para responder.',
  'error.sessao_expirada': 'Sua sessão expirou. Entre de novo.',
  'error.sem_permissao': 'Este agente não tem acesso a esse dado.',
  'error.muitas_requisicoes': 'Muitas perguntas seguidas. Respire e tente de novo.',
  'error.erro_servidor': 'Algo falhou do nosso lado.',
  'feedback.helpful': 'Resposta útil',
  'feedback.not_helpful': 'Resposta não ajudou',
  'feedback.report': 'Reportar esta resposta',
  'feedback.report_short': 'Reportar',
  'feedback.thanks': 'Obrigado pelo retorno.',
  'report.title': 'Reportar resposta',
  'report.question': 'O que houve com esta resposta?',
  'report.incorreto': 'Está incorreta',
  'report.ofensivo': 'É ofensiva',
  'report.perigoso': 'É perigosa',
  'report.privacidade': 'Expõe dado meu',
  'report.outro': 'Outro motivo',
  'invoice.closes_on': 'fecha em {date}',
  'invoice.due_on': 'vence em {date}',
  'settings.title': 'Ajustes',
  'settings.privacy': 'Privacidade e dados',
  'settings.clear_thread': 'Limpar esta conversa',
  'settings.clear_memory': 'Limpar o que este agente lembra de mim',
  'settings.delete_account': 'Excluir conta e todos os dados',
  'settings.delete_warning':
    'Isto apaga conversas, memórias dos agentes, preferências e não dá para desfazer.',
  'settings.language': 'Idioma',
  'settings.currency': 'Moeda',
  'quick.balance.now': 'Quanto tenho disponível?',
  'quick.balance.next7': 'O que vence nos próximos 7 dias?',
  'quick.invoice.current': 'Como está minha fatura?',
  'quick.invoice.why': 'Por que ela subiu?',
  'quick.goal.progress': 'Como está minha meta?',
  'quick.tx.month': 'Onde gastei este mês?',
  'quick.budget.status': 'Estourei alguma categoria?',
  'quick.planning.month': 'Quanto posso gastar até o fim do mês?',
  'agents.balance': 'Agente de Saldo',
  'agents.balance.desc': 'Entenda seu dinheiro disponível e os próximos compromissos.',
  'agents.invoices': 'Agente de Faturas',
  'agents.invoices.desc': 'Analise cartões, faturas, compras, fechamento e vencimento.',
  'agents.goals': 'Agente de Metas',
  'agents.goals.desc': 'Planeje objetivos e acompanhe seu progresso.',
  'agents.transactions': 'Agente de Transações',
  'agents.transactions.desc': 'Encontre, classifique e organize suas movimentações.',
  'agents.budget': 'Agente de Orçamento',
  'agents.budget.desc': 'Controle categorias, limites e comportamento de gastos.',
  'agents.planning': 'Agente de Planejamento',
  'agents.planning.desc': 'Faça simulações e conecte informações dos seus especialistas.',
};

const en: Dicionario = {
  'app.name': 'Kansas IA Financeira',
  'home.greeting': 'Hi, {name}',
  'home.ask_title': 'What do you want to sort out today?',
  'home.ask_placeholder': 'Ask Kansas...',
  'home.ask_a11y': 'Question field for Kansas',
  'home.specialists': 'Your specialists',
  'home.alerts': 'Alerts from your agents',
  'agent.input_placeholder': 'Type your question',
  'agent.input_a11y': 'Message field for the agent',
  'agent.send': 'Send',
  'agent.running_tool': 'checking {tool}...',
  'agent.empty': 'Ask anything about this topic.',
  'common.retry': 'try again',
  'common.cancel': 'Cancel',
  'common.confirm': 'Confirm',
  'error.rede': 'No connection right now.',
  'error.timeout': 'That took too long.',
  'error.sessao_expirada': 'Your session expired. Sign in again.',
  'error.sem_permissao': 'This agent has no access to that data.',
  'error.muitas_requisicoes': 'Too many questions in a row. Try again shortly.',
  'error.erro_servidor': 'Something failed on our side.',
  'feedback.helpful': 'Helpful answer',
  'feedback.not_helpful': 'Answer did not help',
  'feedback.report': 'Report this answer',
  'feedback.report_short': 'Report',
  'feedback.thanks': 'Thanks for the feedback.',
  'report.title': 'Report answer',
  'report.question': 'What was wrong with this answer?',
  'report.incorreto': 'It is incorrect',
  'report.ofensivo': 'It is offensive',
  'report.perigoso': 'It is dangerous',
  'report.privacidade': 'It exposes my data',
  'report.outro': 'Other reason',
  'invoice.closes_on': 'closes on {date}',
  'invoice.due_on': 'due on {date}',
  'settings.title': 'Settings',
  'settings.privacy': 'Privacy and data',
  'settings.clear_thread': 'Clear this conversation',
  'settings.clear_memory': 'Clear what this agent remembers about me',
  'settings.delete_account': 'Delete account and all data',
  'settings.delete_warning':
    'This erases conversations, agent memories and preferences. It cannot be undone.',
  'settings.language': 'Language',
  'settings.currency': 'Currency',
  'quick.balance.now': 'How much do I have available?',
  'quick.balance.next7': 'What is due in the next 7 days?',
  'quick.invoice.current': 'How is my statement?',
  'quick.invoice.why': 'Why did it go up?',
  'quick.goal.progress': 'How is my goal going?',
  'quick.tx.month': 'Where did I spend this month?',
  'quick.budget.status': 'Did I blow any category?',
  'quick.planning.month': 'How much can I spend until month end?',
  'agents.balance': 'Balance Agent',
  'agents.balance.desc': 'Understand your available money and what is already committed.',
  'agents.invoices': 'Invoices Agent',
  'agents.invoices.desc': 'Cards, statements, purchases, closing and due dates.',
  'agents.goals': 'Goals Agent',
  'agents.goals.desc': 'Plan objectives and follow your progress.',
  'agents.transactions': 'Transactions Agent',
  'agents.transactions.desc': 'Find, categorize and organize your activity.',
  'agents.budget': 'Budget Agent',
  'agents.budget.desc': 'Categories, limits and spending behaviour.',
  'agents.planning': 'Planning Agent',
  'agents.planning.desc': 'Run simulations across your specialists.',
};

const es: Dicionario = {
  ...en,
  'home.greeting': 'Hola, {name}',
  'home.ask_title': '¿Qué quieres resolver hoy?',
  'home.ask_placeholder': 'Pregúntale a Kansas...',
  'home.specialists': 'Tus especialistas',
  'home.alerts': 'Alertas de tus agentes',
  'agent.send': 'Enviar',
  'common.retry': 'intentar de nuevo',
  'settings.title': 'Ajustes',
  'settings.delete_account': 'Eliminar cuenta y todos los datos',
  'agents.balance': 'Agente de Saldo',
  'agents.invoices': 'Agente de Facturas',
  'agents.goals': 'Agente de Metas',
  'agents.transactions': 'Agente de Transacciones',
  'agents.budget': 'Agente de Presupuesto',
  'agents.planning': 'Agente de Planificación',
};

const DICIONARIOS: Record<Idioma, Dicionario> = { pt, en, es };

export function traduzir(
  idioma: string, chave: string, params?: Record<string, string>,
): string {
  const dic = DICIONARIOS[(idioma as Idioma)] ?? en;
  // chave sem tradução no idioma do usuário cai no inglês antes de virar a
  // própria chave feia na tela
  let texto = dic[chave] ?? en[chave] ?? chave;
  if (params) {
    for (const [k, v] of Object.entries(params)) {
      texto = texto.split(`{${k}}`).join(v);
    }
  }
  return texto;
}

export function idiomasDisponiveis(): Idioma[] {
  return Object.keys(DICIONARIOS) as Idioma[];
}
