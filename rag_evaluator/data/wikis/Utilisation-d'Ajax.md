[[_TOC_]]

#Objet
Ce document définit la méthodologie pour utiliser l’AJAX, technologie Internet permettant le lancement de requêtes asynchrones à partir d’un client sur un serveur Web.

#Domaine d'application
Cette instruction est applicable à tous les développements Visual Basic.NET

#Description
L’**Asynchronous Javascript And XML** (AJAX) est une technique qui permet :
- Le lancement de requêtes HTTP au serveur, et ce sans rechargement de page.
  - Méthodes POST, GET, HEAD ou tout autre méthode supportée par le serveur,
  - Lancement asynchrone (le script côté client continue à s’exécuter),
  - Lancement synchrone (le script côté client attend la réponse du serveur).
- La lecture des réponses sous forme XML ou texte.

#Méthodologie de développement
##Programmation côté serveur : `VB.NET`
La page `IsiAjax.aspx` est la page qui gère toutes les sollicitations asynchrones des clients, et qui les met en corrélation avec les traitements adéquats. Ces traitements sont appelés **Stratégies**. Chaque stratégie différente doit avoir sa propre classe dérivée. 

Ainsi, après s’être assuré que le genre de traitement que l’on désire implémenter n’existe pas, la première étape est de faire hériter une nouvelle classe à la classe `IsiAsyncStrategy`. Cette classe aura pour but de prendre en entrée des informations envoyées par le client, de les traiter (notamment en consultant la base de données), et d’envoyer une réponse au client.

Par exemple, la classe `IsiAsyncCallCoverStrategy` est une stratégie qui consiste à :
- Prendre en entrée une date d’appel, un numéro de contrat et un identifiant d’objet,
- Renvoyer au client la couverture de l’appel.

La fonction principale à surcharger est `ExecuteRequest`, qui contient le traitement nécessaire, et qui renvoie une chaîne de caractères au client.
>Cette chaîne de caractères pourra contenir différentes valeurs qui devront être sérialisées. Pour cela, on pourra utiliser le séparateur `#` et coder (échapper) ce même caractère dans cette liste de valeurs. Côté client, il suffira de **désérialiser** cette chaîne (`split` en Javascript), puis de des-échapper le caractère `#` des valeurs.

Il faut ensuite adapter la fonction `Page_Load` d’`IsiAjax.aspx.vb` afin qu’elle prenne en compte cette stratégie.

Attention, notez que dans tous les cas, le client doit renseigner au serveur le nom du traitement qu’il désire. Il doit donc envoyer une variable nommée **Traitement**. (Par exemple, `IsiCallCover` pour l’exemple ci-dessus).

##Programmation côté client : `Javascript`
Avant de commencer à développer côté client, il faut d’abord savoir sur quel **événement** provoqué par l’utilisateur l’AJAX sera lancé. Il faudra ensuite déterminer quelle fonction sera appelée lors de cet événement.

S’il s’agit de composants Infragistics, on peut directement renseigner, côté VB, quelle fonction devra être appelée lors d’un événement sur le composant.

Voici un exemple de code dans `IsiPage.vb` :
```vb
pMenuListBar.ClientSideEvents.BeforeItemSelected = "iws_Menu_BeforeItemSelected"
```
Cela signifie que la fonction javascript `iws_Menu_BeforeItemSelected` sera appelée lors d’un clic sur un item de la `ListBar pMenuListBar`.

Dans cette fonction appelée sur un événement, il faut directement utiliser la classe `IsiAjax`. Cette classe peut être utilisée de manière générique, ou spécifique (il faudra donc la dériver – c’est possible en Javascript !).

##Description de la classe IsiAjax
![image.png](/.attachments/image-cc707140-cc0c-44a1-95be-a7f7193bea21.png)

- `IsiAjax(sUrl)` : Le constructeur prend en paramètre l’URL de la page sollicitée. Dans le cas d’IWS, c’est la page IsiAjax.aspx qui est sollicitée.
- `setOutput(sCtrlID`) : Fonction qui définit le contrôle HTML vers lequel la réponse du serveur est redirigée. Il peut s’agir d’un `<TEXTAREA>`, `<DIV>` ou même `<BODY>`.
- `redirectResponseToOutput(sData)` : Permet de rediriger les données sData reçues du serveur vers le contrôle dont l’ID a été défini avec setOutput. Cette fonction est destinée à être surchargée pour des utilisations spécifiques d’IsiAjax.
- `AsyncExecute(sData, sMethod, bCancelLastRequest, sReturnType, oAjaxChild)` : Fonction la plus **importante**, elle lance la requête au serveur en mode Asynchrone (voir plus bas) :
  - `sData` (string): Données à envoyer au serveur. Elles sont concaténées à l’URL en cas de méthode GET. Ne pas oublier de renseigner la variable Traitement afin que la page IsiAjax.aspx.vb puisse exécuter la bonne stratégie.
  - `sMethod` (string): Uniquement ‘POST’ et ‘GET’ ont été implémentés. Utiliser de préférence POST pour passer des données volumineuses qui nécessitent un traitement côté serveur.
  - `bCancelLastRequest` (booléen): Mettre à ‘true’ si on désire annuler la dernière requête qui n’a pas encore reçu de réponse.
  - `sReturnType` (string) : ‘TEXT’ ou ‘XML’. Format de la réponse du serveur.
**ATTENTION** Si on précise le format XML, il faut que la réponse du serveur soit du XML, sinon la requête échoue.
  - `oAjaxChild` : Etonnant, mais si nous utilisons une classe dérivée d’IsiAjax, **il faut passer en paramètre l’objet lui-même**. Cela est la seule façon de gérer la surcharge en javascript.
- `SyncExecute (sData, sMethod, sReturnType, oAjaxChild)` : A l’instar de AsyncExecute, cette fonction lance une requête Synchrone au serveur. Elle retourne directement la réponse. Si oAjaxChild est renseigné (pas à NULL), alors la fonction `redirectResponseToOutput` est également appelée lors de la réception de la réponse.

###Utilisation générique
L’utilisation générique consiste simplement à afficher dans un contrôle (plus précisément d’initialiser l’attribut **value**) la chaîne de caractères renvoyée par le serveur. Il n’y a aucun traitement particulier sur la chaîne.

 

###Utilisation dérivée.
Il sera souvent nécessaire de dériver la classe `IsiAjax` afin qu’elle traite la chaîne de retour. La principale fonction à surcharger est `redirectResponseToOutput(sData)`. C’est dans cette fonction qu’il faudra coder tous les traitements nécessaires sur la chaîne renvoyée par le serveur.
**Par exemple :**
- Gérer la désérialisation de la chaîne,
- Distribuer la réponse à plusieurs composants HTML,
- Lancer d’autres fonctions dès la réception de cette réponse.
 
Voici un exemple pour dériver une classe Javascript :
```js
function IsiAjaxDerive(sURL)
{
 this.parent = IsiAjax;
 this.parent(sURL);
 // Fonction surchargée.
 this.redirectResponseToOutput = function(sData)
 { 
  if (sData)
  { 
   // Ici, traitement spécifique…
  } 
 }
}
 
IsiAjaxDerive.prototype = new IsiAjax() ;
```
 

La dernière ligne est primordiale pour assurer l’héritage des fonctions de la classe mère `IsiAjax`.

##Fonctionnement Asynchrone ou Synchrone ?
Le fonctionnement Asynchrone est pratique lorsqu’il n’est pas nécessaire d’attendre la réponse du serveur pour continuer l’exécution normale du code côté client (par exemple `IsiSuggest`, qui a juste un fonctionnement informatif).

Le fonctionnement Synchrone sera primordial lorsque des questions doivent attendre la réponse du serveur (le navigateur reste bloqué tant que le serveur n’a pas répondu). De plus, la réponse du serveur est directement retournée, sans avoir besoin de surcharger `redirectResponseToOutput`.
>La seule différence de programmation vient de l’appel de fonction `AsyncExecute` ou `SyncExecute`.

##Exemple concret
Je veux afficher dans un contrôle HTML (prenons une DIV d’identifiant « DIV1 ») la réponse du serveur en exécutant la stratégie « test », et ce sans rechargement de page, simplement en cliquant sur un bouton.

En considérant que `onButtonClick()` est la fonction appelée lors de l’appui sur le bouton en question :

```html
<SCRIPT language=’javascript’ type=’text/javascript’ SRC=’./scripts/IsiAjax.js’></SCRIPT>
<SCRIPT language=’javascript’ type=’text/javascript’>
function onButtonClick() {
 var oAjax = new IsiAjax("../../Classes/IsiAjax/IsiAjax.aspx");
 oAjax.setOutput(‘DIV1’) ;
 oAjax.AsyncExecute(‘traitement=test_strategy’, ‘GET’, true, ‘TEXT’, oAjax) ;
}
</SCRIPT>
```

Côté serveur, on aura (`IsiAjax.aspx.vb`) :

```vb
Select Case Request.Item("Traitement")
Case "test_strategy"
mStrategy = New IsiTestStrategy()
Case …
End Select
```


`IsiTestStrategy` est une classe dérivée de `IsiAsyncStrategy`, dont la fonction `ExecuteRequest` devra être surchargée et contenir le traitement nécessaire (avec possibilité de consulter la base de données). Cette fonction renvoie simplement un `String` qui sera envoyé au client, et qui sera affiché dans l’élément DIV1 de notre page HTML.