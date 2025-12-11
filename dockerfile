# 1. Image de base avec Python
FROM python:3.12-slim

# 2. Dossier de travail dans le conteneur
WORKDIR /app

# 3. Copier le contenu du projet dans le conteneur
COPY . .

# 4. Commande exécutée au démarrage du conteneur
CMD ["python", "main.py"]
