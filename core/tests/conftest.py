"""
Shared pytest fixtures for the Event Ticketing API.

Everything the test modules need in order to talk to the API lives here, so the
test files themselves stay focused on *behaviour* instead of setup boilerplate.

Run the suite from this directory (the one holding manage.py + pytest.ini):

    pytest
"""

from datetime import timedelta

import pytest
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.utils import timezone
from rest_framework.test import APIClient

from events.models import Event, TicketTier

User = get_user_model()

# ---------------------------------------------------------------------------
# Endpoints under test (kept as constants so a URL change is a one-line fix)
# ---------------------------------------------------------------------------

JWT_CREATE_URL = "/auth/jwt/create/"
JWT_REFRESH_URL = "/auth/jwt/refresh/"
REGISTER_URL = "/auth/users/"
ME_URL = "/auth/users/me/"


# ---------------------------------------------------------------------------
# Cross-cutting safety nets
# ---------------------------------------------------------------------------


@pytest.fixture
def password():
    """The password every test user is created with (and logs in with)."""
    return "strongpass123"


@pytest.fixture(autouse=True)
def clear_throttle_cache():
    """
    Wipe DRF's throttle history around every single test.

    settings.py puts AnonRateThrottle (20/min) and UserRateThrottle (60/min) on
    *every* endpoint. DRF keeps its request counters in the cache, and that
    cache survives for the whole pytest process -- so without this fixture a
    suite that makes a few dozen requests starts returning 429 partway through,
    in a test that looks nothing like the cause. Classic "why is this failing
    now?" trap.
    """
    cache.clear()
    yield
    cache.clear()


@pytest.fixture(autouse=True)
def disable_silk(settings):
    """
    Strip django-silk out of the middleware stack while testing.

    Discovered the hard way: with SilkyMiddleware active, every request also
    writes silk_request / silk_sqlquery rows. That makes any query-count
    assertion meaningless (the /events/ list showed silk's own INSERTs), and it
    adds real overhead to every single request.

    Each (APIClient) builds its middleware chain when it is constructed -- which
    happens after this autouse fixture runs -- so removing it here takes effect.
    """
    settings.MIDDLEWARE = [m for m in settings.MIDDLEWARE if "silk" not in m.lower()]


@pytest.fixture(autouse=True)
def fast_password_hasher(settings):
    """
    Use a fast password hasher in tests only.

    PBKDF2 is deliberately slow -- that is the entire point of a password hash.
    A test suite hashes constantly (every create_user, every login, every
    registration test), which is why the raw suite took over 3 minutes. MD5
    drops that to milliseconds.

    NEVER do this in production settings.
    """
    settings.PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]


@pytest.fixture(autouse=True)
def no_real_email(settings):
    """
    Stop tests from calling the Brevo API.

    settings.py points the mail backend at anymail/Brevo, so any code path that
    sends mail would attempt a real network call. Swap in the in-memory backend
    instead -- `django.core.mail.outbox` then holds whatever was "sent".

    Note this overrides MAILERS, not EMAIL_BACKEND: Django 6.1 deprecates
    EMAIL_BACKEND in favour of MAILERS (removal in Django 7.0).
    """
    settings.MAILERS = {
        "default": {"BACKEND": "django.core.mail.backends.locmem.EmailBackend"}
    }


# ---------------------------------------------------------------------------
# Clients
# ---------------------------------------------------------------------------


@pytest.fixture
def api_client():
    """A fresh DRF APIClient. (pytest-django does not provide this one.)"""
    return APIClient()


def _login(client, email, password):
    """
    Log in through the *real* endpoint and attach the JWT to the client.

    Note the `JWT` prefix, not `Bearer`: settings.SIMPLE_JWT sets
    AUTH_HEADER_TYPES = ("JWT",). Change that setting and this helper is the
    single place the suite needs updating.
    """
    response = client.post(
        JWT_CREATE_URL,
        {"email": email, "password": password},
        format="json",
    )
    assert response.status_code == 200, f"login failed for {email}: {response.data}"
    client.credentials(HTTP_AUTHORIZATION=f"JWT {response.data['access']}")
    return client


# ---------------------------------------------------------------------------
# Users
# ---------------------------------------------------------------------------


@pytest.fixture
def user(db, password):
    """A normal, non-staff account."""
    return User.objects.create_user(email="customer@example.com", password=password)


@pytest.fixture
def admin_user(db, password):
    """A staff account. Only staff may write events (IsAdminUser)."""
    return User.objects.create_user(
        email="admin@example.com",
        password=password,
        is_staff=True,
    )


@pytest.fixture
def auth_client(api_client, user, password):
    """An APIClient already authenticated as `user`."""
    return _login(api_client, user.email, password)


@pytest.fixture
def admin_client(api_client, admin_user, password):
    """An APIClient already authenticated as `admin_user`."""
    return _login(api_client, admin_user.email, password)


# ---------------------------------------------------------------------------
# Event data
# ---------------------------------------------------------------------------


@pytest.fixture
def event(db):
    """One saved event, dated in the future."""
    start = timezone.now() + timedelta(days=10)
    return Event.objects.create(
        title="Nairobi Tech Summit",
        description="A one-day conference about shipping software.",
        location="KICC, Nairobi",
        start_time=start,
        end_time=start + timedelta(hours=8),
    )


@pytest.fixture
def tier(event):
    """One ticket tier hanging off `event`."""
    return TicketTier.objects.create(
        event=event,
        name="Regular",
        price="2500.00",
        capacity=100,
    )


@pytest.fixture
def event_payload():
    """A valid create-event request body, nested tiers included."""
    start = timezone.now() + timedelta(days=30)
    return {
        "title": "Lagos Music Festival",
        "description": "Three stages, two days.",
        "location": "Eko Hotel, Lagos",
        "start_time": start.isoformat(),
        "end_time": (start + timedelta(hours=6)).isoformat(),
        "ticket_tiers": [
            {"name": "Regular", "price": "5000.00", "capacity": 500},
            {"name": "VIP", "price": "25000.00", "capacity": 50},
        ],
    }
