[[_TOC_]]

La version IWS Nautilus est développée avec Visual Studio 2022, il est nécessaire de l'installer pour développer sur cette version (FW et IWS).

#Télécharger Visual Studio 2022

Pour télécharger Visual Studio 2022, cliquez [ici](https://visualstudio.microsoft.com/fr/vs/) puis sélectionnez la version "Enterprise 2022. Un exécutable va se télécharger et il faudra l’exécuter.

#Installation de Visual Studio 2022

L'utilitaire Visual Studio Installer se lance et demande les modules à installer, il faut sélectionner :
- Développement web et ASP.NET
- Développement .NET Desktop
- Développement d'extension Visual Studio

![image.png](/.attachments/image-286d4a59-b00c-40b7-807d-a31e9f240128.png)
![image.png](/.attachments/image-86b1a019-38f6-47e9-95af-2261329d34ec.png)

Pour ceux qui préfèrent la langue de Shakespeare il faut penser à la sélectionner dans la rubrique "Module linguistiques"

![image.png](/.attachments/image-808422da-8bd7-4e8e-b355-e644fd351a94.png)

On peut ensuit lancer l'installation, pour que cela soit plus rapide laisser le bouton sur l'option ci-dessous.
![image.png](/.attachments/image-50481bc8-1eae-4df7-960f-b7d010ce44d6.png)


#Connexion à Visual Studio 2022

Au premier lancement, Visual Studio demande un compte avec une licence valide. Il faut se connecter avec son compte `<ORGANIZATION_ACCOUNT>` ; si aucune licence valide n'est trouvée, contacter l'équipe responsable des licences. Une fois la licence assignée, cliquer sur "Check for an updated license".

# Connexion à Azure DevOps
Pour configurer la connexion à Azure DevOps, suivre cette procédure : [Connexion à Azure DevOps](<INTERNAL_WIKI_URL>).

#Installation de IsiProductivityPowerTools

Suivre la procédure ici : [IsiProductivityPowerTools](<INTERNAL_WIKI_URL>).

# En cas de manque de place sur C: uniquement
Il est peut-être nécessaire de suivre le wiki : [Manque de place sur le disque C:](<INTERNAL_WIKI_URL>).

# Configuration de Gulp

L'intégration dans Visual Studio est gérée par l'extension "NPM Task Runner" installable facilement via le manager d'extension de Visual Studio. Cf. [Configuration de Gulp et Node.js](<INTERNAL_WIKI_URL>).

#Configuration de TypeScript
Pour configurer TypeScript, suivre ce [wiki](<INTERNAL_WIKI_URL>) puis redémarrer Visual Studio, accéder aux propriétés d'un projet Web, onglet "TypeScript Build", sélectionner la version installée, enregistrer et régénérer la solution.

