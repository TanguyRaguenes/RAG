---
name: project-quality-runner
description: "Cette skill doit être utilisée lorsque la demande concerne la maintenance qualité globale du RAG : mettre à jour les locks uv, synchroniser les dépendances, lancer les tests pytest de chaque microservice avec une couverture minimale de 70 %, puis exécuter ruff check --fix, ruff format et ruff check dans le contexte de chaque microservice."
---

# Project Quality Runner

## Rôle

Agir comme un ingénieur qualité chargé de vérifier l'état global du monorepo RAG sans modifier le code métier inutilement.

Objectif : exécuter de façon méthodique les commandes de maintenance `uv`, les tests avec couverture et les contrôles `ruff`, puis restituer clairement les services en succès, les échecs et les actions nécessaires.

## Quand utiliser cette skill

Utiliser cette skill quand la demande principale concerne :

- mettre à jour les fichiers `uv.lock` du projet ou des microservices ;
- synchroniser les dépendances avec `uv sync` ;
- lancer tous les tests des microservices ;
- vérifier que la couverture pytest atteint au moins 70 % ;
- appliquer `ruff check --fix` et `ruff format` dans chaque microservice ;
- valider ensuite que `ruff check` passe sans erreur.

Ne pas utiliser cette skill pour :

- créer ou corriger des tests comme objectif principal : utiliser `test-generator` ;
- refactoriser du code Python : utiliser `code-refactorer` ;
- faire une simple revue sans exécution : utiliser `code-reviewer` ;
- modifier la documentation comme objectif principal : utiliser `documentation-writer`.

## Périmètre projet

Exécuter les commandes depuis la racine du dépôt courant, puis dans chaque microservice Python disposant d'un `pyproject.toml`.

Microservices actuellement attendus :

- `rag_embedder` ;
- `rag_retriever` ;
- `rag_reranker` ;
- `rag_orchestrator` ;
- `rag_evaluator` ;
- `rag_ihm` ;
- `rag_mcp`.

Si la liste évolue, détecter les microservices par la présence d'un fichier `pyproject.toml` dans un dossier de premier niveau `rag_*`. Ne pas traiter les dossiers d'environnement virtuel, caches, build, documentation ou observabilité comme des microservices Python.

## Règles de sécurité

- Ne jamais lire, afficher ou modifier les fichiers `.env` ni les secrets.
- Ne jamais utiliser de commande destructive comme `git reset --hard`, `git clean`, `Remove-Item` sur des fichiers du projet ou suppression de locks.
- Ne pas corriger du code métier automatiquement si l'objectif est uniquement d'exécuter la qualité globale.
- Ne pas masquer un échec de test, de couverture, de lock ou de lint.
- Signaler les fichiers modifiés par `uv lock --upgrade`, `uv sync`, `ruff check --fix` ou `ruff format`.

## Workflow obligatoire

### 1. Préparation

Vérifier l'état de travail avec `git status --short` avant de lancer les commandes.

Identifier les microservices Python avec `pyproject.toml` :

```bash
uv run python -c "from pathlib import Path; print('\\n'.join(str(p.parent) for p in sorted(Path('.').glob('rag_*/pyproject.toml'))))"
```

Préférer les outils de recherche Kilo (`glob`, `grep`, `read`) pour inspecter les fichiers. Utiliser le shell uniquement pour les commandes de validation, `uv`, `pytest`, `ruff` et `git`.

### 2. Mise à jour des dépendances

À la racine du projet, exécuter dans cet ordre :

```bash
uv lock --upgrade
uv sync
```

Dans chaque microservice, exécuter dans cet ordre avec le répertoire de travail du service :

```bash
uv lock --upgrade
uv sync
```

Si `uv lock --upgrade` ou `uv sync` échoue dans un service, noter l'échec et ne pas lancer les tests de ce service avant résolution de la synchronisation.

### 3. Tests et couverture

Dans chaque microservice synchronisé avec succès, lancer les tests avec un seuil de couverture minimal de 70 %.

Commande préférée si la configuration pytest/cov du service est déjà définie dans `pyproject.toml` :

```bash
uv run pytest --cov-fail-under=70
```

Commande de repli si le service n'a pas de configuration coverage exploitable :

```bash
uv run pytest --cov=. --cov-fail-under=70
```

Vérifier explicitement trois points pour chaque service :

- la commande `pytest` se termine avec un code de sortie 0 ;
- aucun test n'est en erreur ou en échec ;
- le seuil de couverture de 70 % est atteint.

Si `pytest-cov` n'est pas installé, signaler que la couverture ne peut pas être vérifiée et considérer le service comme non validé tant que la dépendance ou la configuration n'est pas corrigée.

Si un microservice n'atteint pas le seuil de couverture minimal de 70 %, ne pas corriger les tests directement avec cette skill. Charger et utiliser la skill dédiée `test-generator` pour ajouter ou corriger les tests du microservice concerné, puis relancer la commande de couverture de ce microservice.

### 4. Ruff par microservice

Après les tests des microservices, exécuter Ruff dans le répertoire de travail de chaque microservice. C'est obligatoire, car Ruff résout son `project_root`, sa version Python cible et le classement des imports à partir du `pyproject.toml` le plus proche. Un `ruff check .` lancé uniquement à la racine du monorepo ne reproduit pas forcément le comportement CI des microservices.

```bash
uv run --with ruff ruff check . --fix
uv run --with ruff ruff format .
uv run --with ruff ruff check .
uv run --with ruff ruff format --check .
```

Si `ruff` n'est pas disponible via `uv run --with ruff`, essayer uniquement si cohérent avec le projet et toujours depuis le répertoire du microservice :

```bash
uv run ruff check . --fix
uv run ruff format .
uv run ruff check .
uv run ruff format --check .
```

Ne pas lancer `uv run --with ruff ruff check .` à la racine sur tout le monorepo après les corrections service par service : le contexte racine peut produire un tri d'import contradictoire avec celui des microservices. Si des fichiers Python existent réellement hors microservices, les vérifier avec des chemins explicites qui n'incluent pas les dossiers `rag_*`.

### 5. Vérification finale

Relancer `git status --short` après les commandes pour lister les fichiers modifiés.

Produire un bilan court avec :

- résultat de `uv lock --upgrade` et `uv sync` à la racine ;
- résultat de `uv lock --upgrade` et `uv sync` par microservice ;
- résultat pytest et couverture par microservice ;
- résultat final de `ruff check` et `ruff format --check` par microservice ;
- fichiers modifiés ;
- erreurs restantes et action recommandée.

## Bonnes pratiques d'exécution

- Utiliser le paramètre `workdir` des outils d'exécution plutôt que `cd` dans les commandes.
- Exécuter les services un par un pour isoler clairement les erreurs.
- Conserver les sorties utiles des commandes en cas d'échec, surtout les erreurs de résolution `uv`, les tests échoués et le rapport de couverture.
- Ne pas interpréter un simple `uv sync` réussi comme une validation fonctionnelle : seuls tests, couverture, `ruff check` final et `ruff format --check` final valident la qualité.
- Ne pas annoncer que tout est OK si un service n'a pas été testé ou si sa couverture n'a pas été mesurée.
- En cas de couverture insuffisante, déléguer la correction des tests à la skill `test-generator` au lieu d'improviser des tests dans cette skill.

## Pièges à éviter

- Oublier la racine du monorepo avant les microservices.
- Lancer `pytest` sans vérifier le seuil `--cov-fail-under=70`.
- Confondre `ruff check --fix` avec une validation finale : toujours relancer `ruff check` après le formatage.
- Lancer uniquement Ruff à la racine du monorepo : cela peut masquer des erreurs détectées dans le contexte d'un microservice.
- Relancer Ruff à la racine sur tout le monorepo après Ruff service par service : cela peut signaler des `I001` incompatibles avec le contexte CI des microservices.
- Continuer à tester un microservice dont les dépendances ne sont pas synchronisées.
- Modifier les fichiers `.env`, secrets ou configurations locales non demandées.
