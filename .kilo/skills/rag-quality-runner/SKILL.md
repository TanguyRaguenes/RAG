---
name: rag-quality-runner
description: "Cette skill doit etre utilisee lorsque la demande concerne la verification qualite globale du RAG : detecter les microservices Python, synchroniser les dependances uv, lancer les tests avec couverture minimale, executer Ruff par microservice et produire un bilan exploitable sans modifier le code metier inutilement."
---

# Rag Quality Runner

## Role

Piloter une passe qualite globale du monorepo RAG en appliquant une sequence reproductible : etat Git, detection des microservices, synchronisation `uv`, tests avec couverture, Ruff par microservice, puis bilan final.

Utiliser cette skill pour executer ou diagnostiquer la qualite globale du projet, pas pour refactoriser, documenter ou creer des tests comme objectif principal.

## Workflow

Lire `references/quality-workflow.md` avant de lancer les commandes. Ce fichier contient le perimetre, les regles de securite, les commandes obligatoires, les variantes acceptables et les pieges a eviter.

Sequence minimale a respecter :

- verifier `git status --short` ;
- detecter les dossiers `rag_*/pyproject.toml` ;
- executer `uv lock --upgrade` et `uv sync` a la racine puis par microservice ;
- lancer les tests avec couverture minimale ;
- executer `ruff check --fix`, `ruff format`, `ruff check` et `ruff format --check` dans chaque microservice ;
- terminer par un bilan listant succes, echecs, couverture, lint et fichiers modifies.

## Boundaries

- Ne pas lire, afficher ou modifier les fichiers `.env` ni les secrets.
- Ne pas utiliser de commande destructive.
- Ne pas assimiler un Ruff lance a la racine aux checks Ruff CI des microservices.
- Si un microservice n'atteint pas la couverture minimale, charger `test-generator` pour la correction des tests avant de relancer la couverture.
- Signaler clairement tout service non valide, non teste ou non synchronise.

## Resources

- `references/quality-workflow.md` : workflow detaille derive de `project-quality-runner`.
