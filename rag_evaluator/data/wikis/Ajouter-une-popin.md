[[_TOC_]]

# Développement
##Créer une popin générique
Il est possible de créer une popin plus générique (utilisant un appel Ajax) sans classe VB si il n'y a besoin que d'un texte et des boutons standard.
- Dans un fichier JS :
   - Créer une fonction contenant les instructions selon les actions
  - Selon l'action choisie, on fait un appel ajax contenant la classe qui gère les traitements, avec une action
```js
function beforeActionOnColors(item) {
    let msg;
    let oAjax = new IsiAjax("../../Classes/IsiAjax/IsiAjax.aspx");
    oAjax.init();

    if (item) {
        switch (item.key) {
            // Action "Peupler les couleurs"
            case "actionPeuplerCouleurs":
                //Texte à afficher dans la popin
                msg = getMessagesForJavascript(false).GetMessage("actionPeuplerCouleurs").L_MESSAGE;
                uiCore.showConfirm({
                    message: msg,
                    iconType: IsiIconType.Question,
                    //Gestion des controles disponibles : Oui, Non, Annuler
                    confirmMode: IsiModeConfirm.YesNoCancel,
                    callback: function (result) {
                        //Clic sur Oui
                        if (result == IsiButtonType.Yes) {
                            //Effectuer le traitement sur tous les enregistrements
                            oAjax.SyncExecute('Traitement=IsiSyncCouleurs&action=peupler', 'POST', 'TEXT', "TEXT");
                        }
                        //Clic sur Non
                        else if (result == IsiButtonType.No) {
                            //Effectuer le traitement sur les enregistrements n'ayant pas de couleur
                            oAjax.SyncExecute('Traitement=IsiSyncCouleurs&action=completer', 'POST', 'TEXT', "TEXT");
                        } else {
                            uiCore.setSubmit(false);
                        }      
```
- Dans le fichier **menu.js** :
   - Ajouter les actions dans la fonction **beforeActionOnDetail**
  - Appeler la fonction précédemment créée
```js
if (uiCore.getSubmit()) {
        beforeActionOnColors(item);
    }
```
- Dans le fichier **IsiTreatmentManager.vb**
  - Ajouter les actions à la liste :
```vb
Case ActionPeuplerCouleurs, ActionViderCouleurs
                bAllWentOK = True
```
- Dans le fichier **IsiAjax.aspx.vb** :
  -  Appeler le constructeur de notre classe contenant les traitements, avec l'action en paramètre (dans l'exemple actuel, l'action sera "peupler", "completer" ou "vider")
```vb
Case "IsiSyncCouleurs"
       mStrategy = New IsiSyncCouleurs(Me.IsiSession, Request.Item("action"))
```
- Dans la classe effectuant les traitements (ici **IsiSyncCouleurs.vb**) :
  - Passer en paramètre du constructeur l'action
  - Effectuer le code voulu selon l'action dans la fonction **ExecuteRequest()**
```vb
Public Sub New(ByVal session As IsiSession, ByVal action As String)
        MyBase.New(session)
        _action = action
    End Sub
```
   
```vb
Public Overrides Function ExecuteRequest() As String

        Select Case _action

            Case "peupler"
                'Code à effectueur si l'action est "peupler"
            Case "completer"
                'Code à effectueur si l'action est "completer"
            Case "vider"
               'Code à effectueur si l'action est "vider"

        End Select

        Return String.Empty
    End Function
```


## Chargement de la popin
Si la popin est designable : il faut utiliser la méthode LoadMyDesign.
Renseigner la propriété IsiCurrentModalPage afin de faire marcher les connexes, prendre exemple sur la GLOB055.
De paire avec cette propriété, il faut définir la propriété ModalInputID, afin que la variable currentModalPage soit vidée à la fermeture, après l'appel de la méthode CleanSessionAfterClosePopinOverridable. Prendre exemple sur l'écran HELP016.

##  Gestion de la fermeture
Les popin disposent de deux méthodes pour fermer une popin :
- coté vb : JsClosePopin permet de fermer une popin après réalisation d'un traitement. Attention, une fois que la popin est repostée, il faut reposter aussi le formulaire parent, sinon l'appli n'est pas stable, par exemple le bouton précédent ferme l'appli.
- coté js : 
   - la méthode _**uiCore.closeCurrentPopin()**_ permet de fermer la popin courante.
   - la méthode _**closePopinWithSessionCleaning()**_ permet de fermer la popin en appelant la méthode surchargeable _**CleanSessionAfterClosePopinOverridable**_, pour réaliser des actions personnalisée sur la popin, cette fonction vide aussi l'objet currentModalPage en session, qui permet de faire fonctionner la page appelante sans repostage.
Il est possible passer des paramètres à ces trois méthodes, afin de réaliser des actions spécifiques après fermeture de la popin.

## Ouverture de la popin
Afin de pouvoir ouvrir une popin, il faut renseigner le fichier isilog.popins.js avec les lignes suivantes :
```javascript
function GLOB055() { // Nom de l'écran
    return getPopInInstance("GLOB055", // identifiant pouvant être différent du code écran pour les GLOB019, c'est cet identifiant qui doit être utilisé dans  ModalInputID
{       code: "GLOB055", // Code de l'écran
        width: 832, // largeur de la popin
        height: 230, // hauteur de la popin
    });
} 
```
Il y a deux façons d'ouvrir une popin :
   - coté VB: la méthode ShowModal
   - coté js: on peut appeler directement GLOB055().open(param)

## Retour de la popin
Il est possible définir un callback sur l'ouverture de la popin, par exemple pour lancer un repostage du formulaire appelant, ou pour relancer une autre popin après. On peut prendre comme exemple la méthode IsiRestoreRequestLine dans Isilog.popins.js
Pour les anciennes popins, les retours sont traités dans la fonction execUserModalChoice dans IsiPage.js.

# Cas de test standard des popin:
 - Test de la stabilité de l'application après fermeture de la popin (bouton précédent, enregistrement du formulaire courant)
 - Le bouton fermer doit-il bloquer l'action en cours (exemple: popin s'affichant avant l'enregistrement) 

| Mots clés |
|:-----------|
| **pop-in** - **JsClosePopin** - **closeCurrentPopin**  - **ShowModal** |