import os
import random
from pathlib import Path

import httpx
from dotenv import load_dotenv
from locust import HttpUser, between, task

load_dotenv(Path(__file__).with_name(".env"))

QUESTIONS = [
    "C'est quoi Kelio ?",
    "Comment écrire un commentaire ?",
]

OIDC_TOKEN_URL = "http://localhost:1411/api/oidc/token"
OIDC_RESOURCE = "http://localhost:8003"
OIDC_SCOPE = "rag:ask"


class RagUser(HttpUser):
    wait_time = between(10, 60)

    def on_start(self):
        client_id = os.environ["LOCUST_OIDC_CLIENT_ID"]
        client_secret = os.environ["LOCUST_OIDC_CLIENT_SECRET"]

        response = httpx.post(
            OIDC_TOKEN_URL,
            data={
                "grant_type": "client_credentials",
                "client_id": client_id,
                "client_secret": client_secret,
                "resource": OIDC_RESOURCE,
                "scope": OIDC_SCOPE,
            },
            timeout=10,
        )
        response.raise_for_status()

        access_token = response.json().get("access_token")
        if not isinstance(access_token, str) or not access_token:
            raise RuntimeError("Pocket ID n'a pas retourné d'access token valide")

        self.client.headers.update({"Authorization": f"Bearer {access_token}"})

    @task
    def ask_question(self):
        with self.client.post(
            "/ask_question",
            json={
                "question": random.choice(QUESTIONS),
                "provider": "api",
            },
            name="POST /ask_question",
            catch_response=True,
        ) as response:
            if response.status_code != 200:
                response.failure(
                    f"Erreur HTTP {response.status_code}: {response.text}"
                )
