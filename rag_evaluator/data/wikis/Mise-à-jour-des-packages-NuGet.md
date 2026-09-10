# Introduction

Cet article détaille la procédure à suivre lorsqu'on doit mettre à jour les packages NuGet, dans IWS Legacy.

# Quels sont les solutions ?

Il faut mettre à jour le framework Isilog correspondant à la version IWS.
La solution IWS (commencer par la iws.sln, puis la full pour valider que tous les packages sont dans la même version (cf. onglet "Consolidate" du manager de package).
Signaler dans `<INTERNAL_TRACKING_TOOL>` les impacts à prendre en compte.

# Comment faire ?
- mettre à jour les packages par groupe logique
- faire toutes les mises à jours mineures
- faire ensuite les mises à jours majeures
  - en cas de breaking change, faire une tâche et traiter dans un second temps

Très important : pour chaque package mis à jour, vérifier que les binding-redirect de tous les projets FW+IWS, sont à jour (avec la nouvelle version)

# Quoi tester ?

Il faut tester :
- IWS (rechercher un dossier, prise en compte, lui ajouter une PJ, générer une procédure et réaliser des actions)
- Web API : utiliser le site API, cf. [Tester l'API Web](<INTERNAL_WIKI_URL>).
- IIM
- Le site de Diag

# Comment tester ?
- lancer l'application fuslogvw (ouvrir une console powershell liée à l'environnement de visual studio, en admin)
- utiliser les applications 
- vérifier dans fuslogvw qu'aucune trace n'est remontée

Pour les détails sur `fuslogvw`, voir : [Résoudre l'erreur Impossible de charger le fichier ou l'assembly](<INTERNAL_WIKI_URL>).
