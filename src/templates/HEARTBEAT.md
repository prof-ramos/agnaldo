---
summary: "Template de tarefas de monitoramento Discord"
read_when:
  - Bootstrapping um workspace manualmente
---

# HEARTBEAT.md - Tarefas de Monitoramento Discord

# Mantenha este arquivo vazio (ou apenas com comentários) para pular chamadas de API de heartbeat.

# Adicione tarefas abaixo quando quiser que o agente verifique algo periodicamente.

## Exemplos de Tarefas Discord

### Verificações Diárias (rodar 2-4 vezes ao dia)

- [ ] **Verificar mensagens não lidas** — Canais importantes com menções?
- [ ] **Verificar alertas do servidor** — Algo deu errado?
- [ ] **Verificar novos membros** — Bem-vindos para dar?
- [ ] **Verificar status de integrações** — APIs externas funcionando?

### Verificações Semanais

- [ ] **Relatório de atividade** — Resumo da semana do servidor
- [ ] **Limpeza de canais** — Arquivar ou limpar canais antigos
- [ ] **Atualização de roles** — Verificar permissões e cargos

### Tarefas Proativas

- [ ] **Moderar spam** — Detectar e reportar spam
- [ ] **Saudar novos membros** — Mensagem de boas-vindas automática
- [ ] **Monitorar palavras-chave** — Alertar sobre tópicos importantes

## Quando agir (HEARTBEAT_OK para ignorar)

**Aja quando:**
- Mensagem importante chegou
- Alerta de sistema detectado
- Evento agendado próximo (< 2h)
- Algo interessante encontrado
- > 8h desde última mensagem

**Ignore com HEARTBEAT_OK quando:**
- Madrugada (23:00-08:00) a menos que urgente
- Humanos claramente ocupados
- Nada novo desde última verificação
- Verificado há < 30 minutos

---

Adicione e remova tarefas conforme necessário. Mantenha curto para limitar uso de tokens.
