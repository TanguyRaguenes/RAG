
1.   Objectif
L'objectif de ce document est de décrire les règles et bonnes pratiques de modélisation IWS avec AMC designer.

2.   Pré-requis
Les pré-requis sont les suivants :

- Connaissance des méthodes de modélisation (UML/MERISE)
- Connaissance des SGBD (gestion des clés primaires, étrangères)
- Connaissance de l’outil de modélisation AMC Designer

3.   Règles de nommage
3.1.                      Entités

Le nom des entités doit respecter les règles suivantes afin de générer des noms de tables exploitables:

- Ne jamais excéder 30 caractères
- Etre français
- Etre en majuscule
- Ne comporter exclusivement que des caractères de l’alphabet non accentués

 

Pour toutes les entités systèmes, afin de les différencier des autres, on ajoutera le préfixe suivant «Z_ » afin de les différencier des autres entités, exemple Z_ECRAN.

 

Le nom des tables doit être cohérent avec ce qu’elle contient. Par exemple si une entité contient des contrats, l’entité se nommera naturellement « CONTRAT ».

Pour certaines entités, afin d’éviter un nom trop verbeux, on utilisera des abréviations. Par exemple « UTILEQUIP » est l’entité qui contient les affectations d’utilisateur à des équipes.

On n’emploiera pas de nom  en conflit avec des objets systèmes et commandes Oracle ou SQL Server, exemple : ACTION, INSERT, PIVOT etc.

 

Lorsqu’une entité ne contient pas de données pouvant exister seules (i.e. entité de détail d’une autre entité), alors on préfixera cette entité par le nom de son entité mère (ou une contraction si elle est trop longue), exemple « UTILEQUIP » pour les équipes de l’utilisateur (entité UTILISATEUR) et non « EQUIPEUTIL ».

 

Une nouvelle entité doit apparaître dans au moins un diagramme.

 

 

3.2.                      Champs

Les champs doivent avoir :

Un code : le code est composé d’un préfixe et d’un nom en français, on peut utiliser un suffixe lorsque plusieurs types d’informations se répètent dans une même entité. Les préfixes sont :
- C_ pour un code
- L_ pour un libellé
- N_ pour un nom ou un nombre
- D_ pour une date
- DD_ pour une date de début
- DF_ pour une date de fin
- F_ pour un booléen
- VA_ pour une valeur (alpha ou numérique)
- DU_ pour une durée
- U_ pour une unité
- Q_ pour une quantité
- T_ pour un type
- PXS_ pour un prix saisi
- PXU_ pour un prix utilisé
- MTS_ pour un montant saisi
- MTU_ pour un montant utilisé
- C_LOV_ pour un champ exploitant une LOV
Un libellé : le libellé est en français, il doit être concis et intelligible
Une description : on y indique le rôle fonctionnel, dans le cas de liste de valeurs fixes on énumère les valeurs possibles et leur signification
Un domaine : c’est le domaine de données, il permettra de calculer le type de données et la taille.
 

3.3. Renommage
 

Lors du renommage d’une entité ou d’un champ, il est obligatoire de faire une mesure d’impact vis-à-vis du spécifique et de l’existant. Il faut vérifier si l’élément à renommer fait l’objet des manipulations suivantes :

- Des requêtes
- Du paramétrage spécifique
- Des triggers, procédures stockées…
 

Prenons l’exemple d’une requête, celle-ci se base sur le nom de la table en dur, si le nom de la table change, la requête devient obsolète et va planter.

 

4.   Champs système
On utilisera un mécanisme d’héritage pour appliquer les éléments suivants à une entité :

 

- Prise en charge des signatures (obligatoire si on souhaite gérer de l'export de paramétrage sur cette entité)
- Date de création
- Date de modification (obligatoire s’il y a un formulaire Web exploitant cette entité)
- Date d’archivage
- Code identifiant externe
 

5.   Champs de type liste
Les champs de type liste peuvent s’appuyer soit sur une LOV (Z_LOV, non multilangue mais enrichissable) soit sur une famille de message (Z_FAMMESSWEB, multilangue mais non enrichissable)

6.   Valeurs par défaut
Les valeurs par défaut booléenne doivent être mise dans le MPD lorsque la valeur est "Vrai" (-1 en Oracle, 1 en SQL Server) et dans le MCD sinon.

 

7.   Relations entre entités
Le MCD actuel a historiquement quelques associations. Désormais on utilise systématiquement des entités avec des relations.

8.   Entité d'association
Créer une entité d'association avec des relations. La clé peut alors être formée des clés de relations (relation dépendante) ou d’une clé à partir des attributs de l’entité d’association (compteur ou autres)

 

9.   Ordre des champs dans la table
Clé primaire en premier, clé père en second, puis champs dans l'ordre du formulaire puis champs systèmes.

 

10.  Mise en forme des diagrammes & commentaires
 

Tout ajout/modification/suppression dans le MCD implique la mise à jour des diagrammes impactés dans le MCD puis dans le MPD Oracle.

 
Le diagramme doit contenir les entités principales de la fonction représentée avec l’intégralité des champs. Ces champs peuvent être en relation avec d’autres tables. On affichera la relation et la table connexe dans le diagramme uniquement lorsque :

Elle n’apparaît dans aucun autre diagramme
Elle est obligatoire dans une des entités principales du diagramme
Son affichage est nécessaire à la compréhension fonctionnelle, par exemple des tables temporaires ou de statistiques qui ne sont pas en relation peuvent être affichée pour rappeler qu’elles ont un rôle
 

On n’affichera donc pas systématiquement toutes les entités étrangères (et surtout pas récursivement) afin de conserver un diagramme lisible.
 

Les commentaires doivent être inscrits dans le MCD et complété dans le MPD pour les objets qui n'existent pas dans le MCD (clés étrangères etc.)
 

Lorsqu’une table est utilisée pour plusieurs processus distincts, alors on créera un diagramme dédié par processus avec des instances de tables préfixées par I_ pour les distinguer des vraies tables exploitées dans la base.

 

La description de l’instance indiquera la table de base et précisera que c’est une instance.

On ne dupliquera dans l’instance que les champs exploités pour ce processus en modifiant leur libellé pour qu’il corresponde aux terminologies du processus (i.e. celles de l’IHM)

11. Suppressions de colonnes ou de tables (ou recyclage)
Toutes colonnes ou tables pouvant accueillir des données utilisateur ne doit en aucun cas être supprimées ou réutilisée pour un autre usage. Les paramétrages spécifiques chez nos clients peuvent les exploiter

 
12. Modélisation d'un prix ou d'un montant
IWS gère la devise, donc chaque modélisation d'un prix doit être associée à une devise.
Il faut également se poser la question sur la présence d'une quantité et d'un code TVA.
Dans le cas particulier des lignes de détail dépendant d'une entête (commande, contrat, ...), la devise de la ligne est reprise de l'entête, il n'est donc pas nécessaire de modéliser la devise sur la ligne.
 