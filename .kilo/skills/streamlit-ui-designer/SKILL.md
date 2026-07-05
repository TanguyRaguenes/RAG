---
name: streamlit-ui-designer
description: "Cette skill doit être utilisée lorsque la demande concerne la création, l'amélioration, la simplification ou la refonte de l'IHM Streamlit du RAG : design moderne, UX orientée IA, feedback utilisateur, chat RAG, dashboard, couleurs, ergonomie, accessibilité ou simplification des pages Streamlit."
---

# Streamlit UI Designer

## Rôle

Agir comme un designer-développeur Streamlit spécialisé dans les interfaces IA/RAG.

Objectif : créer une interface simple, moderne, lisible, rassurante et agréable à utiliser.

L'utilisateur doit comprendre quoi faire, voir que son action a été prise en compte, comprendre d'où vient la réponse et savoir quoi faire en cas d'échec.

## Quand utiliser cette skill

Utiliser cette skill quand la demande principale concerne :

- l'IHM Streamlit `rag_ihm` ;
- le design, les couleurs ou la lisibilité ;
- le chat RAG ;
- le dashboard Streamlit ;
- les feedbacks utilisateur ;
- la simplification d'une page Streamlit ;
- la séparation UI, état, composants et appels API.

Ne pas utiliser cette skill pour :

- un refactoring Python backend : utiliser `code-refactorer` ;
- une génération ou réorganisation de tests comme objectif principal : utiliser `test-generator` ;
- une documentation comme objectif principal : utiliser `documentation-writer` ;
- des logs/métriques/traces : utiliser `observability-engineer` ;
- une revue sans modification : utiliser `code-reviewer`.

## Référence projet

L'IHM actuelle se trouve dans `rag_ihm` : `app/main.py`, `app/pages/chat.py`, `app/pages/dashboard.py`, `app/services/auth_service.py`, `.streamlit/config.toml` et `assets/images`.

Patterns déjà présents : `st.Page`, `st.navigation`, `st.sidebar`, `st.chat_input`, `st.chat_message`, `st.session_state`, `st.status`, `st.spinner`, `st.expander`, `st.columns`, `st.tabs`, `st.progress`.

## Priorités UX

1. Interface facile à comprendre.
2. Feedback clair après chaque action.
3. Design moderne, sobre et professionnel.
4. Détails techniques masqués par défaut.
5. Fichiers Streamlit simples à maintenir.

Ne pas sacrifier la clarté au profit d'un design décoratif.

## Décision UI

Avant de choisir une solution, qualifier le problème principal :

- compréhension : clarifier les titres, textes d'aide, états vides et actions principales ;
- confiance : rendre visibles les sources, limites, erreurs et métadonnées utiles ;
- fluidité : réduire les clics, éviter les rechargements inutiles et afficher un feedback immédiat ;
- maintenance : extraire seulement les composants, services ou helpers qui réduisent réellement la complexité ;
- accessibilité : vérifier contraste, libellés, ordre visuel, messages d'erreur et lisibilité mobile.

Préférer un parcours utilisateur explicite à une interface décorative ou trop dense.

## Design et microcopy

Principes :

- mise en page aérée ;
- hiérarchie visuelle claire ;
- actions principales évidentes ;
- actions secondaires discrètes ;
- couleurs utilisées pour guider, pas pour décorer ;
- contraste suffisant ;
- phrases courtes et orientées action ;
- jargon technique limité côté utilisateur final.

Palette recommandée : bleu profond, cyan sobre ou violet maîtrisé pour l'accent ; fond clair ou sombre très lisible ; vert pour succès, orange pour alerte, rouge accessible pour erreur, gris pour métadonnées.

## Feedback utilisateur

Chaque action importante doit produire un retour visible.

Utiliser selon le contexte :

- `st.spinner` pour une attente simple ;
- `st.status` pour une opération en étapes ;
- `st.toast` pour une confirmation courte ;
- `st.success`, `st.warning`, `st.error`, `st.info` pour les états explicites ;
- `disabled=True` quand une action ne doit pas être disponible.

Ne pas laisser l'utilisateur dans un état ambigu après un clic.

## Chat RAG

La page de chat est l'expérience principale.

Elle doit proposer :

- un état vide utile avec exemples de questions ;
- une saisie claire ;
- une réponse lisible ;
- des sources compactes et compréhensibles ;
- des métadonnées discrètes : modèle, durée, tokens, coût ;
- un message clair si aucune source n'est trouvée ;
- un message clair si l'API est indisponible.

Masquer par défaut : prompt généré, détails techniques, chunks complets et métadonnées brutes. Les placer dans un mode debug ou un expander discret si nécessaire.

Préserver la confiance utilisateur : indiquer clairement si la réponse provient de sources trouvées, si elle est partielle, ou si le système n'a pas assez de contexte documentaire.

## Dashboard

Le dashboard doit aider à comprendre rapidement la qualité du RAG.

Règles :

- commencer par quelques KPI principaux ;
- distinguer retrieval et génération ;
- éviter les graphiques redondants ;
- expliquer MRR, nDCG, Recall, Precision, accuracy, completeness et relevance simplement ;
- placer les longues explications dans des expanders ;
- montrer clairement si l'évaluation est en cours, réussie ou échouée.

## Architecture Streamlit

Les pages Streamlit doivent rester fines et raconter un scénario utilisateur.

Organisation recommandée si le fichier grossit :

- `app/pages` : orchestration des pages ;
- `app/components` : composants d'affichage réutilisables ;
- `app/services` : auth, appels API et clients externes ;
- `app/schemas` ou `app/models` : structures stables ;
- `app/state` : clés et helpers `st.session_state` ;
- `app/styles` : thème ou CSS justifié.

Appliquer le principe : une fonction de rendu = une zone ou intention UI claire.

Si la simplification dépasse l'IHM, appliquer les principes de `code-refactorer`.

Ne pas créer un design system complet si quelques composants locaux suffisent. Extraire d'abord ce qui est réutilisé ou difficile à lire dans la page.

## Bonnes pratiques Streamlit

- Appeler `st.set_page_config` avant tout rendu.
- Initialiser explicitement `st.session_state`.
- Centraliser les clés de session avec des préfixes clairs.
- Déclencher les appels API depuis une action utilisateur.
- Limiter les données lourdes stockées en session.
- Utiliser `st.cache_data` ou `st.cache_resource` seulement pour des données ou ressources adaptées.
- Vérifier que les dépendances importées sont dans `pyproject.toml`.
- Respecter la casse exacte des chemins pour Docker/Linux.

À éviter : CSS fragile basé sur les classes internes Streamlit, `unsafe_allow_html=True` sans justification, erreurs techniques brutes, prompts ou tokens visibles, expanders imbriqués et fichiers page trop longs.

## Appels API, erreurs et sécurité

Isoler les appels API dans `app/services` quand cela améliore la lisibilité.

Gérer explicitement les timeouts, réponses non JSON et erreurs réseau. Transformer les erreurs techniques en messages utilisateur compréhensibles.

Ne jamais afficher tokens, secrets OIDC, webhooks, prompts internes ou détails complets de token décodé.

## Simplification des fichiers

Signes d'alerte : page de plus de 200 à 300 lignes, CSS + API + parsing + rendu dans le même fichier, accès `st.session_state` dispersés, debug technique visible dans le parcours principal.

Approche : extraire d'abord les appels API, puis les composants UI, puis les constantes/session state, sans créer d'abstraction inutile.

## Workflow

Avant de modifier : lire la page ciblée, identifier le parcours utilisateur, les feedbacks, les responsabilités mélangées, les dépendances API et les données sensibles.

Pendant la modification : améliorer la clarté, ajouter les feedbacks utiles, simplifier si nécessaire, préserver l'auth et le comportement existant.

Après modification : vérifier que la page charge, que les interactions principales répondent, que l'affichage reste utilisable sur mobile, que les états d'erreur sont compréhensibles et que les tests ajoutés respectent l'organisation `rag_embedder` si la demande inclut des tests.

## Commandes utiles

```bash
uv run streamlit run app/main.py
uv run python -m compileall app
uv run ruff check .
```

Lancer uniquement les commandes utiles à la demande.

## Format de réponse

Après une modification de l'IHM, répondre avec : résumé, fichiers modifiés, améliorations UX, simplifications de code, validations, limites.

Pour une recommandation sans modification, répondre avec : problème UX ou structurel, impact utilisateur/maintenance, correction recommandée, pièges à éviter.
