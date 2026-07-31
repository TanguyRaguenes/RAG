[[_TOC_]]


# Introduction
L’objectif de ce wiki est d’utiliser au mieux le Framework .NET afin d’optimiser les performances d’IWS. Cette instruction concerne tous les développements effectués sur IWS.

# Règles générales de développement
## Utilisation des fonctions du noyau IWS ou du Framework .NET
Il faut toujours vérifier qu’une fonction qui semble générique n’a pas déjà été développée pour IWS ou dans le Framework .NET.

### Exemple 
Une fonction qui travaille sur le chemin d’un fichier (pour en extraire l’extension, le nom, etc. ...) est disponible dans la bibliothèque System.IO.Path.

```VB
fileNameWithOutExtension = System.IO.Path.GetFileNameWithoutExtension(sFileName)
fileExtension = System.IO.Path.GetExtension(sFileName)
```

## Initialisation des variables de type intégré
Les variables de type intégré (Long, Integer, Short, Boolean, Double, Decimal, ...) ont toujours une valeur par défaut. Il n’est donc pas nécessaire d’initialiser explicitement ces variables avec cette valeur.

Ne pas faire :
```VB
Dim unLong as Long = 0
dim unInteger as Integer = 0
dim unBoolean as Boolean = false
dim unDecimal as Decimal = 0.0
```

Mais faire :
```VB
Dim unLong as Long 
dim unInteger as Integer 
dim unBoolean as Boolean 
dim unDecimal as Decimal
```

## Comparaison de chaines sans tenir compte de la casse
Pour comparer deux chaînes qui n’ont pas la même casse et mettre en évidence leur égalité, on utilisera la fonction String.Compare :

Ne pas faire :
```VB
Dim sVar1 As String = "CTRL_DATAFIELD"
Dim sVar2 As String = "ctrl_datafield"
' ici, on crée deux nouvelles chaines avec la méthode toUpper
If sVar1.ToUpper = sVar2.ToUpper Then
    ' ...
End If
```
Mais faire :
```VB
Dim var1 As String = "CTRL_DATAFIELD"
Dim var2 As String = "ctrl_datafield"
' ici, on utilise une comparaison ordinale qui ne tient pas compte de la casse.
If String.Equals(var1, var2, StringComparison.OrdinalIgnoreCase) Then
    ' ...
End If
```

## Initialisation de constantes
Chaque utilisation de chaines de caractères dans le code, même identique au niveau de la valeur, entraine une chaine en mémoire. Il faut privilégier les constantes, même (et surtout) pour la chaine vide **""**. Voir les classes CstString, CstSQL et CstHtml.

Il a été créé des constantes pour tous les caractères courants. Il faut toujours les utiliser et les remplacer si on en trouve lors des développements.

Ne pas faire :
```VB
' Ce code génère en mémoire 5 chaines de caractères.
Dim var1 As String
var1 = ""
While ds.IsiMoveNext
    var1 &= "." & ds.IsiStrFieldValue("CTRL_DATAFIELD") & "."
    var1 &= ","
End While
```

Mais faire :
```VB
' Ce code génère en mémoire une seule chaine de caractères.
Dim var1 As String
var1 = String.Empty
While ds.IsiMoveNext
   ' La chaine de caractères CTRL_DATAFIELD correspond à une colonne de la base de données IWS
    ' Il est possible (et recommandé) de créer une constante, ici aussi
    var1 &= CstString.CstDot & ds.IsiStrFieldValue("CTRL_DATAFIELD") & CstString.CstDot
    var1 &= CstString.CstComma
End While
```

## Concaténation de chaines
La concaténation de chaînes doit respecter les règles suivantes.

### Utilisez un **StringBuilder** 
A l’intérieur des boucles ou pour la concaténation de gros blocs de textes.
Ne pas faire :
```VB
' Oui, c'est l'exemple précédent, il peut encore être amélioré.
Dim var1 As String
var1 = String.Empty
While ds.IsiMoveNext
   ' La chaine de caractères CTRL_DATAFIELD correspond à une colonne de la base de données IWS
    ' Il est possible (et recommandé) de créer une constante, ici aussi
    var1 &= CstString.CstDot & ds.IsiStrFieldValue("CTRL_DATAFIELD") & CstString.CstDot
    var1 &= CstString.CstComma
End While
```

Mais faire :
```VB
Dim var1 As String
Dim sb As New Text.StringBuilder
While ds.IsiMoveNext   
    sb.Append(CstString.CstDot & ds.IsiStrFieldValue("CTRL_DATAFIELD") & CstString.CstDot)
    sb.Append(CstString.CstCommaAsChar)
End While

var1 = sb.ToString
``` 

NB : Le **StringBuilder** a d’autres méthodes comme **Insert** pour insérer une chaîne à une position précise (au début par exemple), **AppendFormat** pour formater des chaînes sur le même principe que String.Format, **Remove** pour supprimer un morceau de chaine, ou encore **Replace** qui effectue un remplacement dans le StringBuilder.

Pour plus de renseignement consulter .Net sur internet.
 

### Utilisez la fonction String.Format 

Pour formater des dates sous forme de chaîne :
Ne pas faire :
```VB
Dim text1 As String
text1 = "La date est " & Now.Date & "/" & Now.Month & "/" & Now.Year & " et il est " & Now.Hour & ":" & Now.Minute
```

Mais faire :
```VB
Dim text1 As String
text1 = String.Format("La date est {0:dd}/{0:MM}/{0:yyyy} et il est {0:HH}:{0:mm} ", Now)
```

Si vous souhaitez rendre plus lisible la chaine. Par exemple, pour créer du code JavaScript ou SQL, il peut être intéressant de séparer le code VB.
```VB
text1 = String.Format("var {0} = '{1}';", varName, value)
' la version courte est désormais possible (à privilégier)
text1 = $"var {varName} = '{value}';"
```
```VB
text1 = $"SELECT {monSelect}
            FROM {maTable}
           WHERE {maClauseWhere}"
``` 

NB : La fonction String.Format convertie en String les paramètres. Dans certain cas, il est nécessaire de spécifier un format, comme on l'a vu précédemment dans le cas des dates.

```VB
' cas d'une énumération (si on ne met pas le D, c'est le libellé de l'énum qui est inséré dans le texte.
text1 = String.Format("CURRENT_TYPEBASE = '{0:D};", IsiContext.IsiCn.TypeDatabase)
' cas 
```

Utilisez l’opérateur de concaténation & dans tous les autres cas :

```VB
listWhereClause & " AND " & Me.IsiOrderColumn & " >= " & iNewOrder
```

# Utilisation d’une énumération
Pour obtenir la valeur typée d’une énumération à partir d’une chaine, il faut utiliser la méthode Enum.Parse :
```VB
DirectCast([Enum].Parse(GetType(System.Data.SqlDbType), uneValeur), System.Data.SqlDbType)
 ```
Pour obtenir la valeur entière d’une énumération sous forme de chaine, il faut ajouter un paramètre :
```VB
Dim text1 As String

text1 = System.Data.SqlDbType.NVarChar.ToString
' text1 = NVarChar

text1 = System.Data.SqlDbType.NVarChar.ToString("D")
' text1 = 12
``` 

## Générer une chaîne à partir d'une liste
Pour obtenir une liste des éléments concaténés sous forme de chaîne.

Ne pas faire :
```VB
Dim text1 As String
Dim list2 As Generic.List(Of String)
'...
text1 = String.Join(CstString.CstComma, list2.ToArray)
```

Mais faire :
```VB
Dim text1 As String
Dim list2 As Generic.List(Of String)
'...
' cette surchage n'a pas toujours existée
text1 = String.Join(CstString.CstComma, list2)
```

# Utilisation de variable en session
**Attention, cette manière de faire est obsolète, il faut utiliser le IsiContext. Le paragraphe suivant n'est là que pour expliquer l'existant.**

_La création de variable de session s'effectue dans les classes IsiSession pour la partie IsiWeb et dans IsiBasicCtrl (IsiFrameworkSession) pour la partie noyau._

_On distingue 2 types de variables de session :_

- _Variable « locale » à la page nécessaire entre 2 repostages de page, avec des allers-retours, elles sont à créer dans la classe IsiInfoBetweenPage de IsiParam. Cette classe centralise toutes les variables nécessaires entre 2 pages._

- _Variable « commune » à toutes les pages (ex : IsiGlobalParam, IsiCN..), elles sont à créer dans la classe IsiFrameworkSession de IsiBasicCtrl._

_La création de variable de session « locale » doit être utilisée avec précaution, car le déchargement de ces variables est lourd à gérer. On préférera utiliser un champ caché sur la page (Hidden) qui est initialisé via le code JavaScript, puis traité lors du rechargement de la page (comme cela est fait actuellement sur les événements de la grille)._

_La libération des variables de session se fait dans les fonctions :_

_IsiSession.IsiEmptyBeforeFirstPage : Libère toutes les variables qu'il ne faut pas garder lorsqu'on revient sur la GLOB000 depuis une autre page._

_IsiSession.IsiEmptyBeforeHomePage: Libère toutes les variables qu'il ne faut pas transmettre de la HOMEPAGE vers les autres pages._

_NB : Au retour sur la page d’accueil, l’ensemble des variables dites « locales » sont réinitialisées._

# Requêtes
Pour tout savoir des bonnes pratiques dans l'écriture des requêtes SQL, cf. [Exécuter une requête dans IWS](/Accueil/Bonnes-pratiques/Exécuter-une-requête-SQL-dans-IWS).

# Utilisation de la propriété "IsiPageCtrlsMngrs"
Lorsque vous désirez récupérer ou modifier les propriétés d’un contrôle présent sur une page, il est préférable, d’utiliser la propriété « IsiPageCtrlsMngrs » plutôt que la fonction « FindControl ».

L’utilisation de cette propriété permet d’optimiser le chargement des pages et de récupérer un contrôle contenu dans un autre contrôle.

La fonction "FindControl" ne doit plus être utilisée.

# Fin de fichier
Les fichiers (*.sql, *.js, *.ts, *.vb, etc...) doivent terminer par une ligne vide.
C'est à dire que les fichiers ne doivent pas terminer par une ligne contenant du texte.

