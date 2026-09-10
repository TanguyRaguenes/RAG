Suite à la réunion du 29/06/2022, la gestion des traductions UK sera la suivante :

# Objectifs priorisés à partir de la XL V7
Les priorisation des traductions à traiter est la suivante :
- **Priorité 1** : tâche `<INTERNAL_TASK_TITLE>` consacrée aux nouveautés de la version, sous la rubrique Traduction dans `<INTERNAL_TRACKING_TOOL>`
- **Priorité 2** : tâche `<INTERNAL_TASK_TITLE>` consacrée aux incidents d'aide en ligne, sous la rubrique Traduction dans `<INTERNAL_TRACKING_TOOL>`

# Estimation et planning
On observe deux modes/types de tâches de traduction : **création** (traduction de nouveautés, nouveaux contenus) et **révision** (traduction de modifications, tâche `<TICKET_ID>`).

## Mode création (traduction de nouveautés, nouveaux contenus)
Dans le fichier Excel, estimer en nombre de mots en prenant en compte l'objectif de 1200mots/j.

## Mode révision (traduction de modifications)
1. À partir des changesets Azure, le rédacteur technique estime la tâche de la manière suivante :
   - 1h pour une « petite page » – à voir l’estimation en Ko sur le serveur (ex : 20 – 40 Ko) ;
   - 2h pour une moyenne à affiner l’estimation en Ko (ex : 40 – 80 Ko)
   - 4h pour une grande page (au-delà du palier précédent)

1. Dans le fichier Excel `<INTERNAL_SHARE>\Traduction\<TRACKING_FILE>.xlsx`, renseigner :
   - l'estimation en colonne **G** par le rédacteur technique ;
   - avant de commencer la tâche, le traducteur envoie sa contre-estimation afin d'ajuster le prévisionnel dans `<INTERNAL_TRACKING_TOOL>` et le planning ;
   - le temps passé en colonne **H** par le traducteur.

## Langue et consignes de traduction
1. À partir du 27/02/2025, la langue de rédaction pour les traductions est l'**anglais américain en-US**. Se référer aux [bonnes pratiques de rédaction](<INTERNAL_WIKI_URL>).

1. Les libellés de l'aide en ligne (nom d'écran, de menu, de requête, de bouton, etc.) **doivent être conformes aux** libellés de l'interface accessible via `<INTERNAL_APPLICATION_URL>`.
Si des erreurs ou mauvaises traductions sont présentes dans l'interface, il faut prévenir la conception pour qu'on fasse corriger le dysfonctionnement de libellés avec report dans l'aide en ligne.




