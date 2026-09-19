"""
Phase 1 -- authentication tests (djoser + simplejwt).

Run just this file with:

    pytest tests/test_auth.py -v

What this file is protecting:

* Registration really creates a User, and never leaks or stores a plaintext
  password.
* Login issues a usable access + refresh token, and rejects bad credentials.
* Protected endpoints 401 without a valid token.
* The JWT *configuration* in settings.py actually does what it claims
  (refresh rotation + blacklisting), because those two settings silently do
  nothing if the token_blacklist app is missing.
"""

from django.contrib.auth import get_user_model

User = get_user_model()

# djoser's endpoints, mounted under /auth/ in core/urls.py
REGISTER_URL = "/auth/users/"
JWT_CREATE_URL = "/auth/jwt/create/"
JWT_REFRESH_URL = "/auth/jwt/refresh/"
ME_URL = "/auth/users/me/"


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------


class TestRegistration:
    def test_register_creates_a_user(self, api_client, db, password):
        response = api_client.post(
            REGISTER_URL,
            {"email": "new@example.com", "password": password},
            format="json",
        )

        assert response.status_code == 201
        assert User.objects.filter(email="new@example.com").exists()

    def test_register_stores_a_hashed_password(self, api_client, db, password):
        """A plaintext password in the DB is a data breach waiting to happen."""
        api_client.post(
            REGISTER_URL,
            {"email": "new@example.com", "password": password},
            format="json",
        )

        user = User.objects.get(email="new@example.com")
        assert user.password != password
        assert user.check_password(password)

    def test_register_never_echoes_the_password_back(self, api_client, db, password):
        """password is write_only -- it must not appear in the response body."""
        response = api_client.post(
            REGISTER_URL,
            {"email": "new@example.com", "password": password},
            format="json",
        )

        assert "password" not in response.data

    def test_register_rejects_a_duplicate_email(self, api_client, user, password):
        """User.email is unique=True -- this is the DB constraint surfacing as 400."""
        response = api_client.post(
            REGISTER_URL,
            {"email": user.email, "password": password},
            format="json",
        )

        assert response.status_code == 400
        assert "email" in response.data

    def test_register_rejects_a_weak_password(self, api_client, db):
        """Django's AUTH_PASSWORD_VALIDATORS should be enforced at signup."""
        response = api_client.post(
            REGISTER_URL,
            {"email": "weak@example.com", "password": "123"},
            format="json",
        )

        assert response.status_code == 400
        assert not User.objects.filter(email="weak@example.com").exists()

    def test_register_requires_an_email(self, api_client, db, password):
        response = api_client.post(REGISTER_URL, {"password": password}, format="json")

        assert response.status_code == 400
        assert "email" in response.data


# ---------------------------------------------------------------------------
# Login
# ---------------------------------------------------------------------------


class TestLogin:
    def test_login_returns_access_and_refresh_tokens(self, api_client, user, password):
        response = api_client.post(
            JWT_CREATE_URL,
            {"email": user.email, "password": password},
            format="json",
        )

        assert response.status_code == 200
        assert "access" in response.data
        assert "refresh" in response.data

    def test_login_with_a_wrong_password_is_rejected(self, api_client, user):
        response = api_client.post(
            JWT_CREATE_URL,
            {"email": user.email, "password": "definitely-wrong"},
            format="json",
        )

        assert response.status_code == 401

    def test_login_with_an_unknown_email_is_rejected(self, api_client, db, password):
        """Same response as a wrong password -- don't leak which emails exist."""
        response = api_client.post(
            JWT_CREATE_URL,
            {"email": "nobody@example.com", "password": password},
            format="json",
        )

        assert response.status_code == 401

    def test_deactivated_user_cannot_log_in(self, api_client, user, password):
        user.is_active = False
        user.save(update_fields=["is_active"])

        response = api_client.post(
            JWT_CREATE_URL,
            {"email": user.email, "password": password},
            format="json",
        )

        assert response.status_code == 401

    def test_login_does_not_require_a_username(self, api_client, user, password):
        """
        Your User model dropped the username field (USERNAME_FIELD = 'email').
        If djoser ever starts demanding a username again, this fails loudly.
        """
        response = api_client.post(
            JWT_CREATE_URL,
            {"email": user.email, "password": password},
            format="json",
        )

        assert response.status_code == 200


# ---------------------------------------------------------------------------
# The "who am I" endpoint -- proves the token can actually authenticate
# ---------------------------------------------------------------------------


class TestCurrentUser:
    def test_me_requires_authentication(self, api_client, db):
        response = api_client.get(ME_URL)

        assert response.status_code == 401

    def test_me_returns_the_logged_in_user(self, auth_client, user):
        response = auth_client.get(ME_URL)

        assert response.status_code == 200
        assert response.data["email"] == user.email

    def test_me_rejects_a_garbage_token(self, api_client, db):
        api_client.credentials(HTTP_AUTHORIZATION="JWT not-a-real-token")

        response = api_client.get(ME_URL)

        assert response.status_code == 401

    def test_me_rejects_a_token_with_the_wrong_prefix(self, api_client, user, password):
        """
        AUTH_HEADER_TYPES is ("JWT",), so `Bearer <token>` must NOT authenticate.
        If this ever passes, your header types setting changed.
        """
        login = api_client.post(
            JWT_CREATE_URL,
            {"email": user.email, "password": password},
            format="json",
        )
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {login.data['access']}")

        response = api_client.get(ME_URL)

        assert response.status_code == 401


# ---------------------------------------------------------------------------
# Token lifecycle -- verifies the SIMPLE_JWT settings behaviour
# ---------------------------------------------------------------------------


class TestTokenLifecycle:
    def test_refresh_returns_a_new_access_token(self, api_client, user, password):
        login = api_client.post(
            JWT_CREATE_URL,
            {"email": user.email, "password": password},
            format="json",
        )

        response = api_client.post(
            JWT_REFRESH_URL,
            {"refresh": login.data["refresh"]},
            format="json",
        )

        assert response.status_code == 200
        assert "access" in response.data

    def test_refresh_rotates_the_refresh_token(self, api_client, user, password):
        """
        ROTATE_REFRESH_TOKENS = True. Each refresh must hand back a *new*
        refresh token, so a stolen refresh token has a short useful life.
        """
        login = api_client.post(
            JWT_CREATE_URL,
            {"email": user.email, "password": password},
            format="json",
        )
        original_refresh = login.data["refresh"]

        first_refresh = api_client.post(
            JWT_REFRESH_URL,
            {"refresh": original_refresh},
            format="json",
        )

        assert first_refresh.status_code == 200
        assert first_refresh.data["refresh"] != original_refresh

    def test_rotated_refresh_token_is_blacklisted(self, api_client, user, password):
        """
        BLACKLIST_AFTER_ROTATION = True.

        This is the test that catches a silent misconfiguration: if
        rest_framework_simplejwt.token_blacklist is not in INSTALLED_APPS, the
        setting does nothing, the old token keeps working, and nobody notices.
        """
        login = api_client.post(
            JWT_CREATE_URL,
            {"email": user.email, "password": password},
            format="json",
        )
        original_refresh = login.data["refresh"]

        # Rotate it once, which should blacklist the original.
        api_client.post(
            JWT_REFRESH_URL,
            {"refresh": original_refresh},
            format="json",
        )

        # Replaying the original must now fail.
        replay = api_client.post(
            JWT_REFRESH_URL,
            {"refresh": original_refresh},
            format="json",
        )

        assert replay.status_code == 401

    def test_refresh_rejects_a_garbage_token(self, api_client, db):
        response = api_client.post(
            JWT_REFRESH_URL,
            {"refresh": "not-a-token"},
            format="json",
        )

        assert response.status_code == 401


# ---------------------------------------------------------------------------
# Test-infrastructure guards
# ---------------------------------------------------------------------------


class TestTestInfrastructure:
    def test_tests_cannot_reach_a_real_email_provider(self):
        """
        Guard test for the `no_real_email` fixture in conftest.py.

        Sends a real email through Django's mail API and asserts it landed in
        the in-memory outbox. If this ever fails, some test is one
        email-trigger away from making a real network call to Brevo -- and in
        Phase 3 you will absolutely be sending mail.

        Note: keyword arguments on purpose. Django 6.1 deprecates positional
        args on send_mail() as part of the mailers migration.
        """
        from django.core import mail
        from django.core.mail import send_mail

        send_mail(
            subject="probe",
            message="probe",
            from_email="from@example.com",
            recipient_list=["to@example.com"],
        )

        assert len(mail.outbox) == 1
