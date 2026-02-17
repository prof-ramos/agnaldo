# Templates OpenClaw - Agente Discord Agno

Templates adaptados para o agente Discord brasileiro "Agno", baseados na estrutura OpenClaw original.

## Estrutura dos Templates

### `SOUL.md` (2.4 KB)
Personalidade e filosofia do agente. Define verdades fundamentais, fronteiras, e comportamento. Adaptado para contexto Discord brasileiro com gírias moderadas e compreensão cultural.

**Seções principais:**
- Verdades Fundamentais (seja útil, tenha opiniões, seja engenhoso)
- Fronteiras (privacidade, permissões externas)
- Vibração (como transparecer)
- Contexto Discord (adaptações para plataforma brasileira)

### `USER.md` (1.4 KB)
Template de perfil de usuário Discord para contexto pessoal.

**Campos incluídos:**
- Dados pessoais (nome, pronomes, fuso horário)
- Contexto Discord (ID, username, servidores, funções)
- Preferências de comunicação
- Projetos atuais e preferências individuais

### `IDENTITY.md` (1.1 KB)
Metadados do agente Discord Agno.

**Campos incluídos:**
- Nome, criatura, vibração, emoji, avatar
- Específicos Discord (prefixo de comando, canais principais)
- Notas de implementação

### `TOOLS.md` (1.5 KB)
Documentação de tools customizadas para Discord.

**Exemplos incluídos:**
- Servidores e canais Discord
- Webhooks e URLs de integração
- Comandos customizados
- Integrações externas

### `HEARTBEAT.md` (1.7 KB)
Tarefas de monitoramento para heartbeat checks do bot Discord.

**Categorias de tarefas:**
- Verificações diárias (mensagens, alertas, novos membros)
- Verificações semanais (relatórios, limpeza, roles)
- Tarefas proativas (moderação, boas-vindas, monitoramento)

### `AGENTS.md` (9.1 KB)
Manual completo de operação do agente Discord Agno.

**Seções principais:**
- Primeira execução e inicialização
- Sistema de memória (diária vs longo prazo)
- Segurança Discord
- Comportamento em chats de grupo (quando falar/ficar quieto)
- Uso de reações emoji naturais
- Formatação Discord específica
- Heartbeats vs Cron jobs
- Manutenção de memória

### `MEMORY.md` (3.1 KB)
Template de memória curada de longo prazo.

**Seções principais:**
- Avisos de segurança (NUNCA carregar em contexto público)
- Sobre mim (Agno) - personalidade e evolução
- Sobre meu humano - preferências e contexto
- Projetos importantes
- Pessoas importantes
- Lições aprendidas
- Decisões importantes

## Adaptações Brasileiras

1. **Idioma**: Português brasileiro nativo
2. **Gírias moderadas**: "valeu", "legal", "bora", etc.
3. **Contexto cultural**: Compreensão de informalidade brasileira
4. **Formatação Discord**: Instruções específicas para markdown Discord
5. **Emojis**: Uso natural de reações em comunicações brasileiras

## Como Usar

Copie os templates para a raiz do workspace:

```bash
cp src/templates/SOUL.md .
cp src/templates/USER.md .
cp src/templates/IDENTITY.md .
cp src/templates/TOOLS.md .
cp src/templates/HEARTBEAT.md .
cp src/templates/AGENTS.md .
cp src/templates/MEMORY.md .
```

Personalize cada template conforme necessário para sua instância do Agno.

## Diferenças dos Templates Originais OpenClaw

| Original | Agno Discord | Principal Mudança |
|----------|--------------|-------------------|
| Genérico | Discord-específico | Contexto de plataforma |
| Inglês | Português BR | Localização completa |
| Assistente pessoal | Bot de comunidade | Escopo social expandido |
| Heartbeat genérico | Monitoramento Discord | Tarefas específicas Discord |

## Referências

Baseado em templates OpenClaw originais:
- `openclaw/docs/reference/templates/` (instalação local do OpenClaw)

---

**Criado para**: Agente Discord Agno
**Localização**: `src/templates/`
**Data**: 2026-02-17
