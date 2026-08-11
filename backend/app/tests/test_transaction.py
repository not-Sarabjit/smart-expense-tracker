import pytest


def register_and_login(client, email, password="TestPass123!"):
    """Helper: registers a user and returns their auth headers."""
    client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "first_name": "Test",
            "last_name": "User",
            "password": password,
        },
    )
    login = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    token = login.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def user_a_headers(client):
    return register_and_login(client, "usera@example.com")


@pytest.fixture
def user_b_headers(client):
    return register_and_login(client, "userb@example.com")


@pytest.fixture
def category_id(client, user_a_headers):
    """Creates a category for user A to attach transactions to."""
    response = client.post(
        "/api/v1/categories/create_category",
        json={"name": "Groceries", "category_type": "expense"},
        headers=user_a_headers,
    )
    return response.json()["id"]


def test_create_expense_transaction(client, user_a_headers, category_id):
    response = client.post(
        "/api/v1/transactions",
        json={
            "amount": 42.50,
            "type": "expense",
            "description": "Weekly groceries",
            "date": "2026-08-01",
            "category_id": category_id,
        },
        headers=user_a_headers,
    )
    assert response.status_code in (200, 201)
    data = response.json()
    assert data["amount"] == "42.50"
    assert data["type"] == "expense"


def test_create_income_transaction(client, user_a_headers, category_id):
    response = client.post(
        "/api/v1/transactions",
        json={
            "amount": 3000.00,
            "type": "income",
            "description": "Paycheck",
            "date": "2026-08-01",
            "category_id": category_id,
        },
        headers=user_a_headers,
    )
    assert response.status_code in (200, 201)
    assert response.json()["type"] == "income"


def test_list_transactions_only_shows_own(client, user_a_headers, user_b_headers, category_id):
    """User B should not see User A's transactions."""
    client.post(
        "/api/v1/transactions",
        json={
            "amount": 20.00,
            "type": "expense",
            "description": "A's coffee",
            "date": "2026-08-02",
            "category_id": category_id,
        },
        headers=user_a_headers,
    )

    response = client.get("/api/v1/transactions", headers=user_b_headers)
    assert response.status_code == 200
    assert response.json() == [] or all(
        tx["description"] != "A's coffee" for tx in response.json()
    )


def test_update_transaction_success(client, user_a_headers, category_id):
    create = client.post(
        "/api/v1/transactions",
        json={
            "amount": 10.00,
            "type": "expense",
            "description": "Snack",
            "date": "2026-08-03",
            "category_id": category_id,
        },
        headers=user_a_headers,
    )
    tx_id = create.json()["id"]

    response = client.put(
        f"/api/v1/transactions/{tx_id}",
        json={"amount": 15.00, "description": "Bigger snack"},
        headers=user_a_headers,
    )
    assert response.status_code == 200
    assert response.json()["amount"] == "15.00"


def test_update_another_users_transaction_fails(client, user_a_headers, user_b_headers, category_id):
    """User B must not be able to update User A's transaction."""
    create = client.post(
        "/api/v1/transactions",
        json={
            "amount": 10.00,
            "type": "expense",
            "description": "A's lunch",
            "date": "2026-08-04",
            "category_id": category_id,
        },
        headers=user_a_headers,
    )
    tx_id = create.json()["id"]

    with pytest.raises(ValueError):
        client.put(
            f"/api/v1/transactions/{tx_id}",
            json={"amount": 999.00},
            headers=user_b_headers,
        )


def test_delete_transaction_success(client, user_a_headers, category_id):
    create = client.post(
        "/api/v1/transactions",
        json={
            "amount": 5.00,
            "type": "expense",
            "description": "To delete",
            "date": "2026-08-05",
            "category_id": category_id,
        },
        headers=user_a_headers,
    )
    tx_id = create.json()["id"]

    response = client.delete(f"/api/v1/transactions/{tx_id}", headers=user_a_headers)
    assert response.status_code in (200, 204)


def test_delete_another_users_transaction_fails(client, user_a_headers, user_b_headers, category_id):
    """User B must not be able to delete User A's transaction."""
    create = client.post(
        "/api/v1/transactions",
        json={
            "amount": 5.00,
            "type": "expense",
            "description": "A's item",
            "date": "2026-08-06",
            "category_id": category_id,
        },
        headers=user_a_headers,
    )
    tx_id = create.json()["id"]

    with pytest.raises(ValueError):
        client.delete(f"/api/v1/transactions/{tx_id}", headers=user_b_headers)


def test_no_auth_token_fails(client):
    """Hitting transactions without a token should be rejected."""
    response = client.get("/api/v1/transactions")
    assert response.status_code == 401