Etapes de mise en place :
1° Installer docker
2° Créer un dossier wikis au même emplacement que le dossier RAG
3° Cloner le repo contenant les wikis
4° Coller les wikis dans le dossier créé précedement
5° Dans l'invite de commande taper :
    docker compose up -d --build
6° Bien attendre que les models soient téléchargés. Pour se faire dans le terminal taper
    docker logs ollama_container
    quand le traitement est terminé le message suivant s'affiche : Models pulled
7° Se rendre sur l'url de l'embedder :
    http://localhost:8002/docs
    puis exécuter la route ingest/bulk

    Si besoin de supprimer la collection ainsi créée aller sur l'url du retriever :
    http://localhost:8001/docs
    Puis exécuter la route delete_collection

8° lancer l'IHM :
    http://localhost:8501/
