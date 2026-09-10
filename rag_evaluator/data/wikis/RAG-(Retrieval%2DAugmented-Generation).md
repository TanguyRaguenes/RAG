
[[_TOC_]]

# 1° Introduction

Le RAG (Retrieval-Augmented Generation) permet de fournir des informations complémentaires à un LLM afin d'améliorer ses réponses.

Pour cela, il recherche des documents pertinents dans une base de connaissances et les ajoute au contexte envoyé au modèle.

![{B03F6A80-5800-46D6-8CE2-4AEEEA4EC08E}.png](/.attachments/{B03F6A80-5800-46D6-8CE2-4AEEEA4EC08E}-4ada41a1-9e11-4463-a984-4dd185d8bbe6.png)


# 2° Vocabulaire

|Terme| Description |
|--|--|
| LLM | Modèle ( = IA) chargé de générer la réponse. |
| Document | Fichier ou contenu à indexer dans la base de connaissances. |
| Chunk | Portion d'un document. |
| Chunking | Découpage d'un document en plusieurs chunks. |
| Embedding | Représentation vectorielle d'un texte. |
| Ingestion | Ajout d'un document dans la base de connaissances. |
| Retrieval | Recherche des chunks les plus pertinents. |
| Reranking | Tri des résultats pour améliorer leur pertinence. |
| Base vectorielle | Base de données utilisée pour stocker les embeddings. |
| Collection | Ensemble de données stockées dans la base vectorielle. |
| Payload | Métadonnées associées à un chunk. |



# 3° Architecture globale

Le RAG repose sur plusieurs composants qui collaborent pour indexer les documents et effectuer les recherches sémantiques.

- L'orchestrateur pilote les différentes étapes du traitement.
- L'embedder génère les embeddings des documents et des requêtes utilisateur.
- La base vectorielle stocke les embeddings ainsi que leurs métadonnées.
- Le retriever recherche les chunks les plus pertinents dans la base vectorielle.
- Le reranker réordonne les résultats afin d'améliorer leur pertinence.

Le schéma ci-dessous présente les interactions entre ces différents composants :

![{2650A151-3ED8-462E-8343-0257983BB8B7}.png](/.attachments/{2650A151-3ED8-462E-8343-0257983BB8B7}-663786e1-5c67-4993-ae56-dd5e3224d0b3.png)
_Le schéma présente le fonctionnement général du RAG. Dans l'implémentation actuelle, une étape de reranking est également réalisée après le retrieval afin d'améliorer la pertinence des résultats retournés._

# 4° Flux d'ingestion

Le flux d'ingestion permet d'ajouter un document dans la base de connaissances.

Les étapes sont les suivantes :

1. Réception du document.
2. Découpage en chunks.
3. Génération des embeddings.
4. Stockage des chunks et des embeddings dans Qdrant.

```text
Document
   ↓
Chunking
   ↓
Embedding
   ↓
Qdrant
```


# 5° Flux de recherche sémantique

Le flux de recherche sémantique permet de retrouver les chunks les plus pertinents à partir d'une requête utilisateur.

Les étapes sont les suivantes :

1. Réception de la requête.
2. Génération de son embedding.
3. Recherche dans Qdrant.
4. Reranking des résultats.
5. Retour des chunks les plus pertinents.

```text
Question
   ↓
Embedding
   ↓
Retrieval
   ↓
Reranking
   ↓
Résultats
```

# 6° Description des composants

| Composant | Rôle | Entrées | Sorties | Implémentation |
|------------|------|----------|----------|----------------|
| **ChunkingService** | Découpe les documents en chunks. | Document à indexer. | Liste de chunks. | Découpe le document selon la stratégie configurée. |
| **EmbeddingService** | Génère les embeddings des documents et des requêtes utilisateur. | Texte à vectoriser. | Embedding. | Appelle un provider externe pour générer les embeddings. |
| **RetrievalService** | Recherche les chunks les plus pertinents dans la base vectorielle. | Embedding de la requête, nombre maximum de résultats, filtres éventuels. | Liste de chunks avec leur score de similarité. | Effectue une recherche vectorielle dans Qdrant. |
| **RerankingService** | Réordonne les résultats afin d'améliorer leur pertinence. | Question utilisateur, liste des chunks récupérés, nombre maximum de résultats. | Liste de chunks réordonnée. | Appelle un provider externe pour calculer les scores de pertinence puis trier les chunks. |
| **IngestOrchestratorService** | Orchestre le flux d'ingestion. | Document à indexer. | Chunks enregistrés dans Qdrant. | Exécute les étapes de chunking, embedding et stockage. |
| **SemanticRetrievalOrchestratorService** | Orchestre le flux de recherche sémantique. | Requête utilisateur. | Chunks pertinents. | Exécute les étapes d'embedding, retrieval et reranking. |

# 7° API

## Endpoint d'ingestion

**Méthode :** `POST`  
**Route :** `/api/v1/ai/rag/ingest`

Permet d'indexer un ou plusieurs documents dans une collection.

### Paramètres

| Paramètre | Description |
|-----------|-------------|
| CollectionName | Nom de la collection cible. |
| Documents | Liste des documents à indexer. |
| ChunkingMethod | Paramètres de découpage des documents. |

#### Documents

| Paramètre | Description |
|-----------|-------------|
| Id | Identifiant unique du document. |
| Content | Contenu textuel du document. |
| Metadata | Métadonnées associées au document. |

#### ChunkingMethod

| Paramètre | Description |
|-----------|-------------|
| IsEnabled | Active ou désactive le découpage en chunks. |
| ChunkSize | Taille maximale d'un chunk. |
| Overlap | Nombre de caractères partagés entre deux chunks consécutifs. |

### Résultat

Retourne un objet `IsiIngestQueryResult` contenant un dictionnaire `Results`.
Les valeurs du dictionnaire correspondent aux réponses des différents services du pipeline.

| Clé | Description |
|-----|-------------|
| `chunkingResponse` | Résultat du découpage des documents en chunks. |
| `embeddingResponse` | Résultat de la génération des embeddings. |
| `vectorStoreResponse` | Résultat du stockage des chunks vectorisés dans Qdrant. |

### Exemple de requête

```json
{
  "collectionName": "<COLLECTION_NAME>",
  "documents": [
    {
      "id": "<TICKET_ID_1>",
      "content": "Ticket <TICKET_ID_1>\nProblématique : <REDACTED_TICKET_CONTENT>\nRésolution : <REDACTED_TICKET_CONTENT>",
      "metadata": {
        "ticketNumber": "<TICKET_ID_1>",
        "noAppel": "<TICKET_NUMBER_1>",
        "nature": "INC",
        "priority": "14_JOURS",
        "team": "<TEAM_NAME>",
        "severity": "Plusieurs personnes",
        "blocking": "Mineur",
        "qualifier": "ASSISTANCE",
        "category": "<INTERNAL_CATEGORY>"
      }
    },
    {
      "id": "<TICKET_ID_2>",
      "content": "Ticket <TICKET_ID_2>\nProblématique : <REDACTED_TICKET_CONTENT>\nRésolution : <REDACTED_TICKET_CONTENT>",
      "metadata": {
        "ticketNumber": "<TICKET_ID_2>",
        "noAppel": "<TICKET_NUMBER_2>",
        "nature": "INC",
        "priority": "14_JOURS",
        "team": "<TEAM_NAME>",
        "severity": "Plusieurs personnes",
        "blocking": "Mineur",
        "qualifier": "DYSF\\PRODUIT",
        "category": "<INTERNAL_CATEGORY>"
      }
    },
    {
      "id": "<TICKET_ID_3>",
      "content": "Ticket <TICKET_ID_3>\nProblématique : <REDACTED_TICKET_CONTENT>\nRésolution : <REDACTED_TICKET_CONTENT>",
      "metadata": {
        "ticketNumber": "<TICKET_ID_3>",
        "noAppel": "<TICKET_NUMBER_3>",
        "nature": "INC",
        "priority": "14_JOURS",
        "team": "<TEAM_NAME>",
        "severity": "VIP",
        "blocking": "Mineur",
        "qualifier": "ASSISTANCE",
        "category": "<INTERNAL_CATEGORY>"
      }
    },
    ...
  ],
  "chunkingMethod": {
    "isEnabled": true,
    "chunkSize": 200,
    "overlap": 40
  }
}
```
### Exemple de réponse

```json
{
  "results": {
    "chunkingResponse": {
      "chunks": [
        {
          "documentId": "<TICKET_ID_1>",
          "index": 1,
          "totalChunks": 3,
          "content": "Ticket <TICKET_ID_1>..."
        },
        {
          "documentId": "<TICKET_ID_1>",
          "index": 2,
          "totalChunks": 3,
          "content": "<REDACTED_TICKET_CONTENT>"
        },
        "..."
      ]
    },
    "embeddingResponse": {
      "data": [
        {
          "documentId": "<TICKET_ID_1>",
          "chunkContent": "Ticket <TICKET_ID_1>...",
          "chunkIndex": 1,
          "totalChunks": 3,
          "embeddingIndex": 0,
          "embedding": [
            0.015640259,
            0.020385742,
            -0.027801514,
            "..."
          ]
        },
        {
          "documentId": "<TICKET_ID_1>",
          "chunkContent": "<REDACTED_TICKET_CONTENT>",
          "chunkIndex": 2,
          "totalChunks": 3,
          "embeddingIndex": 1,
          "embedding": [
            0.0006108284,
            0.02748108,
            -0.000031530857,
            "..."
          ]
        },
        "..."
      ],
      "model": "text-embedding-3-small",
      "usage": {
        "promptTokens": 5795,
        "totalTokens": 5795
      }
    },
    "vectorStoreResponse": {
      "response": "Ingestion des documents terminée avec succès"
    }
  }
}
```

---

## Endpoint de recherche sémantique

**Méthode :** `POST`  
**Route :** `/api/v1/ai/rag/semantic-retrieval`

Permet de rechercher les chunks les plus pertinents dans une collection.

### Paramètres

| Paramètre | Description |
|-----------|-------------|
| Query | Texte de la recherche. |
| CollectionName | Nom de la collection cible. |
| RetrievalTopK | Nombre maximum de chunks récupérés lors du retrieval. |
| RerankingTopK | Nombre maximum de chunks conservés après reranking. |
| MetadataFilters | Filtres appliqués sur les métadonnées. |

#### MetadataFilters

| Paramètre | Description |
|-----------|-------------|
| MetadataName | Nom de la métadonnée ciblée. |
| IsIncluded | Indique si les valeurs doivent être incluses ou exclues. |
| MetadataValues | Valeurs utilisées par le filtre. |

### Résultat

Retourne un objet `IsiSemanticRetrievalQueryResult` contenant un dictionnaire `Results`.
Les valeurs du dictionnaire correspondent aux réponses des différents services du pipeline.

| Clé | Description |
|-----|-------------|
| `embeddingResponse` | Résultat de la génération de l'embedding de la requête utilisateur. |
| `retrievalResponse` | Chunks retrouvés dans Qdrant avant reranking. |
| `rerankingResponse` | Chunks réordonnés après reranking. |
| `retrievedDocumentIdsAfterReranking` | Liste des identifiants des documents conservés après reranking, sans doublon. |

### Exemple de requête

```json
{
  "query": "Erreur Oracle lors de la connexion à la base de données",
  "collectionName": "<COLLECTION_NAME>",
  "retrievalTopK": 6,
  "rerankingTopK": 3,
  "metadataFilters": [
    {
      "metadataName": "team",
      "isIncluded": true,
      "metadataValues": [
        "<TEAM_NAME_1>","<TEAM_NAME_2>"
      ]
    },
    {
      "metadataName": "qualifier",
      "isIncluded": false,
      "metadataValues": [
        "EVOLUTION\\PRODUIT","DYSF\\PRODUIT"
      ]
    }
  ]
}
```

### Exemple de réponse
```json
```json
{
  "results": {
    "embeddingResponse": {
      "data": [
        {
          "documentId": "query",
          "chunkContent": "Erreur Oracle lors de la connexion à la base de données",
          "chunkIndex": 0,
          "totalChunks": 0,
          "embeddingIndex": 0,
          "embedding": [
            -0.030227661,
            -0.004508972,
            0.10430908,
            "..."
          ]
        }
      ],
      "model": "text-embedding-3-small",
      "usage": {
        "promptTokens": 11,
        "totalTokens": 11
      }
    },
    "retrievalResponse": {
      "chunks": [
        {
          "id": "<TICKET_ID_4>",
          "score": 0.6731993556022644,
          "metadata": {
            "ticketNumber": "<TICKET_ID_4>",
            "noAppel": "<TICKET_NUMBER_4>",
            "severity": "Plusieurs personnes",
            "totalChunks": 1,
            "category": "<INTERNAL_CATEGORY>",
            "documentId": "<TICKET_ID_4>",
            "blocking": "Mineur",
            "chunkContent": "Ticket <TICKET_ID_4>...",
            "qualifier": "ASSISTANCE",
            "nature": "INC",
            "priority": "14_JOURS",
            "chunkIndex": 1,
            "team": "<TEAM_NAME>"
          }
        },
        {
          "id": "<TICKET_ID_5>",
          "score": 0.567376971244812,
          "metadata": {
            "ticketNumber": "<TICKET_ID_5>",
            "chunkContent": "Ticket <TICKET_ID_5>...",
            "...": "..."
          }
        },
        "..."
      ]
    },
    "rerankingResponse": {
      "rerankedChunks": [
        {
          "id": "<TICKET_ID_4>",
          "retrievalScore": 0.6731993556022644,
          "rerankingScore": 0.19348463,
          "metadata": {
            "ticketNumber": "<TICKET_ID_4>",
            "noAppel": "<TICKET_NUMBER_4>",
            "severity": "Plusieurs personnes",
            "totalChunks": 1,
            "category": "<INTERNAL_CATEGORY>",
            "documentId": "<TICKET_ID_4>",
            "blocking": "Mineur",
            "chunkContent": "Ticket <TICKET_ID_4>...",
            "qualifier": "ASSISTANCE",
            "nature": "INC",
            "priority": "14_JOURS",
            "chunkIndex": 1,
            "team": "<TEAM_NAME>"
          }
        },
        {
          "id": "<TICKET_ID_6>",
          "retrievalScore": 0.5223541855812073,
          "rerankingScore": -0.07246905,
          "metadata": {
            "ticketNumber": "<TICKET_ID_6>",
            "chunkContent": "Ticket <TICKET_ID_6>...",
            "...": "..."
          }
        },
        "..."
      ],
      "model": "jina-reranker-v3",
      "objectType": "",
      "usage": {
        "totalTokens": 750
      },
      "results": [
        {
          "originalIndex": 0,
          "score": 0.19348463
        },
        {
          "originalIndex": 2,
          "score": -0.07246905
        },
        "..."
      ]
    },
    "retrievedDocumentIdsAfterReranking": [
      "<TICKET_ID_4>",
      "<TICKET_ID_6>",
      "<TICKET_ID_5>"
    ]
  }
}
```

# 8° DTO du pipeline RAG


## Chunking

| Paramètre | Description |
|------------|-------------|
| Documents | Documents à découper. |
| ChunkSize | Taille maximale d'un chunk. |
| Overlap | Nombre de caractères partagés entre deux chunks consécutifs. |
| Résultat | Liste de chunks contenant l'identifiant du document, l'index du chunk, le nombre total de chunks et son contenu. |

## Embedding

| Paramètre | Description |
|------------|-------------|
| Chunks | Liste des chunks à vectoriser. |
| Résultat | Liste d'embeddings associés aux chunks ainsi que le modèle utilisé et les informations de consommation retournées par le provider. |

## Retrieval

| Paramètre | Description |
|------------|-------------|
| CollectionName | Collection Qdrant utilisée pour la recherche. |
| QueryEmbedding | Embedding représentant la requête utilisateur. |
| TopK | Nombre maximum de résultats retournés. |
| MetadataFilters | Filtres appliqués sur les métadonnées. |
| Résultat | Liste des chunks retrouvés avec leur score de similarité et leurs métadonnées. |

## Reranking

| Paramètre | Description |
|------------|-------------|
| Query | Question utilisateur. |
| RetrievedChunks | Chunks retournés par le retrieval. |
| TopK | Nombre maximum de résultats conservés après reranking. |
| Résultat | Liste des chunks réordonnés avec leur score de pertinence ainsi que le modèle utilisé et les informations de consommation retournées par le provider. |

## Vector Store

| Paramètre | Description |
|------------|-------------|
| CollectionName | Collection dans laquelle stocker les données. |
| Documents | Documents vectorisés à indexer. |
| Résultat | Réponse retournée par le vector store après l'indexation. |

# 9° Qdrant

Qdrant est la base vectorielle utilisée par le RAG. Elle tourne dans un service Windows et non dans un container.

Pour pouvoir installer Qdrant sur son poste il suffit de télécharger le zip suivant "qdrant-x86_64-pc-windows-msvc.zip" :
https://github.com/qdrant/qdrant/releases
De décompresser et enfin de lancer l'exécutable.

<span style="color:red">ATTENTION</span> par défaut Qdrant fonctionne sur le port 6333 or les ports 6300 - 6399 sont réservés pour les crawlers. Il faudra donc modifier le port par défaut en créant un fichier `config.yaml` dans le dossier avec l’exécutable :
![{0B06ADFB-41C5-47EA-8A57-2DB53797A53D}.png](/.attachments/{0B06ADFB-41C5-47EA-8A57-2DB53797A53D}-78f48f67-e390-4fe1-945d-24d22b261cb0.png)
```yaml
service:
  host: 0.0.0.0

  # Port HTTP (API REST + Dashboard)
  http_port: 7000
  
  # Port gRPC
  grpc_port: 7001
```
Puis en lançant Qdrant avec la commande suivante (après s'être positionné dans le dossier avec l'exécutable) :
```bash
qdrant.exe --config-path config.yaml
```

Bien penser aussi à modifier le port dans le fichier : `Services\AI\<PROJECT_NAME>\appsettings.Development.json`.

![{39ED6C17-A202-47BE-A3D6-80C727551B14}.png](/.attachments/{39ED6C17-A202-47BE-A3D6-80C727551B14}-d6803cd2-dc1d-41f6-ac51-e47a5791929e.png)

Le rôle de Qdrant est de stocker les embeddings générés lors de l'ingestion des documents et de permettre leur recherche lors d'une requête utilisateur.

À noter que le terme utilisé par Qdrant pour désigner une entrée est point (*Point*). Les métadonnées associées à cette entrée sont appelées payload.

```text
Document
  └─ Chunk 1 -> Embedding -> Point Qdrant
  └─ Chunk 2 -> Embedding -> Point Qdrant
  └─ Chunk 3 -> Embedding -> Point Qdrant
```

## Données stockées

Pour chaque chunk, les informations suivantes sont enregistrées :

- L'identifiant du chunk (GUID)
- L'embedding associé.
- Les métadonnées du document.

Exemple :

![{257B318B-02D4-44D9-AEDE-7318ABE2CE1A}.png](/.attachments/{257B318B-02D4-44D9-AEDE-7318ABE2CE1A}-f4a83717-77ff-42cf-8335-5961e9ef3088.png)

## Liens utiles

- Documentation des vecteurs : https://qdrant.tech/documentation/manage-data/vectors/
- Documentation des payloads : https://qdrant.tech/documentation/manage-data/payload/

## Visualiser les collections ainsi que leur contenu avec Postman

![{9CB91666-ECAB-48CB-8928-171684095C5A}.png](/.attachments/{9CB91666-ECAB-48CB-8928-171684095C5A}-67985102-9077-402d-8dc3-6b6479a7d6e3.png)
![{4936AD08-A567-469B-BF23-36ABA8B3C8CE}.png](/.attachments/{4936AD08-A567-469B-BF23-36ABA8B3C8CE}-1f8f5ddf-402f-4ddb-89bb-14c1c0ee5b07.png)

# 10° Exemples de configuration des modèles

Afin de réaliser les tests/démos, nous disposons actuellement de modèles hébergés sur Microsoft Foundry (voir avec le service Architecture).

Dans l'attente de l'implémentation du composant de gestion centralisée des fournisseurs de services IA (OpenAI, Azure OpenAI, Jina, etc.) via un mécanisme de templates, les paramètres de connexion peuvent être renseignés directement dans le fichier `appsettings.json` du projet `<PROJECT_NAME>`.

Ces paramètres sont ensuite injectés dans les différents services via le mécanisme d'injection de dépendances et l'interface IConfiguration.

L'exemple ci-dessous illustre une configuration utilisant Microsoft Foundry pour les embeddings et Jina AI (fournisseur proposant une offre gratuite) pour le reranking :

```json

    "Embedding": {
        "Endpoint": "<AZURE_OPENAI_ENDPOINT>",
        "ApiKey": "${AZURE_OPENAI_API_KEY}",
        "Model": "text-embedding-3-small",
        "UrlTemplate": "{Endpoint}/openai/deployments/{Model}/embeddings?api-version=2024-02-01",
        "Dimensions": 768,
        "MaxConcurrency": 5,
        "RemoteApiUrl": "<CLOUDFLARE_TUNNEL_URL>/embed"
    },

    "Reranking": {
        "Endpoint": "https://api.jina.ai/",
        "ApiKey": "${JINA_API_KEY}",
        "Model": "jina-reranker-v3",
        "UrlTemplate": "{Endpoint}/v1/rerank"

    }
```

# 11° Gestion du multilangue

Le RAG ne gère qu'une seule langue afin de limiter la complexité et l'espace de stockage. Pour supporter plusieurs langues, le service interne de traduction via LLM `<TRANSLATION_SERVICE>` devra être utilisé :

À l'ingestion : traduction des documents avant indexation.
À la recherche : traduction de la requête utilisateur avant la recherche sémantique.

Ainsi, les documents et les requêtes sont toujours traités dans une langue unique de référence.
