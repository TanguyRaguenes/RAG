[[_TOC_]]

Téléchargement de BURP :
https://portswigger.net/burp/releases/professional-community-2022-8-4?requestededition=community&requestedplatform=

:warning: télécharger la version Community, les autres versions sont payantes.

#Présentation
BURP est une application qui permet d'effectuer des tests de pénétration sur les applications web

#Lancer un projet
Au lancement de BURP vous arriverez sur la page suivant :
![image.png](/.attachments/image-f2808f2c-3eae-4cf5-9a07-82467c58609e.png)

Vous n'aurez pas le choix de sélectionner ***Temporary project*** avec la version community, vous pouvez donc directement passez à l'étape suivante

puis faire Start BURP
![image.png](/.attachments/image-19237413-3c37-4df5-90ae-3efcab2f4be8.png)

Une fois le projet lancé se rendre dans l'onglet **Proxy** et ouvrir un navigateur via le bouton **Open browser**
![image.png](/.attachments/image-e3e2b88c-1182-4447-87c3-3e5eebabce2f.png)

BURP snif uniquement les url qui passe par sont "navigateur"

Pour voir les url sniffé par BURP, il faut se rendre dans le sous-onglet **HTTP history**
![image.png](/.attachments/image-931db06e-e43b-4889-b004-20672134a5f9.png)

En sélectionnant une des url vous pourrez voir le détail des infos envoyés au serveur et reçu par le client comme avec Fiddler

![image.png](/.attachments/image-f90e71cf-99f2-401c-b51c-77df009393e4.png)

A l'aide d'un click droit sur une des url vous pourrez la rejouer dans l'onglet **Repeater** pour cela faire **Send to Repeater**
![image.png](/.attachments/image-bc77e94f-04ad-4cd9-9bf9-e6081883c6d0.png)

Une fois dans l'onglet **Repeater** vous récupèrerez votre requête HTTP avec tout les cookies correspondant ce qui vous permettra d'attaquer votre site en y modifiant l'url
![image.png](/.attachments/image-753b1d57-9159-4be8-9269-4a365df5ef07.png) 

Sur la partie droite de l'onglet vous verrez le résultat d'exécution de votre requête rejoué
![image.png](/.attachments/image-b1abf927-2ff5-4263-817f-9e3e9c388fc7.png)


> Si vous prenez le temps de découvrir le reste des fonctionnalités n'hésité pas à les ajouter a ce wiki cela ne peut que servir à d'autre
