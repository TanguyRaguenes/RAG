# Étapes de mise en place

## 1. Installer Docker
Installer Docker sur la machine et vérifier qu’il fonctionne correctement.

---

## 2. Créer le dossier `wikis`
Créer un dossier nommé `wikis` au même emplacement que le dossier `RAG`.

---

## 3. Cloner le dépôt contenant les wikis
Cloner le dépôt Git qui contient les wikis.

---

## 4. Copier les wikis
Copier le <u>contenu</u> du dossier IWS.wiki (que vous venez de cloner) dans le dossier `wikis` créé précédemment.

---

## 5. Lancer les conteneurs Docker
Dans une invite de commande, se placer à la racine du projet et exécuter :

```bash
docker compose up -d --build
```

---

## 6. Attendre le téléchargement des modèles
Les modèles sont téléchargés automatiquement.

Pour suivre l’avancement, exécuter :

```bash
docker logs ollama_container
```

Lorsque le téléchargement est terminé, le message suivant s’affiche :

```
Models pulled
```

---

## 7. Ingestion des wikis

### Accéder à l’embedder
Ouvrir l’URL suivante :

```
http://localhost:8002/docs
```

Puis exécuter la route :

```
POST /ingest/bulk
```

### Supprimer la collection (optionnel)
Si besoin de supprimer la collection créée :

- Accéder au retriever :
```
http://localhost:8001/docs
```

- Exécuter la route :
```
DELETE /delete_collection
```

---

## 8. Lancer l’IHM
Ouvrir l’interface utilisateur à l’adresse suivante :

```
http://localhost:8501/
```

