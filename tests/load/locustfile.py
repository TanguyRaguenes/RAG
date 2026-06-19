from locust import HttpUser, task, between

import random

QUESTIONS = [
    "C'est quoi Kelio ?",
    "Comment écrire un commentaire ?",
]


class RagUser(HttpUser):
    wait_time = between(10, 60)

    @task
    def ask_question(self):
        response = self.client.post(
            "/ask_question",
            json={
                "question": random.choice(QUESTIONS),
                "provider": "api",
            },
            name="POST /ask_question",
        )

        if response.status_code != 200:
            response.failure(f"Erreur HTTP {response.status_code}: {response.text}")
