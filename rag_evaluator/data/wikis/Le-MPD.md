[[_TOC_]]

#A quoi ça sert
permettre d'avoir une vision du modèle de données de la base de données .
c'est à dire les tables / colonnes / lien entre les tables.

on y trouve aussi aussi plusieurs schéma afin de comprendre la modélisation de certains modules.
bref une mine d'information pour ceux qui s'intéressent au schéma de la base de données de `<APPLICATION_NAME>`.


# Accès
Cela se passe dans `<INTERNAL_PORTAL>`, dans la section `<INTRANET_SECTION>` et le module `<DATA_MODEL_MODULE>`.

![image.png](/.attachments/image-9f8bdfc8-85a8-404b-8ba6-9b72e40361e1.png)

![image.png](/.attachments/image-8072ea93-6ac4-4ada-a967-14da8fe082a4.png)

#Description

Le modèle est organisé par version de `<APPLICATION_NAME>` : chaque version possède son MPD.

Vous pourrez aussi retrouver le delta des modifications de schéma d'une version au niveau d'un document présent par version. ( ce document reprend  l'historique des mise à jour en plus des  modifications de la version courante. 

![image.png](/.attachments/image-bd650de5-36f6-404f-a7af-f96e49ff4cad.png)

#Astuce 
Pour obtenir rapidement une information, comme une clé primaire ou le nom d'une contrainte, consultez directement le fichier `<DATABASE_SCHEMA_FILE>` de la version concernée, qui contient l'intégralité de la modélisation.
