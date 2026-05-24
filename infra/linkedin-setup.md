# LinkedIn — setup manual de conta nova (1× por ano, ~10 min)

> Necessário porque LinkedIn signup tem captcha + verificação por SMS — impossível automatizar 100%.
> Esta conta é **separada** da principal `fabiokansas@gmail.com`. Se LinkedIn banir por
> automação (~30 dias é o padrão), a conta principal continua intacta.

## Passos (executar uma vez, depois 100% automático)

1. **Criar conta Gmail nova** (se ainda não existe):
   - Abra `accounts.google.com/signup` em uma janela anônima.
   - Username: `fabiokansasblack` (cai em `fabiokansasblack@gmail.com`).
   - Senha forte (use 1Password / Bitwarden / gerenciador qualquer).
   - Verificar com telefone `(11) 95927-3390` (mesmo número, sem problema).
   - Nome: "Fabio Fernandes". Data de nascimento real.

2. **Criar conta LinkedIn**:
   - `linkedin.com/signup`, email `fabiokansasblack@gmail.com`.
   - Confirmar SMS no mesmo telefone.
   - Localização: Diadema, SP, Brasil.
   - Cargo atual / mais recente: "Analista de Controladoria" — "(autônomo)" se quiser pular validação.

3. **Perfil mínimo** (não precisa ser completo — só ser válido pra busca de vagas):
   - Foto: opcional, mas reduz taxa de banimento.
   - Headline: "Analista de Controladoria / FP&A — buscando oportunidades em SP".
   - Sobre: 2 frases ok.
   - Experiência: 1 cargo é suficiente.
   - **Pular** convite Premium, contatos, etc.

4. **Extrair cookie `li_at`** (sessão autenticada):
   - Chrome → F12 (DevTools) → Application → Cookies → `https://www.linkedin.com`.
   - Achar `li_at` na lista (valor começa com `AQEDA...`, ~200 caracteres).
   - Copiar o valor.

5. **Cadastrar como GitHub Secret**:
   - https://github.com/fabiokansas-maker/AUTOMA-O/settings/secrets/actions
   - "New repository secret" → Nome `LINKEDIN_LI_AT` → Value: cole o cookie.
   - Salvar.

Pronto. Próximo run do cron já usa a versão autenticada (`fetch_linkedin_jobs_auth`), que
pega bem mais vagas com metadata melhor do que a versão guest.

## Manutenção

- Cookie `li_at` expira em ~12 meses. Quando começarem a chegar 0 vagas LinkedIn no
  relatório, repetir o passo 4 + 5.
- Se LinkedIn banir a conta: criar nova com `fabiokansasblack2@gmail.com` etc. — sem dano à principal.

## Decisão arquitetural

**Sem auto-apply LinkedIn** (Easy Apply): risco de banimento muito alto vs. benefício
pequeno (recrutadora vê a vaga manualmente do mesmo jeito). LinkedIn fica só pra
**discovery** (descobrir vagas + match Gemini → encaminhar a candidatura via Gupy/Workday
ou email da empresa quando disponível).
