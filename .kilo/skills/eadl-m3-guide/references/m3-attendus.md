# Attendus M3 EADL pour le projet RAG

## Finalité du M3

Le M3 est le Projet d'Étude Professionnel final du titre EADL. Il doit démontrer une expertise d'architecte développeur sur une problématique stratégique réelle ou réaliste en entreprise.

Le dossier doit montrer une démarche complète : analyse du contexte, diagnostic, conception, réalisation, preuves, mesure d'impact, amélioration continue et pérennisation.

Pour ce projet RAG, l'angle recommandé est : concevoir, industrialiser et piloter un RAG interne pour développeurs, avec un microservice d'évaluation permettant de mesurer la qualité et d'alimenter une boucle PDCA.

## Livrable final attendu

Le dossier M3 est un document unique d'environ 50 pages hors annexes, composé de deux parties.

| Partie | Volume cible | Objectif |
|---|---:|---|
| M3.1 Bilan de Projet | environ 30 pages | Présenter l'entreprise, le contexte, la mission significative, l'architecture, la réalisation, les résultats et le bilan critique |
| M3.2 Rapport d'Amélioration Continue | environ 20 pages | Présenter la baseline, les KPI, la démarche PDCA, les améliorations, les mesures avant/après et la pérennisation |

La soutenance dure 40 minutes, suivies de 15 minutes de questions/réponses.

Répartition orale recommandée :

| Séquence | Durée | Contenu |
|---|---:|---|
| M1 synthétisé | 5 min | Entreprise, équipe, contexte SI, rôle |
| M2 / bilan projet | 15 min | Mission, architecture, réalisation, résultats |
| M3.2 amélioration continue | 20 min | Diagnostic, KPI, PDCA, impacts, pérennisation |
| Questions/réponses | 15 min | Justification des choix, limites, recul critique |

## Domaines évalués

| Domaine | Attendus principaux |
|---|---|
| Expertise d'architecture logicielle | Définir, concevoir et justifier une architecture cohérente, maintenable, sécurisée et performante |
| Mise en oeuvre et gestion de projet | Réaliser une solution avec des pratiques professionnelles de pilotage, qualité, tests, CI/CD et documentation |
| Amélioration continue et innovation | Mesurer les écarts, proposer des actions correctives, montrer une démarche PDCA et des leviers d'innovation |
| Communication et professionnalisme | Produire un rapport structuré, sourcé, anonymisé, clair et défendable à l'oral |

## Alignement avec les blocs EADL

| Bloc | Compétences visées | Comment les montrer dans le projet RAG |
|---|---|---|
| Bloc 1 | C01 à C09 | Veille, analyse des besoins, faisabilité, architecture, choix technologiques, revues de conception, modèles de données et flux, tests, spécifications |
| Bloc 2 | C10 à C15 | Planification, conduite de projet, indicateurs, résolution de problèmes, évaluation de l'avancement, montée en compétences et communication |
| Bloc 3 | C16 à C20 | CI/CD, automatisation, DevSecOps, clean code, documentation technique |
| Bloc 4 | C21 à C26 | Déploiement, infrastructure, services cloud ou conteneurisation, sécurité, optimisation, éventuellement FinOps |
| Bloc 5 | C27 à C35 | Données, ETL, automatisation, IA, monitoring, maintenabilité, amélioration continue |

## Plan recommandé pour M3.1

### 1. Introduction et contexte général

Inclure : présentation synthétique de l'entreprise ou de l'entité d'accueil, équipe, produit ou projet concerné, contexte stratégique, enjeux du RAG, rôle et responsabilités exercées.

Éviter : présentation exhaustive de toute l'entreprise, descriptions théoriques de technologies connues, détails confidentiels.

### 2. Objectifs de la mission

Inclure : problématique concrète, objectifs mesurables, critères de succès, contraintes techniques, temporelles, sécurité, qualité, réglementaires ou budgétaires, acteurs impliqués, livrables.

Exemple de problématique adaptée : le RAG initial répond aux questions mais la qualité est difficile à objectiver, les sources remontées ne sont pas toujours pertinentes et l'équipe ne dispose pas d'un mécanisme fiable pour comparer les évolutions.

### 3. Analyse et conception de la solution

Inclure : besoins utilisateurs et parties prenantes, étude de faisabilité, alternatives, architecture applicative, architecture de données, flux, déploiement, sécurité by design, observabilité, choix technologiques argumentés.

Pour le RAG, analyser notamment : ingestion des wikis, embeddings, retrieval, orchestration, génération, interface Streamlit, serveur MCP, évaluation, observabilité et déploiement Docker/Ansible.

### 4. Réalisation et mise en oeuvre

Inclure : déroulement de la mission, jalons, composants développés, pratiques TDD/tests, CI/CD, DevSecOps, documentation, preuves techniques, logs, métriques, captures ou résultats mesurés.

Ne pas présenter le code comme un mode d'emploi. Expliquer les responsabilités des composants et les décisions prises.

### 5. Résultats et bilan critique

Inclure : résultats obtenus versus objectifs, impact qualité, sécurité, performance, maintenabilité, difficultés rencontrées, limites, compromis, pistes d'amélioration.

Le bilan doit montrer de la prise de recul : ce qui marche, ce qui reste fragile, ce qui est simulé, ce qui serait fait différemment.

## Plan recommandé pour M3.2

### 1. Diagnostic et mesure initiale

Présenter la situation de référence : qualité initiale du RAG, dette technique, incidents, temps de réponse, pertinence documentaire, couverture de tests, erreurs, limites d'observabilité.

Définir une baseline avec des valeurs mesurées ou simulées de manière explicite. Ne jamais inventer des métriques sans l'indiquer.

### 2. Démarche d'amélioration

Utiliser PDCA : Plan, Do, Check, Act.

Plan : choisir le problème, le jeu de questions, les KPI, les objectifs et les hypothèses.

Do : mettre en place une action d'amélioration, par exemple reranking, modification du chunking, enrichissement des métadonnées, filtrage par espace documentaire, amélioration du prompt ou refus de réponse si les sources sont insuffisantes.

Check : mesurer à nouveau avec `rag_evaluator`, comparer avant/après, analyser les compromis.

Act : conserver, ajuster, abandonner ou automatiser l'amélioration.

### 3. Mesures et résultats

Comparer avant/après avec des KPI lisibles. Expliquer les compromis, par exemple une amélioration de la pertinence qui augmente légèrement le temps de réponse.

Exemple de formulation : le reranking améliore la pertinence des documents retrouvés mais ajoute environ 900 ms ; ce coût est accepté si le temps total reste inférieur à l'objectif fixé.

### 4. Plan de pérennisation

Présenter les mécanismes qui rendent l'amélioration durable : jeu de questions de référence, exécution régulière des évaluations, seuils de qualité, blocage d'une mise en production si la qualité baisse, surveillance du temps de réponse, enrichissement des questions mal traitées, réindexation des wikis modifiés, dashboard, revue mensuelle des erreurs.

### 5. Conclusion personnelle

Expliquer les apports pour l'entreprise, les apports pour le candidat, le rôle de l'expert en architecture logicielle et la transformation d'un prototype RAG en système pilotable.

## KPI adaptés au RAG

Il vaut mieux sélectionner quatre ou cinq KPI réellement mesurables plutôt que tout mesurer superficiellement.

| KPI | Ce qu'il mesure | Source possible | Usage PDCA |
|---|---|---|---|
| Pertinence des documents retrouvés | Les bons passages remontent-ils ? | `rag_evaluator`, résultats du retriever, top-k | Identifier les problèmes de retrieval |
| Bon document dans le top 5 | Le document attendu est-il dans les 5 premiers résultats ? | jeu de questions avec documents attendus | Mesurer retrieval avant/après |
| Taux de réponses correctes | La réponse répond-elle correctement à la question ? | évaluation humaine ou grille de référence | Mesurer la qualité finale |
| Fidélité aux sources | La réponse repose-t-elle réellement sur les documents ? | comparaison réponse/sources, revue humaine | Réduire hallucinations et réponses non appuyées |
| Taux de questions sans réponse fiable | Le RAG refuse-t-il quand les sources sont insuffisantes ? | cas de test sans source pertinente | Vérifier le comportement de prudence |
| Temps de réponse | Combien de secondes prend une recherche complète ? | métriques applicatives, logs, Prometheus | Suivre le compromis qualité/performance |
| Fraîcheur de l'index | Délai entre modification wiki et disponibilité dans le RAG | logs d'ingestion, dates de documents | Piloter la réindexation |
| Échecs d'ingestion | Documents non indexés correctement | logs, alertes, métriques ingestion | Fiabiliser la base documentaire |
| Satisfaction utilisateur | Réponse jugée utile par les utilisateurs | feedback UI, enquête interne | Valider la valeur métier |

Pour chaque KPI, documenter : définition, formule, outil de mesure, fréquence, baseline, objectif cible, seuil d'alerte et limites.

## Exemple concret de boucle PDCA pour le RAG

Plan : créer un jeu de 50 questions représentatives à partir des wikis, mesurer la baseline, constater que le bon document est souvent proche du sujet mais pas assez précis.

Do : tester plusieurs actions, par exemple ajout d'un reranker, modification de la taille des chunks, ajout du titre du wiki dans les métadonnées, filtrage par espace documentaire, amélioration du prompt, refus de répondre lorsque les sources sont insuffisantes.

Check : mesurer à nouveau les réponses correctes, le bon document dans le top 5, le temps moyen et le taux de réponses non appuyées par les sources.

Act : conserver les changements qui améliorent la qualité sans dépasser le seuil de latence, documenter les décisions, automatiser l'évaluation, enrichir le jeu de questions et intégrer les seuils au processus de livraison.

## Matrice d'audit à produire

| Attendu M3 | À vérifier dans le projet | Preuve attendue | Risque si absent | Recommandation |
|---|---|---|---|---|
| Problématique stratégique | README, docs, architecture, contexte du RAG | formulation claire et mesurable | rapport trop descriptif | cadrer le problème autour de la qualité pilotable du RAG |
| Architecture logicielle | services RAG, schémas, Docker Compose, flux | diagramme, justification des composants | manque de niveau architecte | produire architecture applicative, données et déploiement |
| Qualité et tests | dossiers tests, coverage, CI | résultats pytest, couverture | preuves insuffisantes | lier tests à la fiabilité des services critiques |
| CI/CD | workflows, lint, build, déploiement | pipeline fonctionnel | industrialisation faible | montrer automatisation et critères de non-régression |
| DevSecOps | auth, secrets, scans, config | mesures de sécurité | sécurité peu démontrée | expliquer les protections et limites |
| Observabilité | Prometheus, Grafana, Loki, Tempo | métriques, logs, dashboards | impact difficile à suivre | relier observabilité aux KPI du RAG |
| Amélioration continue | `rag_evaluator`, rapports, scripts | baseline, avant/après, PDCA | M3.2 fragile | faire de l'évaluateur le coeur du PDCA |
| Pérennisation | docs, seuils, roadmap, rituels | Definition of Done, roadmap | amélioration ponctuelle | intégrer évaluations régulières et revue des erreurs |

## Preuves à privilégier

Inclure en annexe ou dans le corps du rapport : schémas Mermaid ou UML, captures Grafana, extraits anonymisés de logs, résultats CI/CD, résultats de tests, tableaux KPI, exemples de questions d'évaluation, rapport généré par `rag_evaluator`, captures de l'IHM, configuration Docker/Ansible anonymisée, documentation technique, roadmap.

Chaque preuve doit être expliquée : ce qu'elle montre, pourquoi elle est fiable, quelle décision elle justifie.

## Contraintes administratives et conformité

Respecter le PDF sélectionnable, la nomenclature de fichiers, le volume de pages, les délais et l'attestation entreprise.

Prévoir les noms : `EADLyy_M3_Rapport_NOM_Prénom.pdf`, `EADLyy_M3_Support_NOM_Prénom.pdf`, `EADLyy_M3_Attestation_NOM_Prénom.pdf`.

Anonymiser noms de clients, contacts, emails, dépôts privés, URLs, IP, tickets, secrets, clés et identifiants. Utiliser des alias cohérents comme `Client A` ou `depot-repo-123`.

Déclarer l'usage d'IA : outil, tâche réalisée, valeur ajoutée, limites, vérifications humaines effectuées.

Citer les sources et licences des dépendances ou ressources externes. Éviter tout plagiat et reformuler avec une analyse personnelle.

## Pièges à éviter

Ne pas rédiger un mode d'emploi du projet. Ne pas lister du code sans analyse. Ne pas multiplier les KPI non mesurés. Ne pas inventer des résultats. Ne pas faire une partie PDCA purement théorique. Ne pas oublier les compromis, limites et risques. Ne pas exposer de données sensibles. Ne pas présenter Git, Docker ou FastAPI de manière scolaire ; expliquer leur usage réel dans le projet.
