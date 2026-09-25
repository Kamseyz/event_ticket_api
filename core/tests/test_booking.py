"""
Phase 2 -- booking tests + the oversell race.

    pytest tests/test_booking.py -v                 # everything
    pytest tests/test_booking.py -k oversell -v     # just the race

Read the two README-style comments below before you run the race test --
SQLite has a limitation that will make a correct fix look broken.
"""

from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta

import pytest
from django.contrib.auth import get_user_model
from django.db import connection
from django.db.models import Sum
from django.db.utils import OperationalError
from django.utils import timezone
from rest_framework.test import APIClient

from booking.models import Booking
from events.models import Event, TicketTier

User = get_user_model()

BOOKING_URL = "/booking/"


def make_event(start_offset_days=10):
    start = timezone.now() + timedelta(days=start_offset_days)
    return Event.objects.create(
        title="Race Condition Arena",
        description="Tiny capacity, many buyers.",
        location="Lagos",
        start_time=start,
        end_time=start + timedelta(hours=4),
    )


# ---------------------------------------------------------------------------
# "Does this even work?" -- single request, no concurrency
# ---------------------------------------------------------------------------


class TestCreateBooking:
    def test_authenticated_user_can_book(self, auth_client, tier):
        response = auth_client.post(
            BOOKING_URL, {"tier_id": tier.id, "quantity": 1}, format="json"
        )

        assert response.status_code == 201
        assert Booking.objects.count() == 1

    def test_booking_starts_as_pending(self, auth_client, tier):
        response = auth_client.post(
            BOOKING_URL, {"tier_id": tier.id, "quantity": 2}, format="json"
        )

        assert response.data["status"] == "PENDING"

    def test_booking_gets_a_reference(self, auth_client, tier):
        response = auth_client.post(
            BOOKING_URL, {"tier_id": tier.id, "quantity": 1}, format="json"
        )

        assert response.data["booking_reference"]
        assert "PAIN_BOOKING" in response.data["booking_reference"]

    def test_total_price_is_price_times_quantity(self, auth_client, tier):
        """tier.price is 2500.00 (see the conftest fixture)."""
        response = auth_client.post(
            BOOKING_URL, {"tier_id": tier.id, "quantity": 3}, format="json"
        )

        assert str(response.data["total_price"]) == "7500.00"

    def test_booking_increments_the_sold_counter(self, auth_client, tier):
        auth_client.post(BOOKING_URL, {"tier_id": tier.id, "quantity": 4}, format="json")

        tier.refresh_from_db()
        assert tier.tickets_sold == 4

    def test_remaining_tickets_reflects_the_booking(self, auth_client, tier):
        auth_client.post(BOOKING_URL, {"tier_id": tier.id, "quantity": 25}, format="json")

        tier.refresh_from_db()
        assert tier.remaining_tickets == 75

    def test_anonymous_cannot_book(self, api_client, tier):
        response = api_client.post(
            BOOKING_URL, {"tier_id": tier.id, "quantity": 1}, format="json"
        )

        assert response.status_code == 401
        assert Booking.objects.count() == 0

    def test_zero_quantity_is_rejected(self, auth_client, tier):
        response = auth_client.post(
            BOOKING_URL, {"tier_id": tier.id, "quantity": 0}, format="json"
        )

        assert response.status_code == 400
        assert Booking.objects.count() == 0

    def test_negative_quantity_is_rejected(self, auth_client, tier):
        response = auth_client.post(
            BOOKING_URL, {"tier_id": tier.id, "quantity": -5}, format="json"
        )

        assert response.status_code == 400
        assert Booking.objects.count() == 0

    def test_unknown_tier_is_404(self, auth_client, db):
        response = auth_client.post(
            BOOKING_URL, {"tier_id": 999_999, "quantity": 1}, format="json"
        )

        assert response.status_code == 404
        assert Booking.objects.count() == 0


# ---------------------------------------------------------------------------
# Capacity boundaries -- one at a time
# ---------------------------------------------------------------------------


class TestCapacityBoundaries:
    def test_booking_exactly_all_remaining_succeeds(self, auth_client, tier):
        """The boundary itself is legal: 100 asked, 100 available -> allowed."""
        response = auth_client.post(
            BOOKING_URL, {"tier_id": tier.id, "quantity": 100}, format="json"
        )

        assert response.status_code == 201

        tier.refresh_from_db()
        assert tier.tickets_sold == 100
        assert tier.remaining_tickets == 0

    def test_one_over_the_remaining_is_rejected(self, auth_client, tier):
        response = auth_client.post(
            BOOKING_URL, {"tier_id": tier.id, "quantity": 101}, format="json"
        )

        assert response.status_code == 400
        assert Booking.objects.count() == 0

        tier.refresh_from_db()
        assert tier.tickets_sold == 0

    def test_sold_out_tier_rejects_any_booking(self, auth_client, tier):
        tier.tickets_sold = tier.capacity
        tier.save(update_fields=["tickets_sold"])

        response = auth_client.post(
            BOOKING_URL, {"tier_id": tier.id, "quantity": 1}, format="json"
        )

        assert response.status_code == 400
        assert Booking.objects.count() == 0

    def test_rejected_booking_does_not_touch_the_counter(self, auth_client, tier):
        tier.tickets_sold = 99
        tier.save(update_fields=["tickets_sold"])

        auth_client.post(BOOKING_URL, {"tier_id": tier.id, "quantity": 5}, format="json")

        tier.refresh_from_db()
        assert tier.tickets_sold == 99


# ---------------------------------------------------------------------------
# THE PHASE 2 TEST -- the oversell race
# ---------------------------------------------------------------------------
#
# WHY transaction=True
# --------------------
# The normal `db` fixture wraps each test in a transaction and rolls it back.
# Anything you create inside that transaction is INVISIBLE to other threads,
# because threads get their own database connection and uncommitted data is not
# visible across connections. So a plain db-fixture test would have every
# worker thread see an empty database and the race would never fire.
#
# `transaction=True` switches to real commits (TransactionTestCase semantics),
# which is exactly what you need to simulate concurrent buyers.
#
# ---------------------------------------------------------------------------
# WHY this test is only trustworthy on PostgreSQL
# ---------------------------------------------------------------------------
# SQLite does NOT support SELECT ... FOR UPDATE. Django's SQLite backend has
# `has_select_for_update = False`, and Django's SQL compiler only emits the
# locking clause when the backend supports it -- which means:
#
#     tier = TicketTier.objects.select_for_update().get(id=...)
#
# is SILENTLY IGNORED on SQLite. No error, no lock, no warning. You would add
# the "fix", re-run this test, and still see overselling -- and conclude your
# fix was wrong when actually the database threw it away.
#
# SQLite also uses whole-database write locking, which produces spurious
# "database is locked" errors under threads. So:
#
#   * On SQLite  -> use the atomic conditional UPDATE (compare-and-set) fix.
#                   It works, because it is a single SQL statement.
#   * On Postgres-> both fixes work, and this test is fully trustworthy.
#
# The two code paths in the worker below surface lock errors as a distinct
# value instead of exploding, so a failure tells you *which* problem you hit.


@pytest.mark.django_db(transaction=True)
def test_concurrent_bookings_never_oversell():
    """
    10 buyers, 1 ticket each, on a tier with capacity 5.

    The invariant is absolute: however the requests interleave, the number of
    tickets sold can never exceed capacity. Before the fix expect this to fail
    loudly with an OVERSELL message -- that failure IS the lesson. After the
    fix, expect accepted == 5 and sold == 5.
    """
    capacity = 5
    bookers = 10

    tier = TicketTier.objects.create(
        event=make_event(),
        name="VIP",
        price="1000.00",
        capacity=capacity,
    )

    users = [
        User.objects.create_user(email=f"racer{i}@example.com", password="testpass123")
        for i in range(bookers)
    ]

    def attempt(user):
        """One buyer, one request, on its own connection."""
        client = APIClient()
        client.force_authenticate(user=user)
        try:
            response = client.post(
                BOOKING_URL,
                {"tier_id": tier.id, "quantity": 1},
                format="json",
            )
            return response.status_code
        except OperationalError as exc:
            # SQLite's whole-database write lock. Not a bug in your code --
            # a limitation of the database you are testing against.
            return f"DB_LOCKED: {exc}"
        finally:
            # Threads get their own connection; close it or SQLite keeps the
            # file/db busy and later threads start failing to acquire.
            connection.close()

    with ThreadPoolExecutor(max_workers=bookers) as pool:
        statuses = list(pool.map(attempt, users))

    accepted = statuses.count(201)
    locked = sum(1 for s in statuses if isinstance(s, str))

    tier.refresh_from_db()
    sold = (
        Booking.objects.filter(ticket_tier=tier).aggregate(total=Sum("quantity"))[
            "total"
        ]
        or 0
    )

    context = (
        f"capacity={capacity} accepted={accepted} sold={sold} "
        f"counter={tier.tickets_sold} locked={locked} statuses={statuses}"
    )

    # The core invariant. If this fails, you sold more tickets than exist.
    assert sold <= capacity, f"OVERSELL: {context}"
    assert tier.tickets_sold <= capacity, f"OVERSELL (counter): {context}"

    # The counter must agree with reality. A "lost update" leaves tickets_sold
    # lower than the tickets actually booked.
    assert tier.tickets_sold == sold, f"COUNTER MISMATCH: {context}"

    # Every accepted booking is one ticket, so these must line up.
    assert accepted == sold, f"ACCEPTED/SOLD MISMATCH: {context}"

    # ...and the tier must actually SELL OUT.
    #
    # This assertion matters more than it looks. Everything above is satisfied
    # by "0 sold" -- so without these two lines the test would also pass if the
    # fix broke booking entirely (over-locking, deadlocks, everything rejected).
    # Proving the invariant is not enough; the happy path has to still work.
    assert accepted == capacity, f"CAPACITY NOT SATURATED: {context}"
    assert sold == capacity, f"CAPACITY NOT SATURATED: {context}"


@pytest.mark.django_db(transaction=True)
def test_concurrent_bookings_leave_no_bookings_when_tier_is_full():
    """
    Same race, but the tier starts sold out -- so a correct implementation must
    accept ZERO bookings. Catches a check that runs before any locking.
    """
    tier = TicketTier.objects.create(
        event=make_event(),
        name="Regular",
        price="500.00",
        capacity=3,
    )
    TicketTier.objects.filter(pk=tier.pk).update(tickets_sold=3)

    users = [
        User.objects.create_user(email=f"late{i}@example.com", password="testpass123")
        for i in range(6)
    ]

    def attempt(user):
        client = APIClient()
        client.force_authenticate(user=user)
        try:
            response = client.post(
                BOOKING_URL, {"tier_id": tier.id, "quantity": 1}, format="json"
            )
            return response.status_code
        except OperationalError as exc:
            return f"DB_LOCKED: {exc}"
        finally:
            connection.close()

    with ThreadPoolExecutor(max_workers=len(users)) as pool:
        statuses = list(pool.map(attempt, users))

    assert statuses.count(201) == 0, f"booked onto a full tier: {statuses}"
    assert Booking.objects.count() == 0


@pytest.mark.django_db(transaction=True)
def test_concurrent_bookings_respect_a_multi_ticket_request():
    """
    5 buyers each want 2 tickets, but only 5 exist.

    A correct implementation accepts exactly TWO of them (2 + 2 = 4 accepted,
    the third would need ticket #5 and #6). This catches an off-by-one in the
    capacity comparison that single-ticket tests miss.
    """
    tier = TicketTier.objects.create(
        event=make_event(),
        name="Pair",
        price="200.00",
        capacity=5,
    )

    users = [
        User.objects.create_user(email=f"pair{i}@example.com", password="testpass123")
        for i in range(5)
    ]

    def attempt(user):
        client = APIClient()
        client.force_authenticate(user=user)
        try:
            response = client.post(
                BOOKING_URL, {"tier_id": tier.id, "quantity": 2}, format="json"
            )
            return response.status_code
        except OperationalError as exc:
            return f"DB_LOCKED: {exc}"
        finally:
            connection.close()

    with ThreadPoolExecutor(max_workers=len(users)) as pool:
        statuses = list(pool.map(attempt, users))

    tier.refresh_from_db()
    sold = (
        Booking.objects.filter(ticket_tier=tier).aggregate(total=Sum("quantity"))[
            "total"
        ]
        or 0
    )

    context = f"accepted={statuses.count(201)} sold={sold} statuses={statuses}"

    assert sold <= 5, f"OVERSELL: {context}"
    assert sold == 4, f"expected exactly 2 winners at 2 tickets each: {context}"
    assert tier.tickets_sold == sold, f"COUNTER MISMATCH: {context}"


# ---------------------------------------------------------------------------
# The mechanism, deterministically (no threads, no lock noise)
# ---------------------------------------------------------------------------


class TestLostUpdateMechanism:
    """
    Fast, deterministic proof of WHY the counter drifts, so you can reason about
    the fix without waiting on threads.

    These do not call your endpoint. They reproduce the exact read-modify-write
    pattern your service uses so you can see the failure in isolation -- and
    then see the primitive that fixes it.
    """

    def test_read_modify_write_loses_a_concurrent_update(self, tier):
        """
        Two "requests" each hold their own copy of the same row. Both add to
        tickets_sold, both save. The second one overwrites the first.

        This is precisely what `tier.tickets_sold += quantity; tier.save()`
        does under concurrency. The counter ends up LOWER than reality, which is
        what makes the tier keep selling tickets it no longer has.
        """
        request_a = TicketTier.objects.get(pk=tier.pk)
        request_b = TicketTier.objects.get(pk=tier.pk)

        # Request A books 3 tickets and saves -> database now says 3.
        request_a.tickets_sold += 3
        request_a.save()

        # Request B is still holding its STALE copy (tickets_sold == 0).
        request_b.tickets_sold += 1
        request_b.save()

        tier.refresh_from_db()

        # Naive expectation: 4. Reality: 1. Request A's 3 tickets vanished.
        assert tier.tickets_sold == 1
        assert tier.tickets_sold != 4

    def test_database_level_increment_does_not_lose_updates(self, tier):
        """
        The same two writes, but the increment happens INSIDE the database via
        an F() expression instead of in Python.

        Nothing is lost, because the new value is computed from the row's
        current value at write time -- there is no stale copy to clobber it.

        This is the primitive your fix will be built from. Either this, or a
        row lock (select_for_update, Postgres only).
        """
        from django.db.models import F

        TicketTier.objects.filter(pk=tier.pk).update(tickets_sold=F("tickets_sold") + 3)
        TicketTier.objects.filter(pk=tier.pk).update(tickets_sold=F("tickets_sold") + 1)

        tier.refresh_from_db()

        assert tier.tickets_sold == 4
