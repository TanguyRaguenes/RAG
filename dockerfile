# 1. Image de base avec Python
FROM python:3.12-slim

# 2. Dossier de travail dans le conteneur
WORKDIR /app

# 3. Installer uv dans l'image
RUN pip install --no-cache-dir uv

# 4. Copier les fichiers de config du projet (sans le code pour l'instant)
COPY pyproject.toml uv.lock* ./

# 5. Installer les dépendances du projet dans l'image (FastAPI, etc.)
RUN uv sync --no-dev

# 6. Copier le reste du code dans l'image
COPY . .

# 7. Commande exécutée au démarrage du conteneur
CMD ["sh", "-lc", "\
  if [ \"$DEBUG\" = \"1\" ]; then \
    exec uv run python -Xfrozen_modules=off -m debugpy \
      --listen 0.0.0.0:5678 \
      -m uvicorn app.main:app --host 0.0.0.0 --port 8000; \
  else \
    exec uv run uvicorn app.main:app --host 0.0.0.0 --port 8000; \
  fi \
"]
