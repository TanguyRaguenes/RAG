[[_TOC_]]

#Objectif
L’objectif de cette instruction est de définir les bonnes pratiques à appliquer lors du développement d'une application web .NET pour empêcher toute faille de sécurité permettant l'injection de code navigateur ou serveur.

#Domaine d'application
Cette instruction concerne le développement d'applications web Microsoft .NET.

#Définitions
- ##Donnée en provenance de l'utilisateur :
  Désigne toute donnée fournie par l'utilisateur (ou son navigateur) à l'application Web. 

  Cela comprend notamment :
  - URL et paramètres d'URL (méthode GET)
  - Champs de formulaires Web cachés ou non (méthode POST)
  - Cookies
  - Headers HTTP


- ##Donnée ou traitement non sensible :
  Par donnée ou traitement non sensible, on entend toute donnée ou traitement dont l'atteinte à l'intégrité ou à la confidentialité ne peut en aucun cas avoir de conséquence sécuritaire. Dans le cas de données échangées depuis le client vers le serveur, ce cas est rarissime, car si ces données subissent un traitement côté serveur par du code applicatif, alors des conséquences sécuritaires peuvent exister. 
Exemples de données / traitements non sensibles :
Un traitement de type JavaScript réalisé côté client qui gère la couleur des pages, le style des polices de caractère, ou bien encore la définition de menus déroulants – une atteinte à ce traitement ne peut en aucun cas avoir de conséquence sécuritaire

- ##Donnée ou traitement sensible :
  Par donnée ou traitement sensible, on entend toute donnée ou traitement dont l'atteinte à l'intégrité ou à la confidentialité peut avoir dans certains cas une ou plusieurs conséquences sécuritaires. 
Remarquons que dans le cas général, la plupart des données échangées entre le client et le serveur sont des données sensibles.

- ##Fiabilité des données et des traitements
  - ###Fiabilité des traitements
    Les traitements réalisés chez l'utilisateur ne sont pas fiables. En effet, rien ne permet de garantir les traitements réalisés sur un poste non maîtrisé.

     Seuls des traitements non sensibles peuvent être réalisés chez l'utilisateur.
On pourra faire de l'aide à la saisie, des traitements esthétiques d'amélioration de l'affichage ou de la navigation, bref tout type de traitement qui n'a strictement aucune implication sécuritaire. Attention cependant à bien s'assurer que ces traitements sont réellement non sensibles.

    Tout traitement sensible doit être réalisé sur le serveur et pas chez l’utilisateur
En effet, non seulement on n'a aucune garantie qu'ils seront effectués correctement chez l’utilisateur, mais en plus les traitements sensibles (potentiellement confidentiels) pourront être analysés par un utilisateur malintentionné.

  - ###Fiabilité des données
    Les données en provenance du navigateur du client ne sont pas fiables. Là aussi, rien ne permet de garantir les données à partir d'un poste non maîtrisé.

  - ###Limitation des échanges de données sensibles au strict nécessaire
    Il faut limiter au strict minimum nécessaire les données sensibles renvoyées par le client. La question qu'il faut se poser par rapport à chaque donnée renvoyée par le client est donc la suivante : a-t-on déjà par ailleurs cette donnée dans notre périmètre ?
En effet, des données connues à l'avance par l'application Web n'ont pas à être échangées côté utilisateur, mais doivent être traitées uniquement côté serveur, sans passer par le client.

    On peut en déduire plusieurs règles pour les données sensibles ni signées ni chiffrées :
    - Les champs de type HIDDEN sont à bannir. 
En effet, ils traduisent un aller-retour de données entre le serveur et le client, sans aucun besoin de saisie par le client.
Exception : le cas particulier de l’ID d’état du curseur, qui permet d’identifier un état unique présenté au client et donc d’assurer la cohérence navigation/session.

    - De la même manière, les cookies sont également à bannir.
Exception : le cas particulier de l'ID de session, qui transite par cookie.

    - Enfin, les données sensibles ne doivent pas non plus transiter dans les URL ou leurs paramètres (méthode GET) pour les mêmes raisons, car les URL sont stockées dans de nombreux endroits (historique navigateur, logs de proxy, logs du serveur, etc.).

    De manière générale, les données sensibles doivent transiter via la méthode POST.

    Exceptions :
        - le cookie ID de session
        - l’ID d’état dans un champ HIDDEN (s’il est nécessaire)
        - les paramètres de navigation indiqués dans l’URL (méthode GET)

  - ###Traitements de sécurité sur les données renvoyées par l'utilisateur
    Les vulnérabilités associées à de mauvais contrôles sur les données renvoyées par l'utilisateur sont de quatre types :
    - Injection de code serveur (SQL injection, LDAP injection, injection de code, buffer overflow, etc.)
    - Modification de données métiers (on pourrait l'appeler CICS injection)
    - Injection de code navigateur (HTML injection = XSS ou Cross Site Scripting)
    - Déni de service

    Pour parer à ces différentes vulnérabilités, nous appliquerons un filtrage technique – qui permet de n'autoriser que des données "saines" d'un point de vue technique. Ce filtrage doit s’appliquer sur les données en entrée de l’application, mais également en sortie (pour pallier les vulnérabilités de type XSS) et doit autant que possible s’appuyer sur le principe de liste blanche.

    Microsoft fournit une bibliothèque (http://wpl.codeplex.com/) qui fournit des méthodes permettant de gérer les failles de type XSS (Cross Site Scripting) et empêcher l'injection de code navigateur(JavaScript, HTML, CSS) et serveur  (LDAP,SQL, VB.NET).

- ##Méthodologie de sécurisation
  Il existe globalement trois techniques de filtrage :

    1: n'accepter que des données techniquement saines
Cette méthode est évidemment la meilleure et la plus efficace, car elle ne dépend pas d'une connaissance variable dans le temps (la définition d'une donnée malsaine). Les deux autres sont citées pour information. Toute utilisation d'une méthode différente de la première devra être validée explicitement (sous forme d'une dérogation).
Il n'est cependant pas possible de n'accepter que les données techniquement saines car cela impliquerait de refuser beaucoup de caractère (<,>,&,%,....)

  2: Refuser les données connues comme étant malsaines
Cette méthode est déconseillée car la liste des données malsaines ne peut être connue.

  3: Transformer les données connues comme étant malsaines en données techniquement
Pour IWS, nous utiliserons cette méthode de filtrage qui consiste à échapper les données saisies avant de les utiliser dans nos traitements.

  - ###Protection contre l'injection de code serveur 
    La protection contre ce risque de vulnérabilité est assurée par un filtrage dit "technique" en entrée de l'application (saisie des données).
Ce filtrage doit garantir la non possibilité d'effectuer des requêtes serveur ou d'exécuter du code applicatif en détournant l'utilisation de l'application.

    Type de faille : SQL injection, LDAP injection, injection de code, buffer overflow, etc.

   - ###Injection de code SQL
     Afin d'éviter que du code SQL puisse être exécutée de manière détournée, toute saisie d'un utilisateur doit être échappée avant d'être utilisée au sein d'une requête SQL.

     Il est donc obligatoire d'utiliser la fonction Isilog REQUETE.IsiBuildSql pour construire les requêtes SQL. Cette dernière garantie l'échappement de tous les paramètres passées à la requête.

     De la même manière, il est interdit de passer des clauses SQL dans les paramètres d'une URL.
Pour passer des paramètres de restriction SQL à un écran, il faut utiliser les propriétés Isilog suivantes:
     - IsiSession.IsiInfoBetweenPages.IsiWhere
     - IsiSession.IsiInfoBetweenPages.IsiWhereAjax

  - ###Injection de code LDAP
    Comme pour le code SQL, les chaines de caractères saisies par l'utilisateur doivent être échappées avant d'être utilisées dans les requêtes LDAP.
Pour sécuriser une chaine saisi par l'utilisateur, il faut alors utiliser la fonction .NET
Microsoft.Security.Application.Encoder.LdapFilterEncode

- ## Protection contre l'injection de code navigateur
   La protection contre ce risque de vulnérabilité est assurée par un filtrage dit "technique" en sortie de l'application (restitution des données saisies).
Une faille XSS peut être provoqué par l'interprétation de code HTML,JavaScript,CSS,VB,... issu du contenu de la base de donnée.

   Type de faille : HTML injection = XSS ou Cross Site Scripting

   - ###Injection de code JavaScript
     Une donnée saisie par l'utilisateur ou issue de la base doit être échappée avant d'être utilisée dans du code JavaScript.
Pour sécuriser une chaine saisi par l'utilisateur, il faut alors utiliser la fonction .NET
Microsoft.Security.Application.Encoder.JavaScriptEncode

  - ###Injection de code HTML
    Une donnée saisie par l'utilisateur ou issue de la base doit être échappée avant d'être utilisée dans du code HTML.
Pour sécuriser une chaine saisi par l'utilisateur, il faut alors utiliser la fonction .NET
Microsoft.Security.Application.Encoder.HtmlEncode











