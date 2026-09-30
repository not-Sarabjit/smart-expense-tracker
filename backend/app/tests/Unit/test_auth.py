# app/tests/test_auth.py


def test_register_success(client):
    """A new user can register with valid data."""
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": "alice@example.com",
            "first_name": "Alice",
            "last_name": "Smith",
            "password": "StrongPass123!",
        },
    )
    assert response.status_code in (200, 201)
    data = response.json()
    assert data["email"] == "alice@example.com"
    assert "password" not in data  # UserOut must never leak the password
    assert "hashed_password" not in data


def test_register_duplicate_email_fails(client):
    """Registering the same email twice should fail."""
    payload = {
        "email": "bob@example.com",
        "first_name": "Bob",
        "last_name": "Jones",
        "password": "AnotherPass123!",
    }
    first = client.post("/api/v1/auth/register", json=payload)
    assert first.status_code in (200, 201)

    second = client.post("/api/v1/auth/register", json=payload)
    assert second.status_code == 409
    assert second.json().get("message") == "An account with this email already exists."


def test_register_missing_fields_fails(client):
    """Missing required fields should trigger a 422 validation error."""
    response = client.post(
        "/api/v1/auth/register",
        json={"email": "no_password@example.com"},
    )
    assert response.status_code == 422


def test_login_success(client):
    """A registered user can log in and receive a JWT access token."""
    client.post(
        "/api/v1/auth/register",
        json={
            "email": "carol@example.com",
            "first_name": "Carol",
            "last_name": "Lee",
            "password": "CarolPass123!",
        },
    )

    response = client.post(
        "/api/v1/auth/login",
        json={"email": "carol@example.com", "password": "CarolPass123!"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


def test_login_wrong_password_fails(client):
    """Logging in with the wrong password should return 401."""
    client.post(
        "/api/v1/auth/register",
        json={
            "email": "dave@example.com",
            "first_name": "Dave",
            "last_name": "Kim",
            "password": "CorrectPass123!",
        },
    )

    response = client.post(
        "/api/v1/auth/login",
        json={"email": "dave@example.com", "password": "WrongPassword!"},
    )
    assert response.status_code == 401


def test_login_nonexistent_user_fails(client):
    """Logging in with an email that was never registered should return 401."""
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "ghost@example.com", "password": "whatever123"},
    )
    assert response.status_code == 401
