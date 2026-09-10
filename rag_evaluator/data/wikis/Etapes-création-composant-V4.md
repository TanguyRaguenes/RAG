[[_TOC_]]

# Prélude

## Objectif de cette page

En suivant les étapes décrites dans cette page, vous créez le socle d'un composant IWS V4 de A à Z : interface graphique, logique métier, handler HTTP, insertion dans un écran, etc.



## Exemples

Cette page s'appuie sur les composants :

* `IsiMarketCatalog`
* `IsiIwsElasticSearch`

Les exemples de code donnés dans ce wiki sont allégés des commentaires, des namespaces, etc. Pour avoir un exemple complet, ouvrir le code des composants ci dessus.



## Nommage et emplacement

Pour le nom des fichiers et leur emplacement, s'inspirer des exemples. Certaines méthodes et fichiers sont appelés par réflexion, il faut donc respecter une structure de projet spécifique.

Pour inspiration, voir [la documentation sur l'emplacement des fichiers dans le Framework](<INTERNAL_WIKI_URL>). La structure du projet y ressemble beaucoup.



## Contexte

Cette page a été rédigée suite à la création de `IsiIwsElasticSearch`.



## Point d'attention

Cette page décrit un composant 100% IWS. Si tout ou partie d'un composant est réutilisable, il faut le créer dans le Framework.

Exemple de composant mi-IWS / mi-Framework :

* `IsiIwsGrid` -> `IsiGrid`
* `IsiIwsAttachedFileManager` -> `IsiAttachedFileManager`

Voir le [wiki de création d'un composant Framework](<INTERNAL_WIKI_URL>).




# Etapes de création d'un composant V4 dans IWS

## Etape 1 - Créer le DTO du composant

**A quoi sert ce DTO ?**

C'est l'objet qui contiendra toute la configuration du composant.

**Comment le créer ?**

1. Créer une interface sur le modèle de `IIsiDtoIwsElasticSearch.vb`

```vb
Public Interface IIsiDtoIwsElasticSearch
    Inherits IIsiDtoComponentV4

End Interface
```

2. Créer le DTO sur le modèle de `IsiDtoIwsElasticSearch.vb`

```vb
<JsonObject(MemberSerialization.OptIn)>
<DataContract>
Public Class IsiDtoIwsElasticSearch
    Inherits IsiDtoComponentV4
    Implements IIsiDtoIwsElasticSearch

End Class
```


## Etape 2 - Créer la partie vb du composant

**A quoi sert la partie vb du composant ?**

La partie vb du composant :
* Peut décrire l'interface du composant (ce n'est pas le cas dans cet exemple, ce sera fait dans la partie typescript)
* Lie un type de DTO au composant
* Contient les méthodes permettant de faire communiquer la partie cliente (typescript) et serveur (vb) du composant
* (à compléter)

**Comment le créer ?**

1. Créer une interface sur le modèle de `IIsiIwsElasticSearch.vb`

```vb
Public Interface IIsiIwsElasticSearch
    Inherits IIsiComponent

    ' Override permettant de typer le DTO
    Overloads Property IsiDto As IIsiDtoIwsElasticSearch

End Interface
```

2. Créer le composant sur le modèle de `IsiIwsElasticSearch.vb`

```vb
Public Class IsiIwsElasticSearch(Of TContext As IIsiIsilogGuiContext)
    Inherits IsiComponentV4(Of TContext)
    Implements IIsiIwsElasticSearch

    ' Paramétrage du composant dans le constructeur
    Public Sub New()
        ' Partie obligatoire
        MyBase.New(GetType(IsiIwsElasticSearch(Of TContext)), GetType(IIsiIwsElasticSearch))
        IsiDtoType = GetType(IIsiDtoIwsElasticSearch)

        ' Partie à adapter au besoin de chaque composant
        IsiEnableJavaScript = True
        IsiEnableAJAX = True
        IsiSendDtoToClient = True
        IsiRaiseEventOnLoad = True
        AddCssClassForIdentifyComponent = True
    End Sub

    ' Override pour typer le DTO
    Public Overloads Property IsiDto As IIsiDtoIwsElasticSearch Implements IIsiIwsElasticSearch.IsiDto
        Get
            Return DirectCast(MyBase.IsiDto, IIsiDtoIwsElasticSearch)
        End Get
        Set(Value As IIsiDtoIwsElasticSearch)
            MyBase.IsiDto = Value
        End Set
    End Property

    ' Définit le nom du composant
    ' Ce nom est utilisé pour inclure automatiquement le script typescript de ce composant
    Protected Overrides ReadOnly Property ComponentName As String
        Get
            Return "ElasticSearch.IsiIwsElasticSearch"
        End Get
    End Property
End Class
```



## Etape 3 - Créer le fichier less

**A quoi sert le fichier less ?**

A définir les règles css liées au composant

**Comment le créer ?**

1. Le créer sur la modèle de `Isilog.Components.ElasticSearch.IsiIwsElasticSearch.less`
2. Importer ce nouveau fichier dans `iws.less`

```less
@import "IsiWebGUI/Isilog.Components.ElasticSearch.IsiIwsElasticSearch.less";
```



## Etape 4 - Créer les DTO du handler

**A quoi servent ces DTO ?**

Ce sont les données que la partie cliente va envoyer / recevoir du serveur lors d'un appel vers le handler ashx.

**Comment le créer ?**

1. Créer une interface 'response' sur le modèle de `IIsiDtoIwsElasticSearchResponse.vb`

```vb
Public Interface IIsiDtoIwsElasticSearchResponse
    Inherits IIsiDtoHttpHandlerResponseV4

    ' Property pour l'exemple
    Property SearchResult As String

End Interface
```

2. Créer une interface 'request' sur le modèle de `IIsiDtoIwsElasticSearchRequest.vb`

```vb
Public Interface IIsiDtoIwsElasticSearchRequest
    Inherits IIsiDtoHttpHandlerRequestV4(Of IIsiDtoIwsElasticSearchResponse)

    Overloads Property Response As IIsiDtoIwsElasticSearchResponse

End Interface
```

3. Créer le DTO 'response' sur le modèle de `IsiDtoIwsElasticSearchResponse.vb` 

```vb
<JsonObject(MemberSerialization.OptIn)>
Public Class IsiDtoIwsElasticSearchResponse
    Inherits IsiDtoHttpHandlerResponseV4
    Implements IIsiDtoIwsElasticSearchResponse

    ' Property pour l'exemple
    <DataMember(Name:="searchResult")>
    Public Property SearchResult As String Implements IIsiDtoIwsElasticSearchResponse.SearchResult

End Class
```

4. Créer le DTO 'request' sur le modèle de `IsiDtoIwsElasticSearchRequest.vb` 

```vb
<JsonObject(MemberSerialization.OptIn)>
Public Class IsiDtoIwsElasticSearchRequest
    Inherits IsiDtoHttpHandlerRequestV4(Of IIsiDtoIwsElasticSearchResponse)
    Implements IIsiDtoIwsElasticSearchRequest

    <JsonConverter(GetType(IsiNewtonSoftConcreteConverter(Of IsiDtoIwsElasticSearchResponse)))>
    <JsonProperty(PropertyName:="response")>
    Public Overloads Property Response As IIsiDtoIwsElasticSearchResponse Implements IIsiDtoIwsElasticSearchRequest.Response
        Get
            Return MyBase.Response
        End Get
        Set(Value As IIsiDtoIwsElasticSearchResponse)
            MyBase.Response = Value
        End Set
    End Property
End Class
```



## Etape 5 - Créer le handler

**A quoi sert le handler ?**

C'est la classe qui va intercepter les appels de la partie cliente du composant, pour appeler la partie serveur correspondante.

Les appels de la partie cliente sont ceux effectués à l'aide de `this.raiseOnEvent(...)` dans le `*.component.ts`

**Remarque**

VS ne supporte plus la création d'un fichier de type "General Handler". Pour créer le fichier ashx, recopier un ancien handler.

**Comment le créer ?**

1. Créer un handler sur le modèle de `IsiIwsElasticSearchHandler.ashx.vb`

```vb
Public Class IsiIwsElasticSearchHandler
    Inherits IsiIwsElasticSearchHandler(Of IIsiWebContext)

End Class

Public Class IsiIwsElasticSearchHandler(Of TContext As IIsiWebContext)
    Inherits IsiHttpHandlerWithSessionV4(Of TContext, IIsiDtoIwsElasticSearchRequest, IIsiDtoIwsElasticSearchResponse)

    Protected Sub New()
        MyBase.New()

        ' Paramètre qui lie le handler et son composant vb
        ManagedComponentType = GetType(IIsiIwsElasticSearch)

        ' Exemple
        ' ----
        ' ConfigureActionSettings va configurer la manière dont sont créés les DTO, dont sont retournés les réponses, etc.
        ' lorsque le router appelle automatiquement les méthodes liées à l'action "Search"
        ConfigureActionSettings("Search", Sub(options As IIsiDtoHttpHandlerRequest.ActionSettings)
                                              options.UseDefaultComponentV4Options()
                                              options.SendResponseData = True
                                          End Sub)
    End Sub

    ''' <summary>
    ''' Récupère le type du DTO contenant les données envoyées au serveur lors d'un appel ajax vers IsiIwsElasticSearchHandler
    ''' </summary>
    Protected Overrides ReadOnly Property HttpHandlerRequestType As Type
        Get
            Return GetType(IIsiDtoIwsElasticSearchRequest)
        End Get
    End Property

    ''' <summary>
    ''' Récupère le type du DTO contenant les données retournées par le serveur à la suite d'un appel ajax vers IsiIwsElasticSearchHandler/>
    ''' </summary>
    ''' <returns></returns>
    Protected Overrides ReadOnly Property HttpHandlerResponseType As Type
        Get
            Return GetType(IIsiDtoIwsElasticSearchResponse)
        End Get
    End Property

    ' Exemple
    Protected Sub SearchActionOnPost()
        RaiseOnEvent("Search")
    End Sub

End Class
```

2. Ajouter le handler dans le web.config du projet `IsiWeb`

```xml
<add name="IsiIwsElasticSearchHandler" verb="*" path="IsiIwsElasticSearchHandler.ashx" preCondition="integratedMode" type="Isilog.IsiComponent.IsiWebGUI.Components.ElasticSearch.HttpHandler.IsiIwsElasticSearchHandler, Isilog.IsiComponent.IsiWebGUI" />
```



## Etape 6 - Créer le BL du composant

**A quoi sert le BL ?**

Il exécute toute la logique métier / tout le code serveur du composant.

**Comment le créer ?**

1. Créer une interface sur le modèle de `IIsiBlIwsElasticSearch.vb`

```vb
Public Interface IIsiBlIwsElasticSearch
    Inherits IIsiBl

End Interface
```

2. Créer le BL sur le modèle de `IsiBlIwsElasticSearch.vb`

```vb
Public Class IsiBlIwsElasticSearch(Of TContext As IIsiIsilogContext)
    Inherits IsiBl(Of TContext)
    Implements IIsiBlIwsElasticSearch

    Public Sub New(context As TContext)
        MyBase.New(context, GetType(IIsiBlIwsElasticSearch))
    End Sub

    ''' <remarks>
    ''' Méthode appelée automatiquement par le RaiseOnEvent("Search") du IsiIwsElasticSearchHandler.
    ''' On retrouve la méthode à appeler grâce à son nom : SearchIIsiIwsElasticSearch
    ''' Partie "Search" du nom de la méthode => Nom de l'évènement levé
    ''' Partie "IIsiIwsElasticSearch" du nom de la méthode => valeur de la propriété ManagedComponentType du IsiIwsElasticSearchHandler
    ''' </remarks>
    Public Function SearchIIsiIwsElasticSearch(result As IIsiResult, request As IIsiDtoIwsElasticSearchRequest) As IIsiResult

        Dim localResult As IIsiResult = BeginTreatment(result, NameOf(SearchIIsiIwsElasticSearch))

        Try
            request.Response.SearchResult = "My result"

        Catch ex As Exception
            HandleTreatmentError(localResult, ex)
        End Try

        EndTreatment(localResult)

        Return localResult

    End Function

End Class
```

2. Lier le BL à son composant dans `IsiIws.vb` à l'aide de `IsiCreateRoute()`

```vb
Private Sub CreateFrontRoutes()
    (...)
    pArea.IsiCreateRoute(GetType(IIsiIwsElasticSearch), GetType(IIsiBlIwsElasticSearch), mpBlFactoryType)
    (...)
End Sub

Private Sub CreateBackRoutes()
    (...)
    pArea.IsiCreateRoute(GetType(IIsiIwsElasticSearch), GetType(IIsiBlIwsElasticSearch), mpBlFactoryType)
    (...)
End Sub
```



## Etape 7 - Créer un fichier `IsiTypeScript`

**A quoi sert ce fichier ?**

Pour chaque propriété contenue dans cette classe, un fichier typescript équivalent sera automatiquement généré à la compilation.

**Comment le créer ?**

1. Créer un fichier sur le modèle de `IsiIwsElasticSearch.vb`

```vb
<IsiTypeScript>
Public Class IsiIwsElasticSearch

    Property DtoIwsElasticSearch As ElasticSearch.IsiDtoIwsElasticSearch

    Property DtoIwsElasticSearchRequest As ElasticSearch.IsiDtoIwsElasticSearchRequest

    Property DtoIwsElasticSearchResponse As ElasticSearch.IsiDtoIwsElasticSearchResponse

End Class
```

2. Compiler la solution pour générer les fichiers *.ts



## Etape 8 - Créer la partie typescript du composant

**A quoi sert la partie typescript du composant ?**

La partie cliente du composant :
* Permet de décrire l'UI du composant
* Permet de réagir aux évènements utilisateurs : clics, entrées claviers, etc.

**Comment le créer ?**

1. Créer le composant sur le modèle de `IsiIwsElasticSearch.component.ts`

```ts
export class IsiIwsElasticSearch extends IsiComponentV4 {

    // =============================
    // Private fields
    // =============================

    /**
     * Le input dans lequel renseigner notre recherche Elastic
     */
    private _inputElasticSearch: JQuery;



    // =============================
    // Private const
    // =============================

    /**
     * Informations utiles pour appeler le handler du composant, côté serveur
     */
    private static readonly AppelsServeur = class {

        /**
         * Nom du handler à appeler pour réagir aux évènements ajax levés par le IsiIwsElasticSearch
         */
        public static readonly nomHandler = "IsiIwsElasticSearchHandler.ashx";

        /**
         * Les évènements qu'il est possible de lever pour appeler une méthode côté serveur
         */
        public static readonly Evenements = class {

            /**
             * Evt à lever pour lancer une recherche Elastic
             */
            public static readonly search = "Search";
        }
    }



    // =============================
    // Constructeur
    // =============================

    /**
     * Crée une nouvelle instance de la classe
     */
    constructor(element: any) {

        super(element);
    }



    // =============================
    // Public methods
    // =============================

    /**
     * Définie le handler HTTP appelé par ce composant
     */
    public _configureHttpHandlerOverridable() {

        this.set_HttpHandlerUrl(IsiIwsElasticSearch.AppelsServeur.nomHandler);
    }

    /**
     * Paramétrer ici les évènements que l'on souhaite pouvoir lever depuis ce composant
     */
    public _declareEventsOverridable() {

        this.declareAjaxEvent(IsiIwsElasticSearch.AppelsServeur.Evenements.search, "POST", null);
    }

    /**
     * Override obligatoire sans quoi le DTO ne peut pas récupérer les valeurs envoyées par la partie vb du composant
     */
    _createInstanceOfDtoOverridable(value: IsiDtoIwsElasticSearch ) {

        return IsiDtoIwsElasticSearch.fromJS(value);
    }

    /**
     * Récupère le dto qui contient la configuration du composant
     */
    public getDto(): IIsiDtoIwsElasticSearch {

        return super.getDto() as IIsiDtoIwsElasticSearch;
    }

    /**
     * Méthode appelée lors du premier chargement du composant. 
     * C'est ici que l'on créé la partie "graphique" du composant.
     */
    public onFirstLoad(sender, args) {

        super.onFirstLoad(sender, args);

        this._inputElasticSearch = jQuery('<input type="text"/>').change((evt) => { this.search() });

        this.getJQueryElement().append(this._inputElasticSearch);
    }



    // =============================
    // Private methods
    // =============================

    /**
     * Exemple d'appel au handler
     */
    private search(): void {

        const request = IsiDtoIwsElasticSearchRequest.fromJS({

            response: IsiDtoIwsElasticSearchResponse.fromJS({})
        });

        this.raiseOnEvent(
            IsiIwsElasticSearch.AppelsServeur.Evenements.search,
            {
                data: request,
                callback: (response: IsiDtoIwsElasticSearchResponse) =>
                {
                    console.log('elastic search result : ', JSON.parse(response.searchResult));
                    alert(response.searchResult);
                },
                error: (response: IsiDtoIwsElasticSearchResponse) => console.error(JSON.stringify(response))
            }
        )
    }
}
```
