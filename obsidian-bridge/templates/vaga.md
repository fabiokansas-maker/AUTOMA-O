---
source: {{source}}
external_id: {{external_id}}
title: {{title}}
company: {{company}}
location: {{location}}
remote: {{remote}}
salary_min: {{salary_min}}
salary_max: {{salary_max}}
url: {{url}}
posted_at: {{posted_at}}
discovered_at: {{discovered_at}}
score: {{score}}
status: {{status}}
---

# {{title}} — {{company}}

📍 {{location}}{{#remote}} (remoto){{/remote}}
💰 R$ {{salary_min}}{{#salary_max}} – R$ {{salary_max}}{{/salary_max}}
🗓️ Postada em {{posted_at}} • descoberta em {{discovered_at}}
🔗 [Ver na origem]({{url}})

## Match analysis

**Score:** {{score}}/100 — {{status}}

**Resumo:** {{match_summary}}

### ✅ Requisitos atendidos
{{#requirements_met}}
- **{{skill}}** — {{evidence}}
{{/requirements_met}}

### ⚠️ Gaps
{{#requirements_gap}}
- **{{skill}}** (severidade: {{severity}})
{{/requirements_gap}}

## Descrição original

{{description}}

## Candidatura

{{#application}}
- **Status:** {{status}}
- **Enviada em:** {{submitted_at}}
- **Resposta:** {{responded_at}} — {{response_notes}}
- **Erro:** {{error}}

### Carta de apresentação enviada
{{cover_letter}}
{{/application}}
