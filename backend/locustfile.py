import random
import uuid
from datetime import date

from locust import HttpUser, between, task


class ExpenseTrackerUser(HttpUser):
    """Load test script for the Smart Expense Tracker FastAPI app."""

    host = "http://localhost:8000"
    wait_time = between(1, 3)

    def on_start(self):
        self.email = f"locust_{uuid.uuid4().hex[:8]}@example.com"
        self.password = "TestPass123!"
        self.token = None
        self.categories = []
        self._register_and_login()

    def _register_and_login(self):
        register_payload = {
            "email": self.email,
            "first_name": "Locust",
            "last_name": "Tester",
            "password": self.password,
        }

        self.client.post(
            "/api/v1/auth/register",
            json=register_payload,
            name="Auth/Register",
        )

        response = self.client.post(
            "/api/v1/auth/login",
            json={"email": self.email, "password": self.password},
            name="Auth/Login",
        )

        if response.status_code != 200:
            raise ValueError(f"Login failed for {self.email}: {response.text}")

        self.token = response.json().get("access_token")
        self.client.headers.update({"Authorization": f"Bearer {self.token}"})

        categories_response = self.client.get(
            "/api/v1/categories/",
            name="Categories/List",
        )
        if categories_response.ok:
            self.categories = categories_response.json()

    @task(3)
    def get_dashboard_summary(self):
        if not self.token:
            return

        today = date.today()
        self.client.get(
            f"/api/v1/transactions/summary?year={today.year}&month={today.month}",
            name="Transactions/Summary",
        )

    @task(3)
    def list_transactions(self):
        if not self.token:
            return

        self.client.get(
            "/api/v1/transactions",
            name="Transactions/List",
        )

    @task(2)
    def create_category(self):
        if not self.token:
            return

        category_name = f"Locust {uuid.uuid4().hex[:6]}"
        payload = {
            "name": category_name,
            "category_type": random.choice(["income", "expense"]),
        }

        response = self.client.post(
            "/api/v1/categories/create_category",
            json=payload,
            name="Categories/Create",
        )

        if response.ok:
            self.categories.append(response.json())

    @task(2)
    def create_transaction(self):
        if not self.token:
            return

        if not self.categories:
            categories_response = self.client.get(
                "/api/v1/categories/",
                name="Categories/List (fallback)",
            )
            if categories_response.ok:
                self.categories = categories_response.json()

        if not self.categories:
            return

        category = random.choice(self.categories)
        payload = {
            "amount": round(random.uniform(10.0, 500.0), 2),
            "date": str(date.today()),
            "type": random.choice(["income", "expense"]),
            "category_id": category["id"],
            "description": "Generated during Locust load test",
        }

        self.client.post(
            "/api/v1/transactions",
            json=payload,
            name="Transactions/Create",
        )
