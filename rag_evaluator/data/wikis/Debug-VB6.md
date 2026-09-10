[[_TOC_]]

# Récupération des sources nécessaires au fonctionnement des outils client serveur

Les VM XP sont : **<LEGACY_VM_1>**, **<LEGACY_VM_2>** et **<LEGACY_VM_3>**.
La connexion à une VM XP se fait avec son identifiant `<EMPLOYEE_ID>`.

Il est possible que la machine soit éteinte, si c'est le cas utiliser Virtual Machine Manager Console pour allumer la machine.

## Gestion des sources
Comme les sources sont sous GIT et que GIT n'est pas compatible XP, il faut récupérer les sources de son poste de dev et les coller sur la VM XP. Lorsque le correctif est terminé, il faut faire l'opération inverse. Les modifications sont alors commitées sur le poste de dev, et pas depuis la VM XP.

## Sur une VM XP
Ajouter un nouveau dossier dans `D:\` nommé `D:\<PROJECT_NAME>\<EMPLOYEE_ID>\`.

Pour pouvoir débugger les outils en VB6 il faut récupérer les sources suivante pour que tout fonctionne. Le reste des sources n'est pas utile.

Il faut récupérer les dossiers suivants :
- `<CLIENT_SERVER_SOURCES>`
- `<COMPONENT_SOURCES>`
- `<SERVER_SOURCES>`
- `<MASTER_SOURCES>`
- `<INTERNAL_TOOLS_SOURCES>`
- `<SHARED_FILES_SOURCES>`
- `Web\<COMPONENT_PATH>\<ENCRYPTION_LIBRARY>`
- Interop

Créer ensuite le dossier `Interop` comme indiqué dans la section [Dossier interop](#interop)

# Modification du code

Pour modifier le code, utiliser l'IDE *Microsoft Visual Basic*.

Regardez comme c'est beau :

![image.png](/.attachments/image-911fc38c-fb87-451e-bc56-42c41cfff2be.png)

# Mise en place du debug / A faire avant compilation
Il faut maintenant lancer l’outil interne `<INTERNAL_TOOL>.exe` (même si l'objectif est de coder sur un autre projet), présent dans `./<INTERNAL_TOOLS_SOURCES>/<INTERNAL_TOOL>`.
Aller dans l’onglet installation, cliquer sur "Install Rebuild...". 
Fermer toutes les interfaces de développement VB6 car elle empêche le fonctionnement de l'Install Rebuild.

![gestion interne install rebuild.JPG](/.attachments/gestion%20interne%20install%20rebuild-32caab18-e698-4126-af1f-f4f806cf705f.JPG)

Sur l’écran qui s’ouvre, dans le cadre option, dans le menu déroulant Sélection, choisir C/S (pour client serveur) et cliquer sur lancer (aucun visual studio vb6 ne doit être ouvert pendant cette étape). 

![install rebuild.JPG](/.attachments/install%20rebuild-f4b3fb3d-fbf0-46e5-82c5-91fdb313a4c5.JPG)

Si l’install rebuild se termine en erreur, c’est surement parce qu’il manque des dll qu’il faudra get avant de réessayer.

Si à cette étape tout c’est bien passé, le debug est enfin prêt. Il ne reste plus qu’à aller sur le programme à debugger et de le lancer avec F5 (permet de recompiler en mode debug).

#Raccourcis
F5 = Lancer le programme en mode debug.
Curseur de la définition de la fonction + Shift + F2 =  Aller à la définition de la fonction.
F8 = Rentrer dans la fonction ou démarrer le programme directement en pas à pas.
Shift + F8 = Pas à pas.
Tools -> Options -> General  = Breaker sur toutes les erreurs.

# Génération de l'exe

Depuis Microsoft Visual Basic (en ayant ouvert le projet souhaité `D:\<PROJECT_NAME>\<EMPLOYEE_ID>\`), on génère l'exe depuis `File > Make xxx.exe...`.

![image.png](/.attachments/image-30bf30d9-0bec-44a9-93e6-1a03842cee64.png)

# Tester un exe

Si vous souhaitez ensuite tester, par exemple, `<INTERNAL_APPLICATION>`, il vous suffit de copier l’exécutable généré dans vos sources.

Attention : dans ce cas, l'application est liée à un setup. Il est donc conseillé de créer une copie sur laquelle vous effectuerez vos tests.

De la même manière, si vous avez modifié des scripts, il faut les inclure dans le dossier compressé de votre version (par exemple : `<INTERNAL_APPLICATION>\<VERSION>\scriptsSQL`).

# Tips

- Si vb6 plante au moment d’entrer dans un break point dans isiscan, la solution est de désactiver les menus.
Pour cela il faut refaire la cinématique et s’arrêter juste avant le break point puis faire Ctrl + F12 pour désactiver tous les menus (et Ctrl + F11 pour les réactiver).
Après ça VB6 ne devrais pas planter au moment d’entrer dans le break point.
- Si vous utilisez un fichier externe il faut redémarrer visual basic pour que ce soit pris en compte, par exemple si on souhaite inclure un cls présent  dans ShardeFile cliquer sur Ajouter > Un nouveau module de classe > existing et ajouter le cls puis fermer en sauvegardant le projet et réouvrir visual basic.
- Les watchs sont limitées en taille, pour voir le contenu en entier faire View > Immediate Window et écrire
 `?<votreVariable> ` puis entrer => le contenu de la variable s'affiche.
- Appuyez sur Ctrl + `Pause` pour mettre en pause un traitement.

# Utilisation de l'ancien mode Isinterface

Pour optimiser l'utilisation d'Isinterface dans XDEV, il est recommandé de passer en mode ancien moteur. Ce choix présente plusieurs avantages, notamment le fait de ne plus avoir besoin de faire communiquer Isinterface avec IIS (Internet Information Services). En utilisant ce mode, Isinterface pourra fonctionner correctement sans dépendre de IIS.

Pour activer cette option, il suffit d'aller dans les réglages d'administration dans IWS et de cocher `Utilisation de l'ancien moteur Isinterface` dans le menu `Administration -> Référentiel -> Options`.

IsiInterface doit également pouvoir communiquer avec IIM (IsiInstallerManager). Pour cela, exécutez la commande suivante dans le CMD de votre machine directement dans le répertoire d'installation de `IIM.exe`, en modifiant les arguments avec votre propre configuration :

``` bash
.\IIM.exe DATAIMPORT CN="<DATABASE_CONNECTION>" log="D:\logs\iim.log" TRACELEVEL=1 HTTP=<INTERNAL_PORT> HOST=<INTERNAL_HOST> USER=<USER_ID>
```

# Copier des fichiers vers les VM XP

## Méthode 1 - Dossier Interop <a id="interop"></a>

Depuis la suppression des anciens lecteurs réseau, les machines XP n'ont plus accès aux fichiers partagés. Pour des raisons de sécurité, elles n'auront pas accès aux nouveaux partages (`<INTERNAL_SHARE_1>` ou `<INTERNAL_SHARE_2>`).

Il est nécessaire de copier les fichiers à la main. Donc, en cas d'erreur, lorsque vous suivez ce wiki, il vous faudra copier les fichiers vous même. Comme ceci :

Créer un dossier `Interop` à la racine du dépôt et copier toute l'arborescence se trouvant sur le réseau, depuis :

`<INTERNAL_SHARE>\Build\Assets\CS\<VERSION>\CS`

## Méthode 2 - FTP

Pour accéder à un dossier partagé vers une VM XP ou depuis une VM XP, il faut utiliser le protocole SMB.
Ce protocole est très vulnérable et nous ne voulons pas l'activer sur les postes récents (vm de dev ou pc physique).

Nous avons donc activé le FTP sur les VM XP.
En utilisant un client FTP (ex : WinSCP), vous pouvez vous connecter sur `ftp://<INTERNAL_HOST>` avec votre identifiant `<EMPLOYEE_ID>` et votre mot de passe.
Les fichiers que vous déposerez seront dans c:\inetpub\ftproot.

⚠ **Ne pas utiliser FileZilla car il applique une couche de sécurité particulière qui bloque l'accès aux machines XP**

La modification est appliquée sur l'ensemble des VM XP concernées.

## Méthode 3 - VM
Cette méthode n'est possible que si vous avez une VM à votre nom.
Pour accéder à vos fichiers de votre VM, il suffit de de taper dans la bar adresse de l'explorateur de fichier de la VM-XP:
-  `\\\\<PERSONAL_VM>\d$`
