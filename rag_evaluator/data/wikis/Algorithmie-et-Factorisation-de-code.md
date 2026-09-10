	 
#Objectif
Ce mode opératoire fournit les bonnes pratiques pour écrire un algorithme ou en modifier un existant. Cela concerne tous les langages (VB.NET, PL/SQL etc.), on considèrera qu'un trigger est assimilable à une procédure dont la conception doit respecter les mêmes bonnes pratiques qu'une procédure ou fonction .NET

#Définitions
- Algorithme : correspond à une procédure de transformation de données d’entrée en données de sortie, codée selon des calculs précis. En d’autres termes, c’est une suite logique d’instructions qui permet d’automatiser la mise en œuvre d’un processus quelconque (multiplier deux nombres, créer un programme informatique, exploiter une base de données…). Pour se faire, il prend en compte le problème ainsi que la décomposition étape par étape des solutions permettant de le résoudre. 

- Factorisation : consiste à rassembler les suites d'instructions identiques dispersées dans un programme en une fonction, pour améliorer la lisibilité du code et en faciliter la correction et les modifications ultérieures. 

- Récursivité : une fonction ou plus généralement un algorithme qui contient un appel à elle-même est dite récursive. Deux fonctions peuvent s'appeler l'une l'autre, on parle alors de récursivité croisée. 

- Inter-blocage (deadlock) : phénomène qui peut survenir en programmation concurrente. L'interblocage se produit lorsque deux processus concurrents s'attendent mutuellement. Les accès concurrent avec réservation de ressource concerna aussi bien la base de donnée que des objets dans un développement indépendant de la base. 

#Création
La première chose à faire avant de créer un algorithme est de faire l'inventaire de ceux déjà existant dans un périmètre similaire, **il faut toujours privilégier la factorisation de code plutôt que d'en créer systématiquement du nouveau à chaque fois**.

Le découpage du processus doit tenir compte des besoins de ré utilisabilité et de manière générale pour une meilleure lecture, et une meilleure maintenabilité il est impératif de découper les traitements complexes afin qu'un algorithme complexe se décompose en un bloc principal clair qui s'appuie sur des appels à des algorithmes simples via des objets, fonctions ou procédures.

Ainsi plutôt qu'un algorithme de plusieurs milliers de ligne on préférera ne pas excéder quelques centaines de lignes avec un découpage en blocs clairs et commentés avec des appels à des fonctions d'une taille semblable et elle-même parfaitement commentées et qui peuvent plus facilement être réutilisables.

**Il est important** de s'assurer dans un algorithme que tous les "Si" ont un "Sinon" quitte à mettre un commentaire 'Pas de traitement à effectuer' dans le Sinon lorsqu'il n'y a rien à y faire, ceci clarifie le fait que c'est un choix et non un oubli.

**Il est important** de s'assurer qu'en cas d'erreur inattendue dans une partie de l'algorithme l'erreur est gérée et assure l'intégrité du traitement en sortie (i.e. le traitement est fait de manière jugée correcte ou le traitement n'est pas fait du tout et l'information est transmise à l'appelant)

#Modification
La modification d'un algorithme existant ne doit pas se faire systématiquement par un ajout d'une condition ou d'un bloc complémentaire car le plus souvent cela alourdit le traitement et nuit aux performances. Il est donc obligatoire d'analyser l'algorithme actuel dans son ensemble pour voir comment intégrer les modifications en mesurant ainsi les impacts et en adoptant ainsi une écriture optimale.

Les bonnes pratiques de création d'un algorithme s'appliquent alors de la même façon à la modification une fois que l'analyse préalable en a été effectuée.

#Optimisation par la mise en cache & les données pré calculées

Un algorithme peut avoir besoin de données résultant aussi bien de calculs en temps réel que d'un référentiel variant peu ou pas ; il peut alors être intéressant d'optimiser via la mise en cache ou le pré calcul.

La mise en cache des données est un mécanisme standard des bases de données mais c'est le SGBD qui décide de ce qu'il met en cache en fonction de ses limites en RAM et des requêtes en cours. 

On décide donc de mettre en cache des données pour les besoins d'un algorithme lorsque
- le volume de données est raisonnable
- le temps d'initialisation la première fois est acceptable  et si des rafraichissements sont nécessaires celui-ci doit également être acceptable
- les données mises en cache sont utilisées de manière récurrente

Une autre façon d'optimiser les performances de mise à disposition de données est de les calculées non pas au moment de l'exécution mais en amont. 

Ceci peut se faire en temps réel (exemple : je crée un débit sur un compte, je mets à jour immédiatement le solde du compte qui est stocké) ou bien de façon périodique (tâche planifiée de calcul de données).

Le choix dépend de la complexité du calcul, de la fiabilité de la donnée souhaitée à l'instant t et de la capacité de stockage acceptable.

**Par exemple** si le calcul est simple (exemple si champ date antérieur à maintenant alors résultat= -1 sinon résultat =0) il peut être plus performant de faire le calcul à la volée plutôt que de générer des mises à jour supplémentaire en base.

**De manière générale** la décision d'une mise en cache ou d'un pré calcul peut être le signe que les algorithmes et la modélisation ne sont pas optimums aussi ce recours ne doit pas être systématique mais doit être analysé.


#Risques-L'effet boite noire

Un algorithme qui fait appel à des fonctions ou procédures risque de faire perdre de vue la quantité d'opérations et la nature des opérations réalisées dans ces fonctions (qui elle-même peuvent en appeler d'autres), cela peut :
- [x] Nuire aux performances car on ne voit plus que potentiellement la même opération peut être effectuées plusieurs fois au lieu d'une (exemple: on appelle deux fonctions A & B qui lancent toutes les deux un traitement C)

- [x] Favoriser les inter-blocages car les réservations de ressources effectuées dans les fonctions ne sautent pas aux yeux, on n'a donc plus de vision globale des poses de verrous, sélections et mises à jour

- [x] Entraine des risques de récursivité indirecte (fonction A qui peut utiliser une fonction B qui peut utiliser à son tour une fonction A), la récursivité directe est plus visible dans l'algorithme principal.




Globalement toute utilisation d'un objet au sens large (objet, fonction, procédure etc.) nécessite d'étudier au préalable les traitements que son utilisation implique

**Exemple :** la simple création d'un objet peut impliquer l'exécution d'algorithmes complexes dans le constructeur, cela peut charger des volumes important de donnés. Une simple ligne de code qui crée un objet peut paraître optimale, mettant en valeur la réutilisabilité et cela peut être contre performant. Il en va de même pour un simple appel à une méthode d'une classe.

**Autre exemple :** une simple opération SQL sur un enregistrement (UPDATE ou DELETE par exemple) peut entrainer une boucle non maitrisée de triggers... 

Ceci concerne aussi la simple consultation ou modification d'une  propriété d'une classe qui si elle a encapsulée des traitements sur le "Property Get" ou le "Property Let" peut entrainer des traitements (effet "boite noire")

On fera par exemple attention à ne pas appeler plusieurs fois une fonction ou proriété si on peut s'en passer :

Exemple :
``` VB
If o.GetCumul() > 0 and o.GetCumul() <> SousTotal Then
	Total=o.GetCumul()+PrixUnitaire
End If

' ------ Il faut préférer cette écriture:
Cumul = o.GetCumul() 'je mémorise dans une variable le résultat de la fonction : 1 seule exécution

If  Cumul > 0 and Cumul <> SousTotal Then
	Total = Cumul +PrixUnitaire
End If
```


#Risques-usure du code

Le non-respect de l'analyse préalable et de la factorisation des algorithmes entraine un phénomène d'usure du code c'est à dire un code qui par ajout successifs de blocs de code et d'évènements en plus des blocs existant devient trop difficile à maintenir et qui favorise :
- Une baisse des performances
- Une hausse des bugs notamment des régressions

#Risques-intégrité des données
Les algorithmes complexes mettant à jour beaucoup de données en base, en cache ou dans des objets présentent plus de risque d'avoir des pertes d'intégrité de données.
Les algorithmes doivent être suffisamment clairs pour maitriser 
- les transactions
- la gestion des erreurs
- les données mises à jour, l'ordre de mise à jour et le nombre de mises à jour (exemple : éviter de faire deux fois un cumul)

#Risques-inter blocage
Les algorithmes doivent prévenir le risque suivant :
```
•	Le processus P1 
o	réserve la ressource A 
o	réserve la ressource B 
o	met à jour la ressource C
o	libère B
o	libère A
•	Le processus P2 
o	réserve la ressource B
o	réserve la ressource A 
o	met à jour la ressource D
o	libère A
o	libère B
```
Ces deux processus peuvent tomber en interblocage. Pour prévenir ce risque il est conseillé de maîtriser l'ordre des poses de verrous afin que ce soit le même dans les algorithmes touchant aux mêmes données.

#Risques- blocage
Les algorithmes doivent prévenir le verrouillage d'une ressource pour laquelle il existe un risque que l'algorithme soit trop long, n'aboutisse pas ou se termine par une non libération de la ressource. 

Les cas typiques sont 
- la boucle infinie
- la récursivité infinie
- la non libération des ressources en cas d'erreur inattendue

