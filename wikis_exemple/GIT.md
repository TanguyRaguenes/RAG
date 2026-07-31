[[_TOC_]]

# Introduction
Cet article détaille la méthode pour utiliser **git** pour IWS et les commandes associées.

# Principe de **git**
## Décentralisation
Le système de **git** repose sur la décentralisation. Chaque client possède localement l'historique des sources.
A la différence de **tfvc** qui repose sur la centralisation. C'est alors le serveur **tfvc** qui stocke les modifications de tout le monde.

Dans **git**, voici les étapes principales :
- récupérer en local un dépôt stocké sur le serveur 
  - **git** télécharge les fichiers depuis `tfs.isilog.fr/tfs` vers `d:\git`
- se positionner sur la branche désirée
- faire des modifications (dev, patch, fix)
  - dans le dossier `d:\git`
- valider les modifications localement
  - dans le dossier `d:\git`
- envoyer au server les modifications
  - **git** téléverse (upload) les fichiers depuis `d:\git` vers `tfs.isilog.fr/tfs`

# Installation de **git**
Voir : [Installation de Git](/Accueil/Git/Installation-de-Git)

# La méthode

Pour chaque étape de la méthode, il est possible d'utiliser Visual Studio ou la ligne de commande. Pour débuter, le mieux est de passer par la ligne de commande afin de bien appréhender les différents aspects de **git**.

## Récupérer les sources d'un projet - Clone
Pour récupérer un dépôt localement, il faut utiliser la commande **clone**.

Pour l'exemple, nous allons utiliser le dépôt **FormationGit**.

Dans Azure devops, menu **Dépôts**, sélectionner le dépôt à cloner, cliquer sur **Cloner**

![image.png](/.attachments/image-fb49649e-016a-4516-b7c5-22527088beac.png)

Copier l'url du dépôt

![image.png](/.attachments/image-7e4789c6-f7ef-4a40-aa4a-75648fb671b7.png)

Ouvrir l'application `terminal`
Créer et aller dans le dossier `d:\git\iws`
Exécuter la commande :
```Powershell
git clone http://tfs.isilog.fr:8080/tfs/Groupe%20ISILOG/IWS/_git/FormationGit
cd .\FormationGit\
```
Le dossier FormationGit est créé et contient les sources.

### Astuces
Pour ouvrir Visual Studio Code directement positionné sur le dossier qu'on vient de clôner, il suffit de faire :
```Powershell
# On se place dans le dossier du dépôt
cd .\FormationGit\
# Ouvre Visual Studio Code
code .
```
De la même manière, si l'on veuit ouvrir l'explorateur de fichier depuis le terminal, on fait :
```Powershell
# Ouvre l'explorateur de fichier, positionné sur le dossier courant.
ii .
```

## Créer une branche pour un développement
Comme spécifié dans l'article [Branches de Git](/Accueil/Git/Branches-de-Git), on crée une branche par développeur par feature :
`users/{matricule}/{nom de la feature}`
par exemple :
`users/lbri/formation`
Dans Azure Devops, menu **Dépôts/Branches**, 

![image.png](/.attachments/image-46c08950-52b5-44cd-aae0-17647a0f0318.png)

puis **Nouvelle branche**

![image.png](/.attachments/image-75d99b6f-594d-4b90-8058-ebfdc25e65b3.png)

puis renseigner le nom de la branche (avec des / pour créer des dossiers), puis "Créer"

![image.png](/.attachments/image-557e6757-08ac-469f-a7b8-a0221b8a3e03.png)

On obtient ça :

![image.png](/.attachments/image-2460c210-17ce-42f3-b1b2-3a576a15b33c.png)

Les branches de feature par développeur permettent plusieurs choses :
- archiver régulièrement (au moins une fois par jour)
- de ne pas impacter les autres 
- de sauvegarder ses modifications sur le serveur

Il ne faut pas avoir peur d'archiver beaucoup de fois car :

  - lors de la PR (pull request - requête de tirage), tous les commits seront 
agrégés en un seul.
  - la branche d'origine sera supprimée

Ceci parce qu'on utilise le mode "squash de validation" avec suppression de la branche d'origine.

## Mettre à jour le dépôt local

### Savoir où on en est
Pour connaitre l'état d'un dépôt, on utilise la commande **status**, depuis le dossier du dépôt.

```Powershell
git status
```

![image.png](/.attachments/image-0d15f8ea-3e9e-47a2-8048-dc09feacc78c.png)

Par exemple, après avoir modifier un fichier et ajouter un autre, **git** indique la chose suivante.

![image.png](/.attachments/image-a76e3361-8d27-4cb4-a7ce-4396a09c540e.png)

### Mise à jour locale des branches
Avant de commencer nos modifications, il est nécessaire d'obtenir les éventuelles nouvelles branches remote. Ceci se fait par la commande **fetch**. Sans ça, on ne pourra pas se positionner sur notre nouvelle branche de feature.

```Powershell
# --all = tous les remotes
# --prune = suppression local des références qui n'existe plus sur le remote
git fetch --all --prune
```

On a le résultat :

![image.png](/.attachments/image-7cfe4709-aa62-4e0a-8355-82f0e8c5a71a.png)

Remarque : la commande **fetch** ne modifie pas les sources locales, elle mets uniquement à jour les informations du dépôt.

### Changer de branche localement
Avant de commencer nos modifications, il est nécessaire de vérifier sur quelle branche on est positionné et d'en changer si nécessaire.

Pour savoir sur quelle branche on est, on utilise la commande **branch**.
```Powershell
git branch
```
Dans notre exemple, on a le résultat suivant, si on a cloner le dépôt avant de créer sa branche personnelle de développement.

![image.png](/.attachments/image-24f50f26-d35a-48f4-b120-59c23df7d7d2.png)

Pour changer de branche, on utilise la commande **switch**
```Powershell
git switch users/lbri/formation
```
Et un `git branch` nous donne alors le résultat suivant :

![image.png](/.attachments/image-afacba5d-016e-4340-9f61-d788332b8a93.png)

### Mise à jour du dépôt local
Pour obtenir les nouveautés disponibles sur le serveur, mais pas encore appliquées localement, on utilise la commande pull.
Cette commande mets à jour les sources en locale.
```Powershell
# mise à jour de la branche courante, uniquement
git pull
```

La commande **pull** seule récupère les modifications de la branche courante seulement. Pour récupérer les modifications de toutes les branches, utiliser l'option **--all** (attention : ne pas confondre avec -a qui est un raccourci de --append).
```Powershell
# mise à jour de toutes les branches
git pull --all
```

## Edition locale
Le dépôt est alors prêts à recevoir nos modifications.
Lorsqu'on a terminé nos modifications, il faut indiquer à **git** ce qu'on veut archiver. Pour cela, la première étape consiste à "préparer" les modifications à archiver. C'est surtout utile lorsqu'on ne veut pas archiver toutes les modifications présentes actuellement.

Sous **tfvc**, correspond au "include/exclude" du "Pending Checking".

Par défaut, **git** ne tiens pas compte des modifications en cours. Même s'il sait qu'elles existent et qu'il connait leurs natures. Il faut indiquer à **git** ce qu'on veut prendre en compte, parmis les modifications actuelles.

Pour lui indiquer les modifications à prendre en compte, il faut utiliser la commande **add**. Il est possible d'ajouter les modifications une par une, ou bien de toutes les prendre.
```Powershell
# Ajoute dans le suivi de **git** de toutes les modifications courantes
git add .
```
```Powershell
# Ajoute spécifiquement, dans le suivi, le fichier ConsoleApp1/ConsoleApp1/Ressources/readme.txt
git add ConsoleApp1/ConsoleApp1/Ressources/readme.txt
```

Pour revenir en arrière sur un fichier, il suffit d'utiliser la commande inverse de **add**, la commande **restore**.
```Powershell
# Supprime du suivi le fichier ConsoleApp1/ConsoleApp1/Ressources/readme.txt
git restore ConsoleApp1/ConsoleApp1/Ressources/readme.txt
```

Pour l'exemple, 
- apporter des modifications dans les fichiers `Program.cs` et `Ressources/readme.txt`. 
- ajouter ces modifications dans le suivi de **git** avec la commande **add**.

Une fois ajoutées, les modifications sont visibles par la commande status
```Powershell
git status
```

Vous devez obtenir ceci :

![image.png](/.attachments/image-86ef71bb-3825-4e5e-93d3-1a185d47287e.png)

Il faut ensuite indiquer à **git** qu'on a terminé de préparer notre archivage et qu'il peut valider ces modifications. Pour cela, on utilise la commande **commit**. Par cette commande, **git** va ajouter les modifications (enregistrées par la commande **add**) dans le dépôt local.
```Powershell
# -a = --all
# -m pour le message de commit, obligatoire,
# si non fourni, git ouvre l'éditeur de texte par défaut pour permettre de saisir le message.
git commit -a -m "ajout de mon nom dans le fichier de ressource"
```

Dans l'exemple, à ce stade, la commande **status** ne doit plus rien afficher, à part le fait qu'on est en avance de 1 commit par rapport au serveur.

![image.png](/.attachments/image-cc8ce6d1-6253-47ea-bb6e-c29982def82d.png)

La dernière étape consiste à envoyer les modifications locales vers le serveur. C'est avec la commande **push**.
```Powershell
git push
```

Pour l'exemple, faire plusieurs cycles "modification locale, add puis commit" successifs.

Consulter le dépôt **FormationGit** dans Azure DevOps, en se positionnant sur "Tout" pour voir les branches de tout le monde.

![image.png](/.attachments/image-bf88286b-dde7-4e8d-b3b5-1286756a9396.png)

## Report d'une feature sur la branche parente

Lorsque le développement de la feature est terminée (après la démo à l'analyste), le moment est venu de merger la feature sur la branche de la version dans laquelle elle est prévue.

De la branche de feature à la branche parente, le merge se fait à l'aide d'une **requête de tirage** (ou **pull request** ou **PR**).

Le mode "squash" est à privilégier lors du merge d'une branche de feature vers la branche parente. Cela permet d'agréger tous les différents archivages de la branche de feature en un seul archivage sur la branche parente.

La branche de feature est supprimée au terme de la PR.

Cf. [Requête de tirage Git](/Accueil/Git/Requête-de-tirage-Git)

## Gestion des conflits
Lors de la pull request, **git** recherche d'éventuel conflit. Celle-ci ne pourra pas être validée tant que les conflits ne seront pas résolut.
Cf. [Gestion des conflits dans Git](/Accueil/Git/Gestion-des-conflits-dans-Git)

## Utilisation pour IWS
Afin de faciliter la gestion des conflits, voici les règles à suivre pour un développement IWS :
- mettre à jour régulièrement sa branche personnelle avec les évolutions de la branche parente : **pull** + **merge**
  - c'est à dire au maximum tous les 2 jours
- mettre à jour sa branche personnelle avec les évolutions de la branche parente lors de la fin du dev et avant la PR
- lancer une daily build sur sa branche personnelle après le dernier **commit** + **push**, avant la PR.

# Visual Studio
Toutes les actions présentées précédemment sont possibles dans Visual Studio. Voir pour le détail : [Git dans Visual Studio](/Accueil/Git/Git-dans-Visual-Studio).

# Résumé de l'utilisation de **git**
## Cycle d'utilisation de **git** pour le développement de la feature planning

- création d'une branche de feature (**users/lbri/planning**) à partir de **develop**
- mise à jour du dépôt local
- sélection de la branche **users/lbri/planning**
- développement
  - jour 1 du développement
  - add + commit + push
  - jour 2 du développement
  - add + commit + push
  - merge de la branche **develop** sur la branche **users/lbri/planning** + commit + push
  - dernier jour du développement
  - add + commit + push
  - merge de la branche **develop** sur la branche **users/lbri/planning** + commit + push
- exécution de la build Daily sur la branche **users/lbri/planning**
  - gestion des erreurs s'il y en a, avec s'il le faut commit + push
- pull request de la branche **users/lbri/planning** vers la branche parente **develop**
- gestion des conflits
- prise en compte des remarques de revue de code
  - éventuels nouveau commits liés aux revues de code
- la pull request est validée,
  - les modifications arrivent sur la branche parente
  - la branche users/lbri/planning est supprimée

# Remarques
- Les fichiers ne sont plus en lecture seule, comme avec **tfvc**. Ils sont tous éditables à tout moment. L'ajout et la suppression de fichiers ou dossiers sont aussi possibles à tout moment.
- Lorsqu'on renomme un fichier, ou un dossier, **git** considère qu'on supprime un fichier (dossier) et qu'on ajoute un nouveau.
- **git** fait la différence entre majuscule et minuscule
  - /users/Lbri et /users/lbri sont des branches différentes
  - un conseil : préférer les noms cours et sans majuscule, espace ou caractère exotique
- **git** ne veut pas de dossier vide
  - C'est un gestionnaire de source pas de dossier. Un dossier vide n'a aucun intérêt
- pour que **git** ignore certain fichier/dossier ou au contraire pour forcer leur prise en compte, il faut éditer le fichier **.gitignore** présent à la racine du dépôt.
- pour faire les commandes **git**, rien de mieux que l'application (Windows Terminal)[https://apps.microsoft.com/store/detail/windows-terminal/9N0DX20HK701?hl=fr-fr&gl=fr], disponible sur le store de Microsoft.
  - mais toutes les actions sont possibles par Visual Studio.
- L'extension pour Visual Studio **IsiProductivityPowerTools** doit être mise à niveau avec la dernière version, de manière à être compatible avec **git**.

