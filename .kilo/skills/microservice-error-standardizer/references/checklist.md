# Checklist exceptions et logs d'un microservice

Utiliser cette checklist pendant l'audit et avant de déclarer la tâche terminée.

## Exceptions

- [ ] Une seule hiérarchie applicative existe dans `app/core/exceptions.py` ou `app/core/errors.py`.
- [ ] Chaque exception expose un code ou slug stable.
- [ ] Les messages publics ne contiennent aucun diagnostic technique dynamique.
- [ ] Les détails publics sont explicitement autorisés.
- [ ] Le contexte interne n'est accessible qu'aux logs serveur.
- [ ] Les erreurs DAL connues sont traduites avec `raise ... from exception`.
- [ ] Aucun `KeyError`, `ValidationError`, timeout ou erreur fournisseur attendu ne sort brut.
- [ ] Aucun `except Exception` ne masque un bug dans le DAL ou le métier.

## Frontière applicative

### FastAPI

- [ ] Un handler central traite l'exception applicative racine.
- [ ] Un handler central traite les exceptions inattendues.
- [ ] Le contrat d'erreur est toujours `{slug, message, details}`.
- [ ] Les 401 ajoutent `WWW-Authenticate: Bearer` si nécessaire.
- [ ] Les validations FastAPI 422 restent stables.

### MCP

- [ ] Les erreurs d'outil utilisent un résultat MCP en erreur, jamais un texte de succès.
- [ ] Les erreurs distinguent authentification, autorisation, quota, timeout, réseau et fournisseur.
- [ ] Le payload d'erreur possède un code stable et un indicateur `retryable` si utile.

### Streamlit

- [ ] Un composant commun affiche et journalise les erreurs.
- [ ] Un HTTP 401 invalide la session locale.
- [ ] Les réponses réseau sont validées avant leur utilisation par les pages.
- [ ] `st.stop()` et `st.rerun()` ne sont pas absorbés par un handler global.

## Logging

- [ ] `configure_json_logging()` est idempotente.
- [ ] Les logs sont écrits sur stdout en JSON.
- [ ] Les loggers applicatifs utilisent `logging.getLogger(__name__)`.
- [ ] Uvicorn utilise le même formatter pour un service FastAPI.
- [ ] Les access logs ne recopient pas une query string sensible.
- [ ] Les champs `extra` sont sérialisés et bornés.
- [ ] Les clés sensibles sont redacted récursivement.
- [ ] Le message dynamique d'une exception n'est pas sérialisé.
- [ ] Une pile est limitée au type et aux emplacements utiles.
- [ ] Une erreur n'est journalisée qu'une seule fois.
- [ ] Les erreurs 4xx attendues utilisent `WARNING`.
- [ ] Les dépendances indisponibles connues utilisent `ERROR`.
- [ ] Les erreurs inattendues utilisent `logger.exception()`.
- [ ] Aucun `print()` n'est présent dans le code applicatif.

## Données interdites

- [ ] Bearer token, clé API, secret, mot de passe et cookie.
- [ ] Code ou state OAuth.
- [ ] Question utilisateur et prompt généré.
- [ ] Document, chunk et embedding complets.
- [ ] Corps HTTP externe et headers.
- [ ] URL complète avec query string ou credentials.
- [ ] Commentaire ou feedback utilisateur.

## Tests

- [ ] Handler d'exception applicative.
- [ ] Handler d'exception inattendue.
- [ ] Statuts et slugs publics.
- [ ] Timeout, connexion et statuts HTTP externes.
- [ ] JSON et contrat externes invalides.
- [ ] Redaction imbriquée et troncature.
- [ ] Idempotence de la configuration logging.
- [ ] Absence de donnée sensible dans payloads et logs.
- [ ] Contrat de succès inchangé.

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
```
