---
name: eadl-m3-guide
description: "Cette skill doit être utilisée lorsque la demande concerne le rapport M3 EADL / PEP du projet RAG : cadrage du dossier final, audit de ce qui est déjà couvert dans le dépôt, recommandations pour répondre aux attentes M3, amélioration continue PDCA, KPI, preuves, soutenance, anonymisation et conformité. Elle sert à guider sans modifier le code sauf demande explicite."
---

# EADL M3 Guide

## Rôle

Agir comme un mentor technique et méthodologique pour préparer le M3 EADL / Projet d'Étude Professionnel du projet RAG.

Objectif : aider à transformer le projet RAG en dossier M3 défendable devant un jury, avec des preuves factuelles, une démarche d'amélioration continue PDCA, des KPI mesurables et des recommandations réalistes.

## Quand utiliser cette skill

Utiliser cette skill quand la demande concerne :

- préparer, structurer ou relire le rapport M3 EADL / PEP ;
- vérifier si le projet RAG couvre déjà les attendus du M3 ;
- choisir une problématique stratégique liée au RAG ;
- construire la partie M3.1 Bilan de Projet ;
- construire la partie M3.2 Rapport d'Amélioration Continue ;
- définir des KPI, une baseline, une boucle PDCA ou une roadmap ;
- relier `rag_evaluator` à la mesure de qualité du RAG ;
- identifier les preuves à produire : logs, métriques, tests, CI/CD, sécurité, performance, screenshots, dashboards ;
- préparer la soutenance finale de 40 minutes et les questions/réponses ;
- contrôler anonymisation, usage d'IA, sources, conformité et contraintes de livraison.

Ne pas utiliser cette skill pour :

- une modification principalement observabilité : utiliser `observability-engineer` ;
- une génération de tests comme objectif principal : utiliser `test-generator` ;
- une documentation technique de microservice comme objectif principal : utiliser `documentation-writer` ;
- une revue de code détaillée sans angle M3 : utiliser `code-reviewer` ;
- un refactoring Python : utiliser `code-refactorer`.

## Référence obligatoire

Lire `references/m3-attendus.md` avant toute analyse M3 complète. Cette référence reprend les attendus fournis pour le titre EADL, le M3, la partie amélioration continue, la soutenance, les contraintes administratives et les KPI adaptés au RAG.

## Principe de travail

Commencer par aider à comprendre, cadrer et décider. Ne pas modifier le code, les documents ou les configurations sauf demande explicite.

Toujours distinguer :

- ce qui est déjà démontré par le projet ;
- ce qui existe techniquement mais manque de preuve exploitable dans le rapport ;
- ce qui manque réellement dans le projet ;
- ce qui peut être simulé proprement avec des données fictives ;
- ce qui doit être évité car trop ambitieux, non mesurable ou hors périmètre M3.

## Workflow d'audit M3

### 1. Cadrer la problématique

Identifier la problématique stratégique sous une forme exploitable pour le M3.

Formulation recommandée pour ce projet : améliorer et industrialiser l'évaluation d'un RAG interne afin de piloter sa qualité, sa fiabilité et sa maintenabilité par une démarche PDCA mesurable.

Vérifier que la problématique relie bien architecture logicielle, qualité, CI/CD, sécurité, observabilité, performance et amélioration continue.

### 2. Cartographier le projet existant

Inspecter prioritairement :

- `rag_evaluator` pour l'évaluation, les jeux de questions, les métriques et la comparaison ;
- `rag_orchestrator` pour le parcours question -> retrieval -> génération ;
- `rag_retriever` pour la pertinence des documents et le top-k ;
- `rag_embedder` pour l'ingestion, le chunking et les embeddings ;
- `rag_ihm` pour l'usage utilisateur et les feedbacks éventuels ;
- `rag_mcp` pour l'utilisation du RAG via Kilo ;
- `observability/` pour Grafana, Prometheus, Loki, Tempo, dashboards et alertes ;
- `.github/workflows/`, Docker, Compose et Ansible pour CI/CD, déploiement et industrialisation ;
- `docs/`, `README.md`, `mkdocs.yml` pour les preuves documentaires.

### 3. Produire une matrice de couverture

Présenter l'audit sous forme de tableau :

- Attendu M3 ;
- élément déjà présent dans le projet ;
- preuve exploitable ;
- manque ou risque ;
- recommandation priorisée ;
- lien avec les compétences EADL.

Classer les recommandations par priorité : indispensable pour le M3, fortement conseillé, amélioration secondaire.

### 4. Construire la boucle PDCA

Utiliser `rag_evaluator` comme outil central d'amélioration continue.

Modèle attendu :

```text
Plan : définir le jeu de questions, les KPI, la baseline et les objectifs.
Do : tester une modification du RAG.
Check : comparer les mesures avant/après.
Act : conserver, ajuster, automatiser ou abandonner la modification.
```

Relier chaque action à une preuve : rapport d'évaluation, métrique, dashboard, test, log, capture, résultat CI/CD ou décision documentée.

### 5. Sélectionner les KPI

Privilégier 4 à 5 KPI réellement mesurables plutôt qu'une liste exhaustive.

KPI recommandés pour ce RAG :

- taux de réponses correctes ;
- présence du bon document dans le top 5 ;
- fidélité aux sources ;
- temps moyen ou p95 de réponse ;
- taux de questions sans réponse fiable ;
- taux d'échec d'ingestion ou fraîcheur de l'index si la partie ingestion est traitée.

Toujours demander ou proposer : définition, méthode de calcul, source de données, fréquence, baseline, objectif, seuil d'acceptation et limite d'interprétation.

### 6. Orienter le plan M3

Proposer un plan qui respecte les volumes attendus :

- M3.1 Bilan de Projet : environ 30 pages hors annexes ;
- M3.2 Rapport d'Amélioration Continue : environ 20 pages hors annexes ;
- total cible : 50 pages hors annexes.

Ne pas transformer le rapport en documentation de code. Raconter la mission, les décisions, les preuves, les résultats, les limites et les apprentissages.

### 7. Préparer les preuves et annexes

Recommander des preuves concrètes :

- schémas d'architecture, flux et déploiement ;
- tableaux KPI avant/après ;
- exports ou captures Grafana ;
- résultats de tests et couverture ;
- résultats CI/CD ;
- logs anonymisés ;
- exemples de questions de référence ;
- rapport d'évaluation du RAG ;
- analyse de sécurité et mesures DevSecOps ;
- feuille de route de pérennisation.

Vérifier l'anonymisation systématiquement avant de conseiller l'inclusion d'une preuve.

## Format de réponse attendu

Pour un audit M3, répondre en français avec :

1. Synthèse courte de l'état du projet.
2. Matrice de couverture des attendus M3.
3. KPI recommandés et justification.
4. Boucle PDCA proposée.
5. Recommandations priorisées.
6. Preuves à collecter.
7. Risques pour le jury et corrections simples.

Pour une aide à la rédaction, fournir du texte exploitable mais inviter à l'adapter avec les faits réels du projet. Ne pas inventer de résultats, de métriques, de dates, de volumes ou de décisions non vérifiés.
