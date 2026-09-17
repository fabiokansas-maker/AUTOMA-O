# Checklist Play Console — release agent-first

Itens que só existem no Play Console (não há API pública para vários deles).
Marcados com ⏳ os que dependem de conferir uma tela; ✅ os que este repositório
já resolve em código.

## Prazo curto — vence 30/09/2026

- ⏳ **Verificação de desenvolvedor Android**: confirmar na home do Play Console
  se `com.pulsefinanceiro.dreai` aparece como registrado. Mais de 99% dos apps
  foram registrados automaticamente (chave de assinatura do Google Play); o
  filtro "não registrados" mostra o que sobrou. E-mail do Google de 04/09/2026:
  apps não registrados *"serão removidos da plataforma no mundo todo"*.

## Compatibilidade

- ⏳ `targetSdk` ≥ **36** na próxima atualização (regra de 31/08/2026);
  ≥ 35 para o app existente seguir disponível a novos usuários em Android
  recente. Prorrogação possível até 01/11/2026.
- ✅ Edge-to-edge tratado por insets nas telas novas (`kansas/app/`).
- ✅ Auditor aponta `targetSdk` e paddings mágicos: `tools/audit_app.py`.
- ⏳ Requisitos novos de qualidade (limites de memória) — e-mail de 26/08/2026.

## Ficha da loja

- ⏳ Título: **Kansas IA Financeira** (20 caracteres; o limite é 30).
- ⏳ Descrição curta e completa reescritas para o posicionamento de
  especialistas, em cada idioma distribuído.
- ⏳ Screenshots novos (home de agentes + tela de agente).
- ⏳ Conferir países/regiões habilitados e o catálogo de dispositivos: exclusão
  de aparelho ou região é causa clássica de "não aparece para fulano".
- ⏳ Usar o botão **View on Google Play** para ver a ficha publicada de fato.

## Conteúdo do app e políticas

- ✅ Denúncia de resposta de IA **dentro do app** (👍 👎 ⚑) —
  `app/AgentScreen.tsx` + tabela `kansas.agent_feedback`.
- ✅ Exclusão de conta e dados apaga também threads, memórias, fatos
  compartilhados e eventos — `kansas.purge_user_agent_data`.
- ⏳ **Declaração de funcionalidades financeiras**: o primeiro lançamento deve
  ficar em organização/educação financeira. "Financial advice" é uma categoria
  declarável à parte — não deixar o Agente de Planejamento virar consultor de
  investimento sem revisar isso por mercado.
- ⏳ **Data safety** coerente com o que a Edge Function envia ao provedor de IA.
- ⏳ Política de privacidade acessível na loja **e** dentro do app, dizendo o
  que vai para o provedor de IA, por quanto tempo fica e como apagar.

## Lançamento

- ⏳ Teste interno → fechado → produção com **rollout gradual**
  (sugestão de engenharia: 5% → 20% → 50% → 100%, nunca 100% de cara).
- ⏳ Ler o **pre-launch report** antes de abrir o rollout.
- ⏳ Acompanhar **Android vitals** (crashes/ANR) no primeiro degrau.
- ✅ Suíte de segurança roda no CI a cada push antes de qualquer build.
