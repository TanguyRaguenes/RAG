[[_TOC_]]

#Les snippets, kézako ?
**Les snippets** (aka **extraits de code** en bon français) sont des **modèles** qui facilitent la saisie de modèle de **code répétitifs**, tels que des boucles ou des instructions conditionnelles.

#Ajouter un snippet dans Visual Studio
Pour **ajouter un snippet** dans Visual Studio :
1. **Créer un nouveau fichier** en local sur votre poste qu'on **appellera X.snippet** (dans mon exemple : comment.snippet).
2. Dans mon exemple je créé un snippet pour insérer rapidement le bloc de commentaire au dessus des nouvelles fonctions.

**Voici le fichier entier :**
``` xml
<?xml version="1.0" encoding="utf-8"?>
<CodeSnippets xmlns="http://schemas.microsoft.com/VisualStudio/2005/CodeSnippet">
  <CodeSnippet Format="1.0.0">
    <Header>
      <Title>comment</Title>
      <Shortcut>comment</Shortcut>
      <Description>Code snippet for add comment bloc</Description>
      <Author>${AUTHOR_ID}</Author>
    </Header>
    <Snippet>
      <Declarations>
        <Literal>
          <ID>description</ID>
          <ToolTip>Comment description</ToolTip>
          <Default>Comment description</Default>
        </Literal>
        <Literal>
          <ID>date</ID>
          <ToolTip>Comment date</ToolTip>
          <Default>01/01/2021</Default>
        </Literal>
        <Literal>
          <ID>task</ID>
          <ToolTip>Comment task</ToolTip>
          <Default>${TICKET_ID}</Default>
        </Literal>
      </Declarations>
      <Code Language="VB">
        <![CDATA[    ''' <summary>
    ''' $description$
    ''' </summary>
    ''' <returns></returns>
    ''' <history>
    '''     <entry mat="<EMPLOYEE_ID>" date="$date$" task="$task$" >Création</entry>
    ''' </history>]]>
      </Code>
    </Snippet>
  </CodeSnippet>
</CodeSnippets>
```

**Explication du fichier !**

La balise **Header** permet de documenter le snippet :
- **Title** : Permet de donner un **titre au snippet**
- **Shortcut** : Permet de définir le **code raccourci pour insérer le modèle de code**
- **Description** : Permet d'indiquer la **description du snippet**
- **Author** : Indique **l'auteur du snippet**

Dans la balise **Snippet** on va **définir le contenu du snippet**.
- **Declarations** : Permet de **définir des variables** dans le snippet
  - **Literal** : Permet de **défnir une variable**
    - **ID** : indique l'**id de la variable** dans le code snippet plus bas
    - **Tooltip** : Permet de définir un petit **commentaire sur l'utilité de la variable**
    - **Default** : Permet de mettre une **valeur par défaut** qui sera affiché lors de l'utilisation du snippet dans le code
  - **Code** : Permet de **définir le modèle de code à insérer** lors de l'utilisation du snippet. 
    - Dans cette balise on a une **propriété Language** qui permet de définir **le langage du modèle de code** dans la balise. 
(pour du **C#** &#8594; **csharp**, pour du **VB** &#8594; **VB**, pour du **C++** &#8594; **CPP**, etc)
    - Il faut **insérer le code** dans les crochets de **```<![CDATA[]]>```**
    - Pour **insérer une variable** il faut **mettre l'id de la variable entre deux "$"**
  
Une fois le fichier fini pour l'insérer dans Visual Studio il faut se dirigier sur VS : 
**Tools** &#8594; **Code Snippets Manager**

![image.png](/.attachments/image-84396bb3-fefd-4f48-a46a-157bd0c53171.png)

Sur cette fenêtre on peut **voir tous les snippets** existants dans VS en fonction de **chaque langage**.

Pour **en ajouter un nouveau** il suffit de :
- Cliquer sur **"Import..."**
- Aller **chercher le fichier** tout juste créé.
- Sur la nouvelle fenêtre il est possible de choisir **la localisation du snippet à importer**. Il est préférable de **cocher seulement "My Code Snippets"**
- Cliquer sur **"Finish"**

**Et voila le tour est joué !**

Pour voir si le snippet à bien été ajouté, il suffit sur la fenêtre **Code Snippets Manager** de **se rendre sur le langage choisi sur le snippet** et de **déplier** le dossier **My Code Snippets** et votre snippet s'y trouvera.
#Modifier un snippet
Pour **modifier un snippet existant** il suffit de modifier le fichier X.snippet. 
Pour **connaitre la localisation** de ce fichier il faut se rendre sur : **Tools** &#8594; **Code Snippets Manager**.
Sur cette fenêtre il faut aller **chercher le snippet à modifier** et lors de la selection du snippet dans le **champ Location** on voit la **localisation du fichier à modifier**.
#Supprimer un snippet
Pour **supprimer un snippet** il suffit de **supprimer le fichier du snippet**.
Pour **connaitre la localisation du fichier** voir la partie **"Modifier un snippet" plus haut**
#Utiliser un snippet
Pour **utiliser un snippet** il suffit sur le fichier voulu d'**insérer le shortcut du snippet** et de faire la **touche TAB**. 
Pour **modifier les variable** il suffit juste de **faire TAB** après l'insertion du snippet pour **parcourir entre chaque variables**.
