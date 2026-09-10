#Préambule

Le but des tests unitaires dans Azure DevOps est de fournir une meilleure traçabilité, en étant lié par l'intermédiaire d'un Work Item ou d'un plan de tests. Cela permet de garantir leur présence et leur exécution contrairement aux tests présents dans les fiches de développement ou dans Squash TM.



# Création d'un cas de test

## Introduction

Lorsque vous commencez votre tâche, vous devrez créer un "Test case" au niveau de votre Work Item avec les étapes des tests que vous pensez faire pour valider votre développement. 

##Méthodologie

Pour créer votre premier cas de test, vous devrez créer un… "Test case" (oui, oui !).


Deuxième étape, on choisit l'emplacement, puis on clic sur le bouton "Add" :

![image.png](/.attachments/image-134cca53-37da-4f33-adcd-3005a6d4940e.png)


On définit ensuite simplement nos cas de tests, comme on le ferait avec Squash. On peut également ajouter des pièces jointes si on souhaite montrer le résultat attendu sans devoir à faire tout un corpus.


![image.png](/.attachments/image-a1d3f6d4-5e44-4f45-93aa-33722b0696bf.png)

## Création de variables personnalisés

Là où se distinguent entre autres les cas de tests dans Azure, c'est qu'on peut créer si on le souhaite des variables. 
Elles commencent systématiquement par un arobase, et les valeurs peuvent être définies en dessous du tableau des étapes des différents cas de tests.

Dans notre cas, la variable **@navigateur** contient les valeurs suivants :
![image.png](/.attachments/image-2da0ae39-6a40-4a63-9ca6-41080348bd2d.png)


L'intérêt de procéder de cette manière est d'éviter de devoir dupliquer autant de fois votre cas de test qu'il y a de valeurs dans les variables. Azure le fera pour vous au moment où vous exécuterez le cas de tests.


# Lier le cas de test à votre Work Item

Deux méthodes :

- Soit depuis votre test unitaire (avec un lien de type "Tests") :

![image.png](/.attachments/image-9ae7d11f-e16e-4ad4-937c-f2781d4756ce.png)

- Soit depuis un work item (avec un lien de type "Tested by" :

![image.png](/.attachments/image-0135d3ff-e1fc-423e-b7b3-40b76085d594.png)



# Exécution de vos cas de tests

- Demandez à votre analyste préféré d'ajouter votre cas de test dans le plan de tests de la version :

![image.png](/.attachments/image-94aad3a2-a216-4701-878c-c026416f6010.png)

En double-cliquant sur la ligne on peut également voir les détails des dernières exécutions ainsi que de leurs statuts :

![image.png](/.attachments/image-5f5f1951-9755-46e3-812c-c558ef720506.png)

Pour ensuite exécuter votre plan de test, sélectionnez votre ligne que vous souhaitez tester puis cliquez sur "Run for web application".

La fenêtre suivante s'ouvre :

![image.png](/.attachments/image-56a6a8d7-e53e-4280-893f-66b17afe613e.png)

Pour chacune des étapes de l'itération correspondante, on peut valider ou refuser l'étape associée.

Sur la capture on peut constater qu'il y a 6 itérations, elles correspondent aux valeurs définies dans les différentes variables (dans notre cas, la variable **@navigateur** créée tout à l'heure).

Une fois terminé, on peut cliquer sur le bouton *"Save and close"*.



