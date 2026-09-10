[[_TOC_]]
| Version IWS | Version concernée | 
|:-----------|-----------:|
| IWS infinity |  Oui |
| IWS air design 2017 et inférieures |  Non|
#Gestion des fichiers less
Depuis la version Infinity le support d'appareils tactiles de différentes tailles / résolution a induit le besoin de crée un style par support. En effet afin que l’expérience utilisateur soit optimale les rendus s'adaptent en fonction de l'affichage.
Pour ce faire sous le répertoire "Styles", un répertoire "RWD" stock les fichiers less qui seront utilisés pour compiler les CSS particulières à chacun des appareils :

<ul><li>Desktop
                 <ul><li>rwd.desktop.mouse.less
                 </li><li>rwd.desktop.touch.less</li></ul>
      </li><li>Phone
                 <ul><li>rwd.phone.less</li></ul>
      </li><li>Tablet
                 <ul><li>rwd.tablet.less</li></ul>
                 </li><li>rwd.touch.less</li>
</ul>
Ce découpage est aussi présent coté Framework (à l'exception du desktop). Ces fichiers vont servir principalement à redéfinir des variables du iws.var.less (IsiFW.var.less coté framework). Ces variables sont elles utilisées dans les fichier less, des composants, et découpages logiques de l'application.

Par exemple :
Dans le fichier iws.var.less:

``` less
@dockedbar-height: 36px;
```
Dans le fichier rwd.phone.less

``` less
@dockedbar-height: 40px;
```

Dans le fichier IsiDockedBar.less

``` less
...
height: @dockedbar-height;
...
```

En mode téléphone la taille de la dockbar en hauteur sera donc de 40px si la variable n'est pas redéfinie dans les autres fichiers alors elle auront la taille 36px.

Remarque :
- Afin d'augmenter la lisibilité et la responsabilisation du less il a été décider d'arrêter le découpage struct et skin ceux-ci doivent être migrés dans des fichiers par composant / découpage applicatif.
- Pourquoi ne pas avoir fait de média query ? la réponse et simple si nous avions fait des media query nous aurions du ajouter en dur les tailles des différentes ruptures (cf. plus bas) ou générer un fichiers avec des variables contenant les ruptures et relancer la compilation des feuilles de CSS.

Il existe 3 ruptures qui sont modifiables par les clients via l'écran des options: 

|Libellé de l'option|Valeur par défaut |
|:------------|---------:|
|Transition smartphone vers petite tablette|768|
|Transition petite tablette vers tablette moyenne|992|
|Transition tablette moyenne vers grande tablette|1280|

En conséquence suivant le type d'appareil utilisé nous auront le résultat suivant en terme d'inclusion CSS (en plus des autres): 

|Option|Fichier de CSS inclus|
|:------------|---------:|
|&lt;Transition smartphone vers petite tablette & tactile|rwd.phone|
|&lt;Transition petite tablette vers tablette moyenne & tactile|rwd.tablet|
|&lt;Transition tablette moyenne vers grande tablette a tactile |rwd.tablet|

Les deux autres feuilles de style rwd.desktop.mouse et rwd.desktop.touch sont lié à l'utilisation des du bouton de changement de mode sur un pc tactile en haut à droite du bandeau sur le protail:
![image.png](.attachments/image-567a6fa8-def1-497f-b1a3-087544ced8fa.png)

#Les classes de la balise body
Le corps de la page (body) inclus des classes en fonction de l'appareil et du mode dans lequel l'application est affichée. Le point d'entrée de cette évaluation se trouve être la méthode EnsureIsRWD de la classe IsiUI et la méthode detectClient su IsiFw.ui.core.js:

|Libellé de l'option|Classes ajoutées sur la balise body pour le positionnement bootstrap ecran RWD uniquement|
|:------------|---------:|
|&gt; Transition smartphone vers petite tablette &lt;Transition petite tablette vers tablette moyenne|rupturePetit|
|&lt; Transition tablette moyenne vers grande tablette |rupturePetit ruptureMoyen|
|&gt; Transition tablette moyenne vers grande tablette|rupturePetit ruptureMoyen ruptureGrand|

Pour les tablettes uniquement (large pour les autres) :
|rupture|classe|
|:----------|---------:|
|&lt; Transition petite tablette vers tablette moyenne|small|
|&lt; Transition tablette moyenne vers grande tablette|medium|
|&gt; Transition tablette moyenne vers grande tablette|large|


|Type de device|Classes ajoutées sur la balise body|
|:------------|---------:|
|Mode téléphone|phone touch|
|Mode tablet|tablet touch|
|Mode pc non tactile |desktop|
|Mode pc tactile|desktop desktopTouchMode touch|

Le point d'entrée pour l'évaluation de l'appareil se trouve dans le IsiFw.ui.core.js méthode detectClient.
|Orientation de l'appareil|Classes ajoutées sur la balise body|
|:------------|---------:|
|Portrait|portrait|
|Paysage|landscape|


|L'état du curseur|Classes ajoutées sur la balise body|
|:------------|---------:|
|Ajout|state-add|
|Consultation|state-consult|
|Recherche|state-search|
|Modification|state-update|


Le code de l'écran est aussi inclus par exemple "HELP005".
Si l'écran est responsive "rwd".
Le nom du navigateur : chrome, edge, firefox...
Si l'application est en mode dev "debug".
Etat d'affichage : showAssociatedView,showForm.