---
name: microservice-error-standardizer
description: "Cette skill doit être utilisée pour auditer, corriger ou standardiser la gestion centralisée des exceptions et des logs structurés d'un seul microservice Python du RAG. Elle couvre FastAPI, MCP et Streamlit, les erreurs DAL, les payloads publics sûrs, la redaction des logs JSON et les tests associés. Elle ne doit pas être utilisée pour une refactorisation générale, une observabilité complète avec métriques/traces, ni pour traiter plusieurs microservices simultanément."
---

# Microservice Error Standardizer

## Rôle

Standardiser les erreurs et les logs d'un microservice sans modifier son comportement métier ni ses contrats de succès.

Produire une implémentation simple à comprendre, adaptée au framework réellement utilisé et sûre pour les données internes du RAG.

## Quand utiliser cette skill

Utiliser cette skill pour un seul microservice lorsque la demande concerne principalement :

- la centralisation des exceptions custom ;
- l'ajout ou la correction des handlers d'erreur ;
- la traduction des erreurs HTTP, SQL, stockage, OIDC ou LLM ;
- l'uniformisation des statuts, slugs et payloads publics ;
- la création ou le durcissement de logs JSON custom ;
- la redaction des secrets et contenus métier dans les logs ;
- la suppression des doubles logs et l'ajustement des niveaux ;
- les tests de non-régression spécifiques aux erreurs et au logging.

Ne pas utiliser cette skill pour :

- une revue sans modification : utiliser `code-reviewer` ;
- une refactorisation générale de l'architecture ou du métier : utiliser `code-refactorer` si elle est autorisée ;
- une observabilité complète incluant Prometheus, OpenTelemetry, Grafana ou alertes : utiliser `observability-engineer` ;
- une génération de tests comme objectif principal : utiliser `test-generator` ;
- plusieurs microservices dans la même intervention : traiter chaque service séparément avec cette skill.

## Principes obligatoires

- Préserver les routes, statuts de succès, DTO de succès, métriques et traces existantes.
- Ne jamais lire ni modifier les fichiers `.env` ou les secrets.
- Ne jamais exposer `str(exception)`, `response.text`, une URL complète, une stack trace ou un détail interne dans une réponse publique.
- Ne jamais logger de bearer token, clé API, secret, cookie, code/state OAuth, question, prompt, document, chunk, embedding ou réponse LLM complète.
- Définir un seul propriétaire du log final pour éviter les doublons.
- Capturer les exceptions techniques connues à la frontière DAL ; laisser les bugs inattendus atteindre le handler global.
- Préférer une hiérarchie courte et explicite à une classe par scénario mineur.
- Utiliser des fonctions pures pour la sérialisation et la redaction ; utiliser des classes pour les exceptions et les adaptateurs avec état.
- Ne pas ajouter une abstraction ou une dépendance sans besoin concret.

Consulter `references/checklist.md` pendant l'audit et avant la validation finale.

## Décider selon le framework

### FastAPI

- Centraliser la hiérarchie dans `app/core/exceptions.py`.
- Placer l'enregistrement des handlers dans `app/api/exception_handlers.py` ou dans un module transversal existant.
- Enregistrer un handler pour l'exception applicative racine et un handler pour `Exception`.
- Conserver les erreurs natives FastAPI utiles, notamment la validation 422, sauf exigence contraire.
- Retourner un contrat stable : `slug`, `message`, `details`.

### MCP

- Centraliser la hiérarchie dans `app/core/errors.py`.
- Classifier les erreurs réseau, authentification, autorisation, quota, fournisseur et contrat.
- Retourner une erreur d'outil structurée avec `isError=true` lorsque le SDK le permet.
- Ne jamais transformer une panne en texte de succès ordinaire.

### Streamlit

- Centraliser l'affichage et la journalisation dans un composant commun.
- Convertir les erreurs réseau et de contrat en une exception applicative unique.
- Nettoyer l'état d'authentification après un HTTP 401.
- Ne pas capturer les exceptions internes de `st.stop()` ou `st.rerun()` avec un `except Exception` global.

## Workflow

### 1. Cartographier le microservice

- Identifier le framework, le point d'entrée et le cycle de vie.
- Lire `core/exceptions.py`, `core/errors.py`, `core/logging.py`, les handlers et les clients DAL.
- Rechercher `HTTPException`, `except Exception`, `logger.*`, `print`, `response.text`, `str(exception)` et les accès dynamiques aux réponses JSON.
- Lire les tests et la configuration de couverture sans lancer de modification.
- Vérifier les conventions locales avant de créer de nouveaux fichiers.

### 2. Définir la taxonomie d'erreur

- Créer une exception applicative racine avec code ou slug, statut, message public et contexte interne sûr.
- Distinguer au minimum erreur client, authentification, autorisation, ressource absente, quota, dépendance externe, contrat invalide et erreur interne lorsque ces cas existent réellement.
- Conserver les détails techniques hors de la représentation publique.
- Déplacer les exceptions dispersées dans les services vers `core`.

### 3. Centraliser la traduction

- Traduire les erreurs connues au niveau le plus proche de leur origine : timeout HTTP, connexion, statut, JSON invalide, validation Pydantic, erreur SQL ou stockage.
- Capturer uniquement les types attendus dans le DAL.
- Éviter `except Exception` dans le métier et le DAL.
- Réserver le handler inattendu de la frontière applicative au dernier recours.
- Conserver le chaînage avec `raise ... from exception` sans sérialiser la cause.

### 4. Centraliser les handlers

- Journaliser une seule fois l'erreur finale.
- Utiliser `WARNING` pour les erreurs client attendues.
- Utiliser `ERROR` pour une dépendance indisponible déjà classifiée, sans traceback par défaut.
- Utiliser `logger.exception()` uniquement pour une erreur inattendue nécessitant la pile.
- Retourner un message public constant et des détails explicitement autorisés.
- Ajouter `WWW-Authenticate: Bearer` aux erreurs HTTP 401 lorsque le framework HTTP le requiert.

### 5. Durcir le logging JSON

- Écrire sur stdout avec `logging.getLogger(__name__)`.
- Rendre `configure_json_logging()` idempotente.
- Réutiliser uniquement le handler géré par l'application sans supprimer les handlers de tests ou du framework.
- Appliquer le même formatter aux loggers Uvicorn pour FastAPI.
- Sérialiser les champs `extra` utiles et stables.
- Redacter récursivement les clés sensibles, y compris dans les objets imbriqués.
- Borner chaînes, collections, profondeur et taille JSON globale.
- Conserver uniquement le type et les emplacements de pile d'une exception inattendue, jamais son message dynamique.
- Neutraliser les access logs susceptibles d'inclure des query parameters sensibles.

### 6. Ajouter les tests ciblés

- Tester une exception applicative avec statut, slug, message public et détails sûrs.
- Tester une exception inattendue avec 500 neutre et log de pile.
- Tester la traduction timeout, connexion, HTTP, JSON et contrat invalide selon les dépendances du service.
- Tester l'absence de token, URL, body externe et contenu métier dans les réponses et logs.
- Tester la redaction récursive, la troncature et l'idempotence du logging.
- Utiliser la vraie application ASGI pour les handlers FastAPI.
- Tester `isError=true` pour MCP ou le rendu centralisé pour Streamlit.

### 7. Valider

Lancer depuis le dossier du microservice :

```bash
uv run pytest
uv run ruff check .
uv run ruff check --select ANN app
uv run ruff format --check .
```

Depuis la racine, lancer également `git diff --check -- <microservice>`.

Ne pas lancer une stack Docker complète si les tests unitaires suffisent. Signaler les intégrations ignorées et les dépendances externes indisponibles.

## Critères de sortie

Considérer le travail terminé uniquement si :

- toutes les exceptions applicatives du microservice sont centralisées ;
- toutes les erreurs attendues des frontières externes sont traduites ;
- une erreur inattendue produit un contrat public neutre ;
- les logs sont JSON, redacted, bornés et sans doublon ;
- les niveaux de logs correspondent à la gravité ;
- les tests couvrent les handlers, contrats et redactions ;
- les contrats de succès et l'observabilité existante restent inchangés.

## Format de réponse

Répondre avec :

- le microservice traité ;
- les exceptions et handlers centralisés ;
- les changements de logging ;
- les fichiers modifiés ;
- les tests et contrôles exécutés ;
- les limites ou dépendances externes non testées.
