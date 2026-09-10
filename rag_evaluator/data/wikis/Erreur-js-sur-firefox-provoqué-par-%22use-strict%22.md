# Erreur levé suite à l'utilisation de la fonction 'caller', 'callee' ou 'arguments'

- `Uncaught (in promise) TypeError: 'caller', 'callee', and 'arguments' properties may not be accessed on strict mode functions or the arguments objects for calls to them` (Firefox)

# Cause

L'erreur peut être levée sur Firefox suite à l'exécution de la fonction `__dopostback` ou `isiPostBack` dans le JS. Elle est provoquée par **_MicrosoftAjaxWebForms_** qui utilise des fonctions dépréciées lorsque JavaScript est en mode strict. Le mode strict est activé par _"use strict"_ dans le code JS d'une fonction ou d'un fichier. À noter que depuis ECMAScript 6, le mode strict est activé par défaut dans les modules sans qu'il ne soit nécessaire d'écrire _"use strict"_ dans le JS et qu'il n'est pas possible de le désactiver.

https://developer.mozilla.org/fr/docs/Web/JavaScript/Reference/Strict_mode

# Solution

Cette erreur peut survenir à cause des fonctions `__dopostback` ou `isiPostBack` qui sont exécutées dans une fonction fléchée. Une solution est de l'exécuter en dehors de la fonction fléchée.

Exemple avec le fichier IsiCtrlManagement:

```js
callback: function (result) {
	if (result === IsiButtonType.Yes) {
		// <AUTHOR> <DATE> <TICKET_ID>
		bBlocAjax = 1;
		// <AUTHOR> <DATE> <TICKET_ID> : on vide ihdItemClick pour bloquer les autres traitements
		document.getElementById("ihdItemClick").value = "";
		iCState();
		isiFocusMe(oCtrlTxt);
		iSCtrlClk(sID + FIELD_SEPARATOR + 'PROP', oCtrlConnexe.fullId, null);
		// <AUTHOR> <DATE> <TICKET_ID> : correction de la sélection d'instance sur connexe.
		bPropTr(null, oCtrlConnexe.clientId + '_' + TEXTBOX, oCtrlConnexe.id, oCtrlConnexe.clientId + SEP_ENCAPS_CTRL + IMAGE_BUTTON_PROPERTY).then((result) => {
			if (result) {
				// <TICKET_ID> : connexes et onglets
				isiPostBack(oCtrlConnexe.clientId.replace(oCtrlConnexe.id, "").replace(/_/g, "$") + oCtrlConnexe.id
					+ '$' + IMAGE_BUTTON_PROPERTY, '');

			} else {
				modifWaitStatus(false, false, "");
			}
		});
	}
	// <TICKET_ID>
	uiCore.setSubmit(false);
}
```
Solution:
```js
callback: async function (result) {
	if (result === IsiButtonType.Yes) {
		// <AUTHOR> <DATE> <TICKET_ID>
		bBlocAjax = 1;
		// <AUTHOR> <DATE> <TICKET_ID> : on vide ihdItemClick pour bloquer les autres traitements
		document.getElementById("ihdItemClick").value = "";
		iCState();
		isiFocusMe(oCtrlTxt);
		iSCtrlClk(sID + FIELD_SEPARATOR + 'PROP', oCtrlConnexe.fullId, null);
		// <AUTHOR> <DATE> <TICKET_ID> : correction de la sélection d'instance sur connexe.
		const result = await bPropTr(null, oCtrlConnexe.clientId + '_' + TEXTBOX, oCtrlConnexe.id, oCtrlConnexe.clientId + SEP_ENCAPS_CTRL + IMAGE_BUTTON_PROPERTY);
			if (result) {
				// <TICKET_ID> : connexes et onglets
				isiPostBack(oCtrlConnexe.clientId.replace(oCtrlConnexe.id, "").replace(/_/g, "$") + oCtrlConnexe.id
					+ '$' + IMAGE_BUTTON_PROPERTY, '');

			} else {
				modifWaitStatus(false, false, "");
			}
	}
	// <TICKET_ID>
	uiCore.setSubmit(false);
}
```
En passant la fonction `bPropTr` en fonction asynchrone, `isiPostBack` n'est plus exécuté dans une fonction fléchée et n'est plus en mode strict.
