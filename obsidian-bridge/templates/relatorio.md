---
data: {{date}}
gerado_por: 06-reporter
---

# Relatório diário — {{date_pretty}}

## KPIs

| Métrica | Valor |
|---|---|
| Vagas vistas (24h) | {{seen_24h}} |
| Vagas com match ≥70 | {{matched_24h}} |
| Candidaturas enviadas | {{applied_24h}} |
| Respostas recebidas | {{responses_24h}} |

## Por plataforma (24h)

{{#by_source}}
- **{{source}}** — vistas: {{seen}}, match: {{matched}}, enviadas: {{sent}}, saúde: {{health}}
{{/by_source}}

## Top 5 vagas com maior score

{{#top_jobs}}
- **{{score}}** — [{{title}} @ {{company}}]({{url}}) ({{location}})
{{/top_jobs}}

## Top skills em gap

(Skills que aparecem mais nos requirements_gap — possíveis investimentos de aprendizado)

{{#top_gaps}}
- **{{skill}}** — apareceu em {{count}} vagas
{{/top_gaps}}

## Saúde dos conectores

{{#sources_health}}
- **{{source}}** — última coleta: {{last_run_at}}, último erro: {{last_error}}
{{/sources_health}}

## Próximas ações sugeridas

- Revisar candidaturas com `status='failed'` e investigar erros
- Atualizar skills com gap recorrente
