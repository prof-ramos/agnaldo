---
summary: "Template de memória curada para agente Discord"
read_when:
  - Bootstrapping um workspace manualmente
---

# MEMORY.md - Sua Memória de Longo Prazo

_Este arquivo é sua memória persistente — o que você carrega entre sessões. Curado, não cru._

## ⚠️ SEGURANÇA IMPORTANTE

- **Carregue APENAS em sessões privadas/DM** (sessões diretas com seu humano)
- **NUNCA carregue em contextos públicos** (canais Discord públicos, grupos, chats com outras pessoas)
- Este arquivo contém contexto pessoal que **NÃO deve vazar** para estranhos
- Em sessões compartilhadas, NÃO leia este arquivo automaticamente

## Validações Técnicas Obrigatórias

Antes de carregar `MEMORY.md`, valide programaticamente:

1. `session.type === "DM"` (ou equivalente no runtime).
2. `session.participants_count == 2` (você + seu humano).
3. `session.guild_id` ausente/nulo.
4. Se qualquer validação falhar, **não carregar** este arquivo e registrar apenas evento técnico (sem conteúdo sensível).

## Como Usar Este Arquivo

### O que gravar aqui

- **Decisões importantes** — Escolhas que afetam como você opera
- **Lições aprendidas** — Coisas que você aprendeu pela experiência
- **Preferências do usuário** — O que seu humano gosta/não gosta
- **Contexto de projetos** — Informação vital sobre projetos em andamento
- **Relacionamentos** — Pessoas importantes, como interagir com elas
- **Opiniões formadas** — Suas opiniões sobre coisas (sim, você tem opiniões)

### O que NÃO gravar aqui

- Segredos e senhas (use arquivos criptografados ou separados)
- Logs brutos de conversas (vão para `memory/YYYY-MM-DD.md`)
- Informação temporária ou obsoleta
- Coisas que outros não deveriam ver (por isso NUNCA carregar em público!)

### Compliance e Proteção de Dados

- Aplique princípio de minimização: registre apenas o que for necessário para utilidade futura.
- Evite armazenar PII sensível de terceiros sem base legal e consentimento apropriado.
- Prefira pseudonimização (IDs/hash) quando nomes completos não forem indispensáveis.
- Se for necessário guardar dados sensíveis, use armazenamento criptografado e controle de acesso estrito.
- Defina processo de retenção e descarte: remover informações desatualizadas e sem finalidade legítima.

## Seção de Memórias

### Sobre Mim (Agno)

_Esta seção é sobre quem você é e como você evoluiu._

- **Personalidade**:_(descubra com o tempo)_
- **Coisas que aprendi**:_(vá adicionando)_
- **Opiniões formadas**:_(o que você gosta/desgosta)_

### Sobre Meu Humano

_Coisas importantes sobre a pessoa que você ajuda._

- **Estilo de comunicação**:
- **Preferências**:
- **Coisas que irritam**:
- **Coisas que fazem rir**:
- **Metas e projetos**:

### Projetos Importantes

_Contexto sobre projetos que seu humano se importa._

#### [Nome do Projeto]

- **Status**:
- **Descrição**:
- **Próximos passos**:
- **Notas importantes**:

### Pessoas Importantes

_Contexto sobre pessoas que seu humano interage._

⚠️ **ATENÇÃO LGPD**: não armazene dados pessoais de terceiros sem necessidade legítima, consentimento quando aplicável e proteção adequada.

#### [Nome]

- **Quem é**:
- **Como interagir**:
- **Contexto importante**:
- **Preferências**:

### Lições Aprendidas

_Coisas que você aprendeu pela experiência difícil._

#### [Data] - [Título da Lição]

_Descrição da lição e como aplicar no futuro._

### Decisões Importantes

_Escolhas que afetam como você opera._

#### [Data] - [Título da Decisão]

_Decisão tomada e o raciocínio por trás dela._

---

## Manutenção

Periodicamente (durante heartbeats ou sessões tranquilas):

1. Leia através de `memory/YYYY-MM-DD.md` recente
2. Identifique coisas que valem a pena manter longo prazo
3. Adicione a este arquivo nas seções apropriadas
4. Remova info desatualizada que não é mais relevante

Pense nisso como um humano revisando seu diário e atualizando seu modelo mental. Arquivos diários são notas cruas; este é sabedoria curada.

---

_Lembre-se: Memória é limitada. Se é importante, escreva. Notas mentais não sobrevivem a restarts._
