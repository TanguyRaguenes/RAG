
---

# Documentation d'installation : Extension Kilocode avec OpenRouter

Cette documentation décrit les étapes nécessaires pour installer l'extension **Kilocode** et la configurer pour utiliser **OpenRouter** comme fournisseur de modèles de langage (LLM).

## Prérequis

* Créer un compte sur [kilo](https://kilo.ai/)
* Demander une clé API valide auprès du gestionnaire du compte d'entreprise [OpenRouter](https://openrouter.ai/).
--> Important : Sauvegardez votre clé dans votre Keepass
* L'éditeur de code (comme VS Code) déjà installé.

---

## 1. Installation de l'extension

1. Ouvrez votre éditeur de code.
2. Accédez à l'onglet **Extensions** (ou utilisez le raccourci `Ctrl+Shift+X` / `Cmd+Shift+X`).
3. Recherchez **Kilocode** dans la barre de recherche.
4. Cliquez sur **Installer**.

---

## 2. Configuration d'OpenRouter

Une fois l'extension installée, vous devez l'associer à OpenRouter pour pouvoir exécuter des modèles.

### Configurer le nouveau fournisseur

1. Ouvrez les paramètres de l'extension Kilocode (via les paramètres de l'éditeur ou en cliquant sur l'icône de l'extension).
2. Localisez la section **Provider** (Fournisseur) et sélectionnez `openrouter`.
3. Recherchez le champ dédié à la clé API (`API Key`) et collez la clé générée.

Pour suivre votre consommation, utiliser le tableau de bord interne : `<INTERNAL_DASHBOARD_URL>`.


### Configurer les modèles du nouveau fournisseur :

1. Dans les paramètres, menu **modèles** sélectionner le modèle par défaut 1 de ces 3 modèles : 
- openrouter/Gemini 3.1 Pro Preview
- openrouter/GPT-5.3-Codex
- openrouter/Claude Sonnet 5


2. Ajoutez en **favori** les modèles suivants :
   * **Gemini 3.1 Pro Preview** 
   * **Gemini 3.5 Flash** 
   * **Claude Haiku 4.5**
   * **Claude Sonnet 4.6**
   * **Claude Sonnet 5**
   * **Claude Opus 4.8**
   * **GPT-5.3-Codex**
   * **GPT-5.5**
   * **GPT-5.6 Sol**
   * **GPT-5.6 Terra**
   * **GPT-5.6 Luna**


3. Renseignez l'un de ces deux modèles comme modèle par défaut selon vos préférences de rapidité ou de performance.
---

## 3. Vérification du fonctionnement

Pour vous assurer que l'installation est fonctionnelle :

* [ ] Ouvrir une nouvelle conversation
* [ ] Choisisser l'agent ASK, sélectionnez le plus petit modèle de vos favoris puis taper 'Bonjour' dans le prompt
* [ ] Le modèle doit vous répondre sans erreur.

Voici un tableau de qualification des modèles pour vos agents KiloCode, basé sur les données de pricing et de benchmarks les plus récentes (juillet 2026).

## 4. Qualification par agent / usage

| Modèle | Code | Ask | Plan | Architecte | Test Engineer | Doc Specialist | Debug | Code Reviewer |
|---|---|---|---|---|---|---|---|---|
| **Gemini 3.1 Pro Preview** | ✅ Bon (1M ctx, fort SWE-bench) | ✅ Bon | ✅ Très bon (long contexte) | ✅ Très bon | 🟡 Correct | ✅ Bon (multilingue) | 🟡 Correct | 🟡 Correct |
| **Gemini 3.5 Flash** | 🟡 Correct, rapide | ✅ Excellent (rapide/pas cher) | 🟡 Limité | ❌ Insuffisant | 🟡 Pour tests simples | ✅ Très bon rapport coût | 🟡 Correct | ❌ Insuffisant |
| **Claude Haiku 4.5** | 🟡 Correct sur tâches courtes | ✅ Excellent | ❌ Insuffisant | ❌ Insuffisant | 🟡 Tests unitaires simples | ✅ Excellent | 🟡 Correct | ❌ Insuffisant |
| **Claude Sonnet 4.6** | ✅ Très bon (équilibre) | ✅ Bon | ✅ Bon | 🟡 Correct | ✅ Très bon | ✅ Très bon (FR fluide) | ✅ Très bon | ✅ Bon |
| **Claude Sonnet 5** | ✅ Excellent (agentique, multi-outils) | ✅ Bon | ✅ Excellent | ✅ Très bon | ✅ Excellent | ✅ Très bon | ✅ Excellent | ✅ Très bon |
| **Claude Opus 4.8** | ✅ Excellent | 🟡 Surdimensionné | ✅ Excellent | ✅ Excellent (référence) | ✅ Excellent | ✅ Très bon | ✅ Excellent | ✅ Excellent (référence) |
| **GPT-5.3-Codex** | ✅ Excellent (spécialisé coding) | 🟡 Pas sa vocation | 🟡 Correct | 🟡 Correct | ✅ Excellent (terminal/CI) | 🟡 Correct | ✅ Excellent (debug agentique) | ✅ Très bon |
| **GPT-5.5** | ✅ Très bon | 🟡 Surdimensionné | ✅ Excellent | ✅ Excellent | ✅ Bon | ✅ Bon | ✅ Très bon | ✅ Excellent |
| **GPT-5.6 Sol** | ✅ Excellent (référence coding/raisonnement) | 🟡 Surdimensionné | ✅ Excellent | ✅ Excellent (référence) | ✅ Excellent | ✅ Très bon | ✅ Excellent | ✅ Excellent (référence) |
| **GPT-5.6 Terra** | ✅ Très bon (meilleur compromis) | ✅ Bon | ✅ Très bon | ✅ Bon | ✅ Très bon | ✅ Très bon | ✅ Bon | ✅ Très bon |
| **GPT-5.6 Luna** | 🟡 Correct (tâches simples) | ✅ Excellent (rapide/pas cher) | ❌ Insuffisant (contexte long) | ❌ Insuffisant | 🟡 Tests simples | ✅ Très bon (rapport coût) | 🟡 Correct | ❌ Insuffisant |

## 5. Rapport coût / raisonnement

| Modèle | Input / Output ($/MTok) | Contexte | Niveau de raisonnement | Rapport coût-efficacité |
|---|---|---|---|---|
| **Claude Haiku 4.5** | $1 / $5 | 200K | Faible-moyen | ⭐⭐⭐⭐⭐ (le moins cher) |
| **Gemini 3.5 Flash** | $1.50 / $9 | 1M | Moyen | ⭐⭐⭐⭐⭐ |
| **GPT-5.3-Codex** | $1.75 / $14 | 400K | Moyen-élevé (spécialisé code) | ⭐⭐⭐⭐ |
| **Claude Sonnet 5** | $2 / $10 *(promo jusqu'au 31/08/2026, puis $3/$15)* | 1M | Élevé | ⭐⭐⭐⭐⭐ (meilleur rapport actuel) |
| **Gemini 3.1 Pro Preview** | $2 / $12 | 1M | Élevé | ⭐⭐⭐⭐ |
| **Claude Sonnet 4.6** | $3 / $15 | 1M | Élevé | ⭐⭐⭐⭐ |
| **Claude Opus 4.8** | $5 / $25 | 1M | Très élevé | ⭐⭐⭐ (justifié sur tâches complexes) |
| **GPT-5.5** | $5 / $30 | 1M | Très élevé | ⭐⭐⭐ |
| **GPT-5.6 Luna** | $1 / $6 | 1M | Faible-moyen (long contexte limité) | ⭐⭐⭐⭐⭐ (le moins cher de la gamme) |
| **GPT-5.6 Terra** | $2,50 / $15 | 1M | Moyen-élevé | ⭐⭐⭐⭐⭐ (meilleur rapport de la gamme) |
| **GPT-5.6 Sol** | $5 / $30 | 1M | Très élevé (référence) | ⭐⭐⭐⭐ (justifié sur tâches complexes) |

## Variantes de raisonnment

Pour chaque modèle vous pouvez sélectionner le niveau de raisonnement :
Ce paramètre est aussi important que le choix du modèle.
- **LOW** => (réponse rapide, courte et coût faible)
- **Medium** => (réponse avec raisonnment modéré et coût raisonnable)
- **High** => (réponse avec raisonnment appronfondie et coût raisonnable si la question est complexe)
- XHigh ou plus => (réponse et raisonnment très long et **coût nettement plus élevé** pour un **gain souvent marginal** par rapport au niveau High

## Recommandations pratiques pour KiloCode

- **Ask / Doc specialist** → Haiku 4.5, Gemini 3.5 Flash ou **GPT-5.6 Luna** (coût minimal, latence faible, suffisant pour Q&A et documentation)
- **Code / Debug au quotidien** → Sonnet 5 (meilleur compromis agentique/coût actuellement, avec le tarif promo) ou GPT-5.3-Codex si vous voulez un modèle dédié aux boucles terminal/CI, ou **GPT-5.6 Terra** comme alternative polyvalente
- **Test Engineer** → Sonnet 4.6/5, GPT-5.3-Codex ou **GPT-5.6 Terra** (bon en exécution d'outils et boucles de test)
- **Plan / Architecte** → Sonnet 5 en usage courant, Opus 4.8, GPT-5.5 ou **GPT-5.6 Sol** pour les décisions d'architecture critiques (isolation multi-tenant, arbitrages MIG vs partitionnement logiciel, etc. — vu la nature de vos projets vLLM/RAG)
- **Code Reviewer** → Sonnet 5 pour un reviewer moins coûteux mais très solide, Opus 4.8 (référence qualité mais très coûteux) ou **GPT-5.6 Sol** (référence coding/raisonnement)
- **Tâche simple / Commentaires** → **GPT-5.6 Luna** (rapide, économique, mais attention : raisonnment limitée)


Notez que ces tarifs évoluent vite (la promo Sonnet 5 se termine le 31 août 2026, et OpenAI a consolidé sa gamme autour de **GPT-5.6 Sol / Terra / Luna** qui remplacent les anciens GPT-5.5 et GPT-5.3-Codex dans les usages quotidiens : Luna pour le volume/rapidité, Terra comme compromis, Sol en référence).
