# Introduction
Le code doit être commenté, mais il doit être bien commenté.

En effet, les commentaires doivent aider à comprendre le code, pas à le décrire. Les commentaires doivent être en accord avec le code. C'est à dire que lors de la maintenance du code, le commentaire doit lui aussi être mis à jour. Le risque d'avoir des commentaires qui décrivent le code est que les commentaires ne correspondent plus au code, car il n'est pas mis à jour.

Ce qui implique aussi que le code doit être simple afin qu'il soit simple à lire et a comprendre sans commentaire. Il faut se dire que si du code nécessite trop de commentaire c'est qu'il n'est pas assez simple. Il vaut mieux prendre la voie de la simplification du code que la voie du commentaire.

De plus, c'est le code qui est exécuté et donc qui fait fois. Quand on découvre une fonction, il faut en lire le code en premier et ensuite lire les commentaires pour les cas particuliers ou les subtilités.

# Référence
https://www.red-gate.com/simple-talk/opinion/opinion-pieces/fighting-evil-code-comments-comments/

 # Exemples
Voici un exemple pris dans IWS qui montre des commentaires inutiles (après ça fait de la couleur, c'est vrai). Tous les commentaires inutiles sont avec une * (en fait tous ;))

```VB
  Protected Overrides Function CheckTreatmentContextAvailabilityOverridable(ByVal list As Generic.List(Of IIsiMenuEntry)) As Generic.List(Of IIsiMenuEntry)
	Dim codeTraitement As String                       ' Code du traitement en cours de validation  *
	Dim newList As Generic.List(Of IIsiMenuEntry)       ' Liste copiée pour suppression             *
	Dim index As Generic.IEnumerator(Of IIsiMenuEntry)        ' Enumérateur de la liste             *
	Dim entry As IIsiMenuEntry                          ' Traitement en cours de validation         *
	Dim parseEnd As Boolean                            ' Indique que le parcours est fini           *
	Dim ctrl As IsiCtrlData

	If sPageName = "ADM012" Then
		ctrl = DirectCast(pCurrentPage, IIsiPage).IsiPageCtrlsMngrs.IsiAllCtrls.IsiGetIsiCtrlData("itxtC_PROFIL")
	End If
	' ------------------------------------------------
	' Restriction des traitements proposés   *

	' Nous copions la liste fournie puis nous la parcourons. A chaque entrée  *
	' trouvée correspondante à un traitement à limiter, nous vérifions les    *
	' droits et supprimons l'entrée dans la liste copiée le cas échéant.      *
	' Une fois la liste parcourue, nous la recopions dans la liste fournie.   *

	' Copie de la liste initiale             *
	newList = New Generic.List(Of IIsiMenuEntry)(list)

	' Initialisation du parcours             *
	index = list.GetEnumerator
	index.Reset()
	parseEnd = Not index.MoveNext()

	' Pour chaque traitement de la liste    *
	While Not parseEnd

		' Capture du traitement         *
		entry = index.Current

		' Capture du code du traitement *
		codeTraitement = entry.Code

		' Suivant le traitement         *
		Select Case codeTraitement
			Case IsiTreatmentManager.actionToutAutoriser
				' S'il s'agit d'une génération de procédure * bravo le copier/coller !
				If ctrl.IsiValue = "SU" Then
					newList.Remove(entry)
				End If
			Case IsiTreatmentManager.actionToutInterdire
				If ctrl.IsiValue = "SU" Then
					newList.Remove(entry)
				End If
			Case IsiTreatmentManager.actionRetablirDroitProfil
				If ctrl.IsiValue = "SU" Then
					newList.Remove(entry)
				End If

		End Select

		' Passage au traitement suivant *
		parseEnd = Not index.MoveNext

	End While

	Return newList
End Function
```
