# Knowledge Graph Service

Sistema avançado de Knowledge Graph para o Agnaldo com extração automática de entidades e relacionamentos.

## Visão Geral

O `GraphService` fornece operações avançadas de grafo:

- **Extração automática de entidades** via LLM
- **Relacionamentos semânticos** detectados automaticamente
- **Consultas avançadas** (subgraph, centralidade, clusters)
- **Exportação** para visualização (D3, Cytoscape, GraphML)
- **Integração** com sistema de isolamento de memória

## Uso Básico

### Inicialização

```python
from src.knowledge import GraphService

graph_service = GraphService(
    user_id="user123",
    db_pool=db_pool,
    openai_client=openai_client,
)
```

### Adicionando Conversa ao Grafo

```python
result = await graph_service.add_conversation_to_graph(
    user_message="Quais são os direitos fundamentais na Constituição?",
    assistant_response="Os direitos fundamentais estão no Art. 5º...",
    session_id="session_123",
    auto_extract=True,  # Extrai entidades automaticamente
)

print(f"Nós criados: {result['nodes_created']}")
print(f"Arestas criadas: {result['edges_created']}")
print(f"Entidades: {result['entities']}")
```

### Busca Semântica

```python
results = await graph_service.semantic_search(
    query="direitos constitucionais",
    include_context=True,  # Inclui vizinhos
    limit=10,
)

for result in results:
    print(f"{result['label']} (similaridade: {result['similarity']:.2f})")
    print(f"  Vizinhos: {result['neighbor_count']}")
```

## Tipos de Entidades

```python
from src.knowledge import EntityType

class EntityType(Enum):
    PERSON = "person"           # Pessoas
    ORGANIZATION = "organization"  # Organizações
    LOCATION = "location"       # Locais
    CONCEPT = "concept"         # Conceitos abstratos
    EVENT = "event"            # Eventos
    TOPIC = "topic"            # Tópicos
    DOCUMENT = "document"      # Documentos
    LAW = "law"                # Leis (contexto jurídico)
    CASE = "case"              # Casos jurídicos
    SUBJECT = "subject"        # Matérias de concurso
```

## Tipos de Relacionamentos

```python
from src.knowledge import RelationType

class RelationType(Enum):
    RELATED_TO = "related_to"    # Relacionamento genérico
    PART_OF = "part_of"         # Parte de
    HAS_PROPERTY = "has_property"  # Tem propriedade
    MENTIONS = "mentions"       # Menciona
    STUDIES = "studies"         # Estuda
    KNOWS = "knows"             # Conhece
    WORKS_AT = "works_at"       # Trabalha em
    LOCATED_IN = "located_in"   # Localizado em
    PRECEDES = "precedes"       # Precede
    FOLLOWS = "follows"         # Segue
    DEPENDS_ON = "depends_on"   # Depende de
    REFERENCES = "references"   # Referencia
    APPLIES = "applies"         # Aplica
```

## Consultas Avançadas

### Subgrafo

```python
subgraph = await graph_service.get_subgraph(
    node_id="node_123",
    depth=2,       # Profundidade da expansão
    max_nodes=50,  # Máximo de nós
)

# Retorna:
# {
#   "nodes": [{"id", "label", "type", "properties"}],
#   "edges": [{"id", "source", "target", "type", "weight"}]
# }
```

### Centralidade

```python
# Nós mais conectados (degree centrality)
central_nodes = await graph_service.get_central_nodes(
    metric="degree",
    limit=10,
)

# Métricas disponíveis:
# - "degree": Número de conexões
# - "betweenness": Nós em caminhos mais curtos
```

### Clusters

```python
clusters = await graph_service.find_clusters(
    min_size=3,  # Tamanho mínimo de cluster
)

for cluster in clusters:
    print(f"Cluster {cluster['component_id']}: {cluster['size']} nós")
    for node in cluster['nodes']:
        print(f"  - {node['label']}")
```

### Caminhos

```python
# Usando o KnowledgeGraph subjacente
path = await graph_service._graph.find_path(
    source_id="node_1",
    target_id="node_2",
    max_depth=5,
)

if path:
    print(f"Caminho encontrado: {' -> '.join(path)}")
```

## Exportação

### JSON (D3.js)

```python
graph_data = await graph_service.export_graph(
    format="json",
    include_properties=True,
)

# Uso com D3.js:
# d3.forceSimulation(graph_data.nodes)
#   .force("link", d3.forceLink(graph_data.links).id(d => d.id))
```

### Cytoscape.js

```python
cytoscape_data = await graph_service.export_graph(format="cytoscape")

# Uso com Cytoscape.js:
# cytoscape({ elements: cytoscape_data.elements })
```

### GraphML (Gephi)

```python
graphml = await graph_service.export_graph(format="graphml")

# Salvar para Gephi:
with open("graph.graphml", "w") as f:
    f.write(graphml)
```

## Resumo do Grafo

```python
summary = await graph_service.get_graph_summary()

print(f"Nós: {summary['node_count']}")
print(f"Arestas: {summary['edge_count']}")
print(f"Clusters: {summary['cluster_count']}")

for node in summary['top_nodes']:
    print(f"  {node['label']}: score {node['score']}")
```

## Integração com Isolamento

O `GraphService` integra automaticamente com o sistema de isolamento:

```python
from src.memory import UserContext

async with UserContext("user123"):
    # Todas as operações são isoladas para user123
    graph_service = GraphService(user_id="user123", db_pool=db_pool)
    await graph_service.add_conversation_to_graph(...)
```

## Exemplo Completo

```python
import asyncio
from src.knowledge import GraphService, EntityType, RelationType
from src.memory import UserContext

async def main():
    # Inicializar
    graph_service = GraphService(
        user_id="student_123",
        db_pool=db_pool,
    )

    # Adicionar conversa
    result = await graph_service.add_conversation_to_graph(
        user_message="Preciso estudar Direito Constitucional para o concurso do STF",
        assistant_response="Vou ajudar você a estudar Direito Constitucional...",
        session_id="study_session_1",
    )

    print(f"Entidades extraídas: {len(result['entities'])}")
    print(f"Relacionamentos: {len(result['relations'])}")

    # Buscar semântica
    results = await graph_service.semantic_search(
        query="constituição federal",
        include_context=True,
    )

    # Obter resumo
    summary = await graph_service.get_graph_summary()
    print(f"Total de nós: {summary['node_count']}")

    # Exportar para visualização
    graph_data = await graph_service.export_graph(format="d3")

asyncio.run(main())
```

## Arquitetura

```
┌─────────────────────────────────────────────────────────────┐
│                       GraphService                           │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────────┐  ┌─────────────────┐                   │
│  │ Entity Extract  │  │ Relation Extract│   (LLM-powered)  │
│  └─────────────────┘  └─────────────────┘                   │
│           │                   │                              │
│           └───────────┬───────┘                              │
│                       ▼                                      │
│  ┌─────────────────────────────────────────────────────────┐│
│  │                    KnowledgeGraph                        ││
│  │  ┌───────────────┐  ┌───────────────┐                   ││
│  │  │   add_node    │  │   add_edge    │                   ││
│  │  └───────────────┘  └───────────────┘                   ││
│  │  ┌───────────────┐  ┌───────────────┐                   ││
│  │  │ search_nodes  │  │  find_path    │                   ││
│  │  └───────────────┘  └───────────────┘                   ││
│  └─────────────────────────────────────────────────────────┘│
│                       │                                      │
│                       ▼                                      │
│  ┌─────────────────────────────────────────────────────────┐│
│  │           PostgreSQL + pgvector                          ││
│  │  ┌─────────────────┐  ┌─────────────────┐               ││
│  │  │ knowledge_nodes │  │ knowledge_edges │               ││
│  │  └─────────────────┘  └─────────────────┘               ││
│  └─────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────┘
```

## Troubleshooting

### Erro: "User ID cannot be empty"

Verifique se o user_id está sendo passado corretamente:

```python
# ❌ Errado
graph_service = GraphService(user_id="", db_pool=db_pool)

# ✅ Correto
graph_service = GraphService(user_id="user123", db_pool=db_pool)
```

### Extração de entidades retorna vazia

- Verifique se o OpenAI client está configurado
- Verifique os logs para erros de API
- Teste com texto mais longo/mais claro

### Consultas lentas

- Adicione índices no banco:
  ```sql
  CREATE INDEX idx_nodes_user ON knowledge_nodes(user_id);
  CREATE INDEX idx_edges_source ON knowledge_edges(source_id);
  CREATE INDEX idx_edges_target ON knowledge_edges(target_id);
  ```
- Use `max_nodes` para limitar subgraphs
- Crie índices pgvector para busca semântica
