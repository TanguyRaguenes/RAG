# Checklist de refactoring architectural d'un microservice

Utiliser cette grille pour classer le code avant de le déplacer et pour vérifier le résultat final.

## Matrice des couches

| Couche | Responsabilités autorisées | Signaux d'alerte |
|---|---|---|
| `api/routers` | HTTP, `Depends`, DTO d'entrée/sortie, status code | SQL, SDK, calcul métier, quota, persistance, orchestration multi-étapes |
| `api/dependencies.py` | construction/injection, accès aux ressources du lifespan | règle métier, transformation de réponse, requête SQL directe |
| `services` | cas d'usage, orchestration, politique métier | `Request`, `Response`, `HTTPException`, `st.*`, `chromadb.Collection` |
| `dal/clients` | HTTP et SDK externes, validation de réponse fournisseur | tri métier, quota, prompt, choix fonctionnel |
| `dal/repositories` | requêtes SQL/vectorielles, mapping persistance | orchestration, policy de retrieval, DTO HTTP |
| `dal/files` | lecture/écriture de fichiers | règle métier d'ingestion ou décision API |
| `domain/models` | concepts métier indépendants | FastAPI, Pydantic de transport, `httpx`, SQL, Streamlit |
| `schemas` | DTO Pydantic HTTP/interservices | accès réseau, règle métier, ressource SDK |
| `core` | config, exceptions, logs, métriques, télémétrie | use case métier, repository, router |

## Router fin

- [ ] Recevoir un schéma typé.
- [ ] Dépendre d'un service ou cas d'usage.
- [ ] Appeler une opération métier claire.
- [ ] Retourner un schéma typé.
- [ ] Ne pas créer directement de client HTTP, pool SQL ou collection vectorielle.
- [ ] Ne pas gérer quota, persistance, métriques métier détaillées ou fournisseur.
- [ ] Ne pas contenir de `try/finally` métier complexe.

## Service

- [ ] Exprimer un cas d'usage identifiable.
- [ ] Dépendre de contrats injectés plutôt que de SDK concrets.
- [ ] Ne pas importer FastAPI ou Streamlit.
- [ ] Garantir le cleanup des ressources métier.
- [ ] Garder les règles de tri, quota, sélection et agrégation.
- [ ] Ne pas parser directement une réponse HTTP brute.
- [ ] Ne pas devenir un module monolithique regroupant des domaines indépendants.

## DAL

- [ ] Encapsuler URL, headers, payload fournisseur, SQL, collection ou chemin de fichier.
- [ ] Configurer timeout et gestion des erreurs externes.
- [ ] Valider JSON et contrat avant de retourner.
- [ ] Retourner DTO ou modèles indépendants du SDK.
- [ ] Ne pas exposer `httpx.Response`, ligne SQL brute ou collection ChromaDB.
- [ ] Ne pas implémenter une politique métier cachée.
- [ ] Réutiliser les clients et pools lorsque le cycle de vie le justifie.

## Domaine et schémas

- [ ] Les requêtes/réponses HTTP sont dans `schemas`.
- [ ] Les payloads interservices sont validés par des schémas.
- [ ] Les modèles domaine ne dépendent d'aucun framework.
- [ ] Les contraintes de collections liées sont validées.
- [ ] Les champs numériques externes refusent booléens, NaN et infinis si nécessaire.
- [ ] Aucun modèle n'est dupliqué sans raison.
- [ ] Un dossier domaine vide est accepté si le métier ne nécessite pas de modèle dédié.

## POO et interfaces

- [ ] Chaque classe possède un état, des dépendances ou une responsabilité cohérente.
- [ ] Chaque `Protocol` correspond à une frontière remplacée en test ou en production.
- [ ] Les objets à cycle de vie sont construits une fois et fermés proprement.
- [ ] Les fonctions pures restent des fonctions.
- [ ] Aucune classe de `staticmethod` n'est ajoutée pour faire seulement "POO".
- [ ] La composition est préférée à l'héritage.

## Typage

- [ ] Tous les paramètres et retours publics sont annotés.
- [ ] Les lifespans et callbacks sont annotés.
- [ ] Les collections utilisent leurs types d'éléments.
- [ ] Les `dict[str, Any]` stables ont été remplacés par un contrat explicite.
- [ ] `Any` restant est limité à une frontière dynamique et validé rapidement.
- [ ] Aucun objet SDK n'est caché derrière un type vague pour contourner l'architecture.

## Simplicité et commentaires

- [ ] Les noms rendent le flux compréhensible sans commentaire narratif.
- [ ] Une fonction conserve un seul niveau d'abstraction principal.
- [ ] Les helpers ajoutés sont réutilisés ou isolent une complexité réelle.
- [ ] Les commentaires décrivent une règle ou un compromis non évident.
- [ ] Le code commenté, mort ou devenu contradictoire est supprimé.
- [ ] Les docstrings n'inventent ni retour ni exception.
- [ ] Aucun pattern ou abstraction n'est ajouté par anticipation.

## Contrats et comportement

- [ ] Routes et méthodes HTTP inchangées.
- [ ] Statuts et payloads de succès inchangés.
- [ ] Variables de configuration existantes préservées.
- [ ] Collection, table, stockage et comportement persistant préservés.
- [ ] Métriques, logs et traces existants préservés.
- [ ] Authentification et autorisation préservées.
- [ ] Les appels interservices utilisent des DTO compatibles des deux côtés.

## Tests

- [ ] Contrat HTTP du router.
- [ ] Orchestration du service avec fakes.
- [ ] Contrat et erreurs du client DAL.
- [ ] Payload externe invalide.
- [ ] Cas vide et limites de collection.
- [ ] Cleanup de session, verrou, client ou pool.
- [ ] Contrat interservice si concerné.
- [ ] Régression du comportement déplacé.

## Validation finale

```bash
uv run pytest
uv run ruff check .
uv run ruff check --select ANN app
uv run ruff format --check .
```

Depuis la racine :

```bash
git diff --check -- <microservice>
git status --short
```
