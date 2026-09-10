
Le but de cet article est de décrire et fournir un script permettant de transformer des données CSV en un fichier LDIF exploitable par LDAP.

**Fichier LDIF et attributs LDAP**
(à voir)
Une entrée LDAP est caractérisé par ses attributs. Les attributs qu’une entrée peut prendre dépendent des classes données à l’entrée par l’attribut « objectclass ».
Un fichier LDIF est un fichier texte contenant des requêtes d’ajout ou de changement de données interprétable par LDAP.

**Méthode et formatage**
Le script [csv2ldif.py](/.attachments/csv2ldap%20-d7996020-9458-4c91-bf4c-1a5b75f3cfde.txt) nécessite Python 3 d’être installé. Il contient une méthode csv2ldif(String **nomFichierCSV**, String **dn**) qui crée un fichier LDIF à partir de données CSV. La méthode prend 2 arguments sous forme de chaîne de caractères :

--**nomFichierCSV** est le nom du fichier dans lequel se trouvent les données au format CSV à exploiter.
Voici sous Excel la forme que doivent prendre ces données :
 
![Données sous forme CSV.png](/.attachments/Données%20sous%20forme%20CSV-074b62b4-9dcb-4482-898d-300cce59d5e7.png)
_Fig. 1 : Représentation Excel de données à importer au format CSV_

Chaque ligne représente une entrée à insérer, et chaque colonne un attribut de l’entrée.
Pour que le script fonctionne, il faut que :
- La première ligne comporte le nom correct des attributs LDAP
- La première colonne soit le « Common Name » (cn) de l’entrée, qui permet d’identifier chacune de manière unique.

--**dn** est le chemin du répertoire où seront créées les entrées dans l’arborescence LDAP. Il prendra typiquement la forme suivante :
« OU=<ORGANIZATIONAL_UNIT>,OU=Users,DC=<INTERNAL_DOMAIN>,DC=<TLD> »
… où « OU=Jakarta » est le nom du répertoire final où se trouveront les entrées.

**Utilisation**
Pour lancer le script, ouvrir la console Idle (téléchargé automatiquement avec Python 3), puis ouvrir depuis Idle le script csv2ldif.py et exécuter le module (F5). Appeler la fonction csv2ldif( ) avec les deux arguments passés en chaîne de caractères.

NB : le caractère reconnu comme délimiteur peut être modifié dans la variable « delimiter » du script. C’est un point-virgule de base ; à modifier en fonction du fichier CSV utilisé.

Une fois la méthode lancée, un fichier nommé ldapdata.ldif sera créé dans le même répertoire que le script. Ci-dessous le résultat généré par le tableau Fig. 1 :
 
![FichierLDIF.PNG](/.attachments/FichierLDIF-7775a88c-c7ba-4642-ab97-a24730361cfa.PNG)
_Fig. 2 : Données créées au format LDIF_

**Ressources**

[Script disponible ici](/.attachments/csv2ldap%20-d7996020-9458-4c91-bf4c-1a5b75f3cfde.txt)

[Télécharger Python](https://www.python.org/downloads/)

Limites actuelles :
-	On ne peut pas importer les données d’un même fichier dans des répertoires différents.
-	Le script est arbitrairement en Python.
