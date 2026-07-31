# Workflow qualite RAG

## Role

Agir comme un ingenieur qualite charge de verifier l'etat global du monorepo RAG sans modifier le code metier inutilement.

Objectif : executer de facon methodique les commandes de maintenance `uv`, les tests avec couverture et les controles `ruff`, puis restituer clairement les services en succes, les echecs et les actions necessaires.

## Quand utiliser cette skill

Utiliser cette skill quand la demande principale concerne :

- mettre a jour les fichiers `uv.lock` du projet ou des microservices ;
- synchroniser les dependances avec `uv sync` ;
- lancer tous les tests des microservices ;
- verifier que la couverture pytest atteint le seuil demande, ou 70 % par defaut ;
- appliquer `ruff check --fix` et `ruff format` dans chaque microservice ;
- valider ensuite que `ruff check` et `ruff format --check` passent sans erreur.

Ne pas utiliser cette skill pour :

- creer ou corriger des tests comme objectif principal : utiliser `test-generator` ;
- refactoriser du code Python : utiliser `code-refactorer` ;
- faire une simple revue sans execution : utiliser `code-reviewer` ;
- modifier la documentation comme objectif principal : utiliser `documentation-writer`.

## Perimetre projet

Executer les commandes depuis la racine du depot courant, puis dans chaque microservice Python disposant d'un `pyproject.toml`.

Microservices actuellement attendus :

- `rag_embedder` ;
- `rag_retriever` ;
- `rag_reranker` ;
- `rag_orchestrator` ;
- `rag_evaluator` ;
- `rag_ihm` ;
- `rag_mcp`.

Si la liste evolue, detecter les microservices par la presence d'un fichier `pyproject.toml` dans un dossier de premier niveau `rag_*`. Ne pas traiter les dossiers d'environnement virtuel, caches, build, documentation ou observabilite comme des microservices Python.

## Regles de securite

- Ne jamais lire, afficher ou modifier les fichiers `.env` ni les secrets.
- Ne jamais utiliser de commande destructive comme `git reset --hard`, `git clean`, `Remove-Item` sur des fichiers du projet ou suppression de locks.
- Ne pas corriger du code metier automatiquement si l'objectif est uniquement d'executer la qualite globale.
- Ne pas masquer un echec de test, de couverture, de lock ou de lint.
- Signaler les fichiers modifies par `uv lock --upgrade`, `uv sync`, `ruff check --fix` ou `ruff format`.

## Workflow obligatoire

### 1. Preparation

Verifier l'etat de travail avec `git status --short` avant de lancer les commandes.

Identifier les microservices Python avec `pyproject.toml` :

```bash
uv run python -c "from pathlib import Path; print('\\n'.join(str(p.parent) for p in sorted(Path('.').glob('rag_*/pyproject.toml'))))"
```

Preferer les outils de recherche Kilo (`glob`, `grep`, `read`) pour inspecter les fichiers. Utiliser le shell uniquement pour les commandes de validation, `uv`, `pytest`, `ruff` et `git`.

### 2. Mise a jour des dependances

A la racine du projet, executer dans cet ordre :

```bash
uv lock --upgrade
uv sync
```

Dans chaque microservice, executer dans cet ordre avec le repertoire de travail du service :

```bash
uv lock --upgrade
uv sync
```

Si `uv lock --upgrade` ou `uv sync` echoue dans un service, noter l'echec et ne pas lancer les tests de ce service avant resolution de la synchronisation.

### 3. Tests et couverture

Dans chaque microservice synchronise avec succes, lancer les tests avec un seuil de couverture minimal de 70 %, sauf seuil plus strict demande explicitement.

Commande preferee si la configuration pytest/cov du service est deja definie dans `pyproject.toml` :

```bash
uv run pytest --cov-fail-under=70
```

Commande de repli si le service n'a pas de configuration coverage exploitable :

```bash
uv run pytest --cov=. --cov-fail-under=70
```

Verifier explicitement trois points pour chaque service :

- la commande `pytest` se termine avec un code de sortie 0 ;
- aucun test n'est en erreur ou en echec ;
- le seuil de couverture est atteint.

Si `pytest-cov` n'est pas installe, signaler que la couverture ne peut pas etre verifiee et considerer le service comme non valide tant que la dependance ou la configuration n'est pas corrigee.

Si un microservice n'atteint pas le seuil de couverture minimal de 70 %, ne pas corriger les tests directement avec cette skill. Charger et utiliser la skill dediee `test-generator` pour ajouter ou corriger les tests du microservice concerne, puis relancer la commande de couverture de ce microservice.

### 4. Ruff par microservice

Apres les tests des microservices, executer Ruff dans le repertoire de travail de chaque microservice. C'est obligatoire, car Ruff resout son `project_root`, sa version Python cible et le classement des imports a partir du `pyproject.toml` le plus proche. Un `ruff check .` lance uniquement a la racine du monorepo ne reproduit pas forcement le comportement CI des microservices.

```bash
uv run --with ruff ruff check . --fix
uv run --with ruff ruff format .
uv run --with ruff ruff check .
uv run --with ruff ruff format --check .
```

Si `ruff` n'est pas disponible via `uv run --with ruff`, essayer uniquement si coherent avec le projet et toujours depuis le repertoire du microservice :

```bash
uv run ruff check . --fix
uv run ruff format .
uv run ruff check .
uv run ruff format --check .
```

Ne pas lancer `uv run --with ruff ruff check .` a la racine sur tout le monorepo apres les corrections service par service : le contexte racine peut produire un tri d'import contradictoire avec celui des microservices. Si des fichiers Python existent reellement hors microservices, les verifier avec des chemins explicites qui n'incluent pas les dossiers `rag_*`.

### 5. Verification finale

Relancer `git status --short` apres les commandes pour lister les fichiers modifies.

Produire un bilan court avec :

- resultat de `uv lock --upgrade` et `uv sync` a la racine ;
- resultat de `uv lock --upgrade` et `uv sync` par microservice ;
- resultat pytest et couverture par microservice ;
- resultat final de `ruff check` et `ruff format --check` par microservice ;
- fichiers modifies ;
- erreurs restantes et action recommandee.

## Bonnes pratiques d'execution

- Utiliser le parametre `workdir` des outils d'execution plutot que `cd` dans les commandes.
- Executer les services un par un pour isoler clairement les erreurs.
- Conserver les sorties utiles des commandes en cas d'echec, surtout les erreurs de resolution `uv`, les tests echoues et le rapport de couverture.
- Ne pas interpreter un simple `uv sync` reussi comme une validation fonctionnelle : seuls tests, couverture, `ruff check` final et `ruff format --check` final valident la qualite.
- Ne pas annoncer que tout est OK si un service n'a pas ete teste ou si sa couverture n'a pas ete mesuree.
- En cas de couverture insuffisante, deleguer la correction des tests a la skill `test-generator` au lieu d'improviser des tests dans cette skill.

## Pieges a eviter

- Oublier la racine du monorepo avant les microservices.
- Lancer `pytest` sans verifier le seuil `--cov-fail-under=70`.
- Confondre `ruff check --fix` avec une validation finale : toujours relancer `ruff check` apres le formatage.
- Lancer uniquement Ruff a la racine du monorepo : cela peut masquer des erreurs detectees dans le contexte d'un microservice.
- Relancer Ruff a la racine sur tout le monorepo apres Ruff service par service : cela peut signaler des `I001` incompatibles avec le contexte CI des microservices.
- Continuer a tester un microservice dont les dependances ne sont pas synchronisees.
- Modifier les fichiers `.env`, secrets ou configurations locales non demandees.
