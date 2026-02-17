---
summary: "Notas locais para Discord bot"
read_when:
  - Bootstrapping um workspace manualmente
---

# TOOLS.md - Notas Locais

Skills definem _como_ as ferramentas funcionam. Este arquivo é para detalhes _específicos_ da sua configuração Discord.

## O Que Vai Aqui

Coisas como:

- Nomes de canais e servidores Discord
- Webhooks e URLs de integração
- Tokens e chaves de API (use variáveis de ambiente em `.env`, adicione arquivos de segredos ao `.gitignore` e nunca faça commit de tokens)
- Comandos customizados e aliases
- Roles e permissões específicas
- Qualquer coisa específica do ambiente

## Exemplo para Discord

### Servidores

- **Principal**: `{server_id}` — Servidor principal do Agno
  - Canal geral: `{channel_id}`
  - Canal de comandos: `{channel_id}`
  - Canal de logs: `{channel_id}`

### Webhooks

- **Notificações**: `{webhook_url}` — Para alertas importantes
- **Logs**: `{webhook_url}` — Para logs de sistema

### Comandos Customizados

- `!info` — Mostra informações do usuário
- `!ajuda` — Lista comandos disponíveis
- `!status` — Status do bot

### Integrações Externas

- **API Externa**: `{base_url}` — URL base para chamadas de API
- **Timeout padrão**: 30000ms

## Por Que Separado?

Skills são compartilhadas. Sua configuração é sua. Mantê-las separadas significa que você pode atualizar skills sem perder suas notas, e compartilhar skills sem vazar sua infraestrutura.

---

Adicione o que te ajudar a fazer seu trabalho. Esta é sua cola.
