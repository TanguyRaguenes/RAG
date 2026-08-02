[[_TOC_]]

# Introduction
Vous souhaitez devenir un vrai petit hackeur, alors ne partez pas vous êtes au bon endroit.
Ici nous allons voir comment utiliser Fiddler.
Fiddler est disponible ici : **W:\\_Outils html-Web\Fiddler**.

# Description
Une fois installé, Fiddler est disponible en recherchant "Fiddler Classic" dans la barre de recherche Windows.

## Requête http
![image.png](/.attachments/image-9e2fa06a-1bae-4cbf-8d40-8272ef8f8ab8.png)

Les requêtes HTTP sont visible sur la partie gauche de Fiddler.
Toutes les requêtes envoyées et reçus par les navigateurs seront affichées dans ce volet de l'application.

## Mettre un breakpoint
-> 2 méthodes et ça se passe dans les menus tous en bas de Fiddler (la deuxième est mieux) 

### Méthode 1
Il est possible d'intercepté une requêtes avant qu'elle soit envoyé dans l'internet pour cela deux possibilité s'offre a nous.

La première est de cliquer sur le bouton ultra secret de fiddler.
![image.png](/.attachments/image-e9d47425-3712-4ddd-8d88-b3398fc13fed.png)

Ce bouton permet de bloquer les requêtes afin de pouvoir les modifier.

Ce bouton possède 3 états, le premier lorsqu'il est tout blanc signifie qu'il ne bloque rien
Le second visible sur l'image ci-dessous est pour intercepté les requêtes sortantes
![image.png](/.attachments/image-087e6b66-7267-4cb5-b70b-9868c192103e.png)

enfin le 3e état est pour intercepté les requêtes entrantes
![image.png](/.attachments/image-923211f2-d465-4996-a02e-766aa4c3c945.png)

### Méthode 2
une barre noire est présente dans Fiddler permettant d'exécuter des commandes
![image.png](/.attachments/image-4b5eb0a9-9142-407f-92a8-fe8fcbdbf12b.png)

Pour créer un breakPoint il faut taper la commande suivante :
``` URL
bpu [monUrl]
```

remplacer [monUrl] par l'url que vous souhaitez break ou juste un mot clé de la requête ( ex : IsiMarketCatalogCart)

<u>exemple :</u>
``` URL
bpu https://rbed.isilog.fr/xlv50/Classes/IsiAjax/IsiAjax.aspx
```
 D'autres commandes existent, voir [ici](https://docs.telerik.com/fiddler/knowledge-base/quickexec)

Pour sortir d'un BreakPoint il faut appuyer sur le bouton "Go" dans la toolbar.
![image.png](/.attachments/image-14490fe5-cc3b-43b1-98db-ea79b3f3f409.png)

## Modifier une requête
Une fois que vous avez bloqué votre requête vous avez la possibilité de l'envoyé.
Pour cela, dans la partie de droite de Fiddler il faut se positionner sur l'onglet "Inspector" puis le sous-onglet "Raw".
Une fois positionné sur l'onglet vous pouvez modifier la requête comme bon vous semble.

![image.png](/.attachments/image-adbfdcd5-01ec-4f5b-a6a7-1398bba1dad2.png)

Pour envoyer la requête après l'avoir modifiée, il faut appuyer sur le bouton Run to Completion.

## Utiliser les filtres
Il est possible de filtrer les requêtes affiché dans Fiddler.
Cela peut être utile afin de facilement retrouver les requêtes qui nous intéressent.

![image.png](/.attachments/image-f7bafc23-f16f-4b4d-90b7-c8379cf04281.png)

Pour activer les filtrer il faut se rendre dans l'onglet "Filers" puis de cocher la case "Use Filters".

Dans la partie "Hosts", sélectionner dans la seconde liste déroulante "Show only the following Hosts"
![image.png](/.attachments/image-21c6513c-d4b8-4b2d-889d-2b515988573c.png)

puis renseigner les urls que vous souhaitez voir apparaitre (voir image ci-dessus)

## Ré-exécuter une requête
Pour exécuter une nouvelle fois une requête qui est déjà passée en luis apportant des modifications, il suffit de la sélectionner et d'appuyer sur la touche "E". Elle se retrouve alors en mode "édition". Il suffit de la modifier et de l'envoyer.
