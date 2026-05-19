# evidence/

Cada job do workflow `hostinger-auto.yml` grava aqui um markdown com timestamp
e link para o run no GitHub Actions. Esses arquivos são commitados de volta
no repo para que o Claude (que não consegue chamar a API do GitHub Actions
sem token autenticado) possa ler o resultado via `git pull`.
