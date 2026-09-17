# Auditoria Play Store — o que eu verifiquei sozinho (17/09/2026)

Tudo abaixo tem evidência. Onde eu **não** consegui verificar, está escrito que
não consegui — não tem chute nenhum neste documento.

## 1. Correção importante: o app NÃO está fora da Play Store

Você descreveu o problema como "meu app não está aparecendo". Fui olhar.

| O que eu checei | Resultado | Como verifiquei |
|---|---|---|
| Página pública do app | **no ar, HTTP 200** | `GET play.google.com/store/apps/details?id=com.pulsefinanceiro.dreai` |
| Nome publicado | **Dinheiro em Dia** | `og:title` da própria página |
| Subtítulo | "Controle de gastos e contas: saiba quanto sobra até o próximo pagamento." | meta description |
| Versão | **1.8.8** | página da loja |
| Última atualização | **17 de setembro de 2026 — hoje** | bloco "Atualizado em" |
| Pacote | `com.pulsefinanceiro.dreai` | id da URL + cockpit Supabase |

Ou seja: **existe release em produção e a página pública responde.** Em junho
o app estava travado em teste fechado — o cockpit registra o bloqueio em
05/06 ("Google negou produção: conta nova exige 12+ testadores por 14 dias") —
mas isso já foi superado.

O que sobra, então, é **descoberta**, não publicação: link direto funciona,
busca por nome é outra história. São problemas diferentes e o segundo se
resolve com título/descrição/assets e volume de instalação, não com código.

E há um detalhe que muda a conversa: o produto hoje se chama **Dinheiro em
Dia**. "Kansas IA Financeira" é um nome novo. Ninguém está procurando por ele
ainda — a busca não vai achar um nome que a ficha não tem.

## 2. O prazo que realmente pode tirar o app do ar — faltam 13 dias

Achei na sua caixa de entrada, do `googleplay-noreply@google.com`:

> **[Último lembrete] Registre seus apps e chaves de assinatura para atender
> aos requisitos da verificação de desenvolvedor Android até 30 de setembro
> de 2026** — *"Todos os apps do Google Play precisam ser registrados até 30 de
> setembro de 2026 (…). Caso contrário, eles serão removidos da plataforma no
> mundo todo."* (e-mail de 04/09/2026; houve um anterior em 07/08/2026)

O mesmo e-mail diz que **mais de 99% dos apps foram registrados
automaticamente** (os que usam a chave de assinatura do Google Play), e que dá
para conferir na home do Play Console, pelo status ao lado de cada app.

Eu **não consigo verificar** se `com.pulsefinanceiro.dreai` está registrado:
isso é uma tela do Play Console, e não existe API pública que responda isso.
É a única coisa neste documento inteiro que depende de alguém olhar — e é
literalmente olhar, não fazer.

Também chegou em 26/08/2026: *"novos requisitos de qualidade de apps"*,
sobre limites de memória do Android.

## 3. Target SDK — a regra confirmada na fonte

Confirmei na documentação do Google Play (não de memória):

| Situação | Exigência | Prazo |
|---|---|---|
| Atualização nova enviada à Play | **API 36** (Android 16) ou superior | 31/08/2026 |
| App existente seguir disponível a novos usuários em Android recente | **API 35** (Android 15) ou superior | 31/08/2026 |
| Prorrogação | possível **até 01/11/2026**, via formulário no Play Console | — |

Consequência de não cumprir: o app **deixa de aparecer** para usuários em
Android recente, continuando visível só em versões antigas. Isso bate
exatamente com o sintoma "sumiu para uns aparelhos e para outros não".

**Não consigo confirmar o targetSdk atual do app**: o código-fonte não está
em nenhum repositório que esta sessão alcança (ver seção 5). Por isso o
auditor `kansas/tools/audit_app.py` já está pronto e responde isso em segundos
assim que o código chegar.

## 4. A ligação entre os seus dois problemas

Você relatou duas coisas: o app sumindo em alguns aparelhos, e menus ficando
por baixo de barras. Elas provavelmente são a mesma história em dois atos.

```
targetSdk antigo  ──> app some para novos usuários em Android recente
       │
       └── você sobe para 35/36 para resolver
                     │
                     └── Android 15+ liga edge-to-edge
                                   │
                                   └── janela desenha ATRÁS das barras
                                                 │
                                                 └── menu/botão sob a barra
```

Não é um bug isolado de padding: é comportamento novo da plataforma. A correção
é tratar insets em toda a árvore de telas — e por isso `kansas/app/` já vem com
`AgentHome` e `AgentScreen` usando `useSafeAreaInsets` em vez de número mágico,
e o auditor marca `paddingTop: 24`, `StatusBar.currentHeight` e afins.

## 5. O que me bloqueia, exatamente

O código do app **não está em nenhum repositório GitHub ao qual eu tenho
acesso**. Verifiquei: a conta expõe um único repositório para esta sessão,
`fabiokansas-maker/AUTOMA-O`, que é o projeto de automação de vagas — não o app.

Pelos registros do seu próprio cockpit, o app é **React Native** (há ação
pendente citando `react-native-iap` e um junction em `C:\Dev`), com backend
**Firebase** (ação pendente: "Edge Function que puxa contagem de usuários do
Firebase"). O fonte vive no seu PC Windows.

Também procurei no Drive: não há espelho do código lá, e o `last-heartbeat.json`
da ponte com o PC não existe — a bridge deste repo não está rodando.

Por isso eu **não refatorei o app**: não dá para refatorar o que não se pode
ler, e inventar o conteúdo dos seus arquivos seria mentira. O que eu fiz foi
construir tudo que **não depende** de ler o código do app — e deixar o auditor
pronto para atacar a Fase Zero sozinho no minuto em que o fonte aparecer.

## 6. O que já está pronto e testado neste repositório

| Entrega | Estado | Prova |
|---|---|---|
| Migrations do núcleo agent-first | prontas | `kansas/db/001..003` |
| Isolamento usuário↔usuário e agente↔agente | **29 testes passando** | `bash kansas/db/run_tests.sh` |
| Cálculo financeiro fora do LLM + validação de tools + i18n | **30 testes passando** | `node --experimental-strip-types kansas/backend/tests/unit.test.ts` |
| Auditoria estática das policies | verde | `python3 kansas/tools/audit_policies.py kansas/db` |
| Auditor Fase Zero do app | validado contra fixture | `python3 kansas/tools/audit_app.py <repo>` |
| Home e tela de agente com insets corretos | prontas | `kansas/app/` |
| CI que roda tudo isso a cada push | pronto | `.github/workflows/kansas-security.yml` |
