# Comandos Jarvis — /bridge

Os 4 comandos abaixo dão controle humano sobre a fila do ChatGPT
Command Bridge. Todos leem/escrevem na mesma Google Sheet.

## /bridge status

Resumo do estado da ponte.

Resposta:
```
[BRIDGE STATUS]
new:              N
running:          N
awaiting_approval: N
done (24h):       N
error (24h):      N
blocked (24h):    N
last_command:     <command_id> · <action>@<target> · <status>
```

## /bridge pendentes

Lista a aba `pending_approval`, do mais recente para o mais antigo.

Resposta:
```
[PENDÊNCIAS]
1. <command_id>  action=<x>  target=<y>  asked_at=<ts>
2. ...
use:  /bridge aprovar <command_id>
```

## /bridge aprovar <command_id>

1. Lê linha em `pending_approval`
2. Atualiza `commands.approved=true, status=new`
3. Remove de `pending_approval`
4. Append em `logs`: level=audit, event=approved_by_jarvis

Resposta:
```
[APROVADO] <command_id>  action=<x>  target=<y>
n8n vai pegar na próxima rodada (até 30s)
```

## /bridge resultado <command_id>

Lê `results` pelo `command_id`, devolve summary + drive_link.

Resposta:
```
[RESULTADO] <command_id>
exit_code: <n>
summary:   <text>
drive:     <link>
finished:  <ts>
```
