"""
Phase 1 -- events CRUD tests.

Run just this file with:

    pytest tests/test_events.py -v

What this file is protecting:

* Anonymous visitors can read events, but nobody without staff rights can write.
* An admin creating an event really creates its nested ticket tiers.
* Internal bookkeeping (tickets_sold) is not writable by a client.
* The start/end time rule holds no matter how the event is edited -- including
  a PATCH that only supplies ONE of the two timestamps.
* Event creation is all-or-nothing, so a mid-way failure cannot leave an
  orphaned Event row behind.

NOTE: two tests here are expected to FAIL until Bug 2 is finished. They are
marked with "REGRESSION" in the docstring.
"""

from datetime import timedelta

import pytest
from django.db import IntegrityError
from django.utils import timezone

from events.models import Event, TicketTier

# events/urls.py is included at the project root, so these paths are bare.
LIST_URL = "/events/"
CREATE_URL = "/events/create/"


def detail_url(pk):
    return f"/events/{pk}/"


def update_url(pk):
    return f"/events/{pk}/update/"


def delete_url(pk):
    return f"/events/{pk}/delete/"


# ---------------------------------------------------------------------------
# Public reads -- anyone, no token
# ---------------------------------------------------------------------------


class TestPublicRead:
    def test_anonymous_visitor_can_list_events(self, api_client, event):
        response = api_client.get(LIST_URL)

        assert response.status_code == 200
        assert len(response.data) == 1
        assert response.data[0]["title"] == event.title

    def test_list_returns_nested_tiers(self, api_client, tier):
        response = api_client.get(LIST_URL)

        tiers = response.data[0]["ticket_tiers"]
        assert len(tiers) == 1
        assert tiers[0]["name"] == "Regular"
        assert tiers[0]["capacity"] == 100

    def test_list_does_not_expose_internal_sales_counter(self, api_client, tier):
        """
        tickets_sold is internal bookkeeping. It is deliberately absent from
        TicketTierSerializers.fields -- keep it that way.
        """
        response = api_client.get(LIST_URL)

        assert "tickets_sold" not in response.data[0]["ticket_tiers"][0]

    def test_anonymous_visitor_can_retrieve_one_event(self, api_client, event):
        response = api_client.get(detail_url(event.id))

        assert response.status_code == 200
        assert response.data["id"] == event.id

    def test_retrieving_an_unknown_event_is_404(self, api_client, db):
        response = api_client.get(detail_url(999_999))

        assert response.status_code == 404

    def test_list_does_not_trigger_an_n_plus_1_query(
        self, api_client, event, django_assert_max_num_queries
    ):
        """
        list_event() uses prefetch_related('ticket_tiers').

        Without it, serialising 5 tiers costs 1 query for the events plus 5 for
        the tiers. With it, the whole page is 2 queries. A hard-coded count is
        brittle, so we assert a *maximum* -- enough to prove prefetching works,
        loose enough to survive an extra incidental query.
        """
        for i in range(5):
            TicketTier.objects.create(
                event=event, name=f"Tier {i}", price="100.00", capacity=10
            )

        with django_assert_max_num_queries(3):
            api_client.get(LIST_URL)


# ---------------------------------------------------------------------------
# Write permissions -- staff only
# ---------------------------------------------------------------------------


class TestWritePermissions:
    def test_anonymous_cannot_create_an_event(self, api_client, db, event_payload):
        response = api_client.post(CREATE_URL, event_payload, format="json")

        assert response.status_code == 401
        assert Event.objects.count() == 0

    def test_regular_user_cannot_create_an_event(self, auth_client, event_payload):
        response = auth_client.post(CREATE_URL, event_payload, format="json")

        assert response.status_code == 403
        assert Event.objects.count() == 0

    def test_regular_user_cannot_update_an_event(self, auth_client, event):
        response = auth_client.patch(
            update_url(event.id), {"title": "Hacked"}, format="json"
        )

        assert response.status_code == 403
        event.refresh_from_db()
        assert event.title == "Nairobi Tech Summit"

    def test_regular_user_cannot_delete_an_event(self, auth_client, event):
        response = auth_client.delete(delete_url(event.id))

        assert response.status_code == 403
        assert Event.objects.filter(id=event.id).exists()

    def test_regular_user_cannot_create_a_tier_on_someone_elses_event(
        self, auth_client, event
    ):
        """
        Tiers are only writable through the event create endpoint, which is
        already staff-gated. This asserts no separate tier-write route leaked in.
        """
        response = auth_client.post(
            f"/events/{event.id}/tiers/",
            {"name": "Free", "price": "0.00", "capacity": 10},
            format="json",
        )

        assert response.status_code in (403, 404)
        assert event.ticket_tiers.count() == 0


# ---------------------------------------------------------------------------
# Admin create
# ---------------------------------------------------------------------------


class TestAdminCreateEvent:
    def test_admin_creates_an_event_with_its_tiers(self, admin_client, db, event_payload):
        response = admin_client.post(CREATE_URL, event_payload, format="json")

        assert response.status_code == 201
        assert Event.objects.count() == 1

        created = Event.objects.get()
        assert created.title == "Lagos Music Festival"
        assert created.ticket_tiers.count() == 2
        assert set(created.ticket_tiers.values_list("name", flat=True)) == {
            "Regular",
            "VIP",
        }

    def test_response_contains_the_nested_tiers(self, admin_client, db, event_payload):
        response = admin_client.post(CREATE_URL, event_payload, format="json")

        tiers = response.data["ticket_tiers"]
        assert len(tiers) == 2
        assert all("id" in tier for tier in tiers)

    def test_tier_price_and_capacity_are_persisted(self, admin_client, db, event_payload):
        admin_client.post(CREATE_URL, event_payload, format="json")

        vip = TicketTier.objects.get(name="VIP")
        assert vip.capacity == 50
        assert str(vip.price) == "25000.00"

    def test_client_cannot_preset_tickets_sold(self, admin_client, db, event_payload):
        """
        tickets_sold is not a serializer field, so DRF must ignore it rather
        than let a client inflate or wipe the sales counter.
        """
        event_payload["ticket_tiers"][0]["tickets_sold"] = 9999

        response = admin_client.post(CREATE_URL, event_payload, format="json")

        assert response.status_code == 201
        assert TicketTier.objects.get(name="Regular").tickets_sold == 0

    def test_create_requires_the_mandatory_fields(self, admin_client, db):
        response = admin_client.post(CREATE_URL, {"title": "No dates"}, format="json")

        assert response.status_code == 400
        assert Event.objects.count() == 0

    def test_creating_an_event_with_no_tiers_is_currently_allowed(
        self, admin_client, db, event_payload
    ):
        """
        Documents today's behaviour: `ticket_tiers: []` is accepted.

        Decide whether an event must ship with at least one tier. If yes, this
        test should flip to expecting 400 -- change it deliberately, don't just
        delete it.
        """
        event_payload["ticket_tiers"] = []

        response = admin_client.post(CREATE_URL, event_payload, format="json")

        assert response.status_code == 201
        assert Event.objects.get().ticket_tiers.count() == 0


# ---------------------------------------------------------------------------
# Date validation
# ---------------------------------------------------------------------------


class TestEventDateValidation:
    def test_create_rejects_end_time_before_start_time(
        self, admin_client, db, event_payload
    ):
        start = timezone.now() + timedelta(days=5)
        event_payload["start_time"] = start.isoformat()
        event_payload["end_time"] = (start - timedelta(hours=1)).isoformat()

        response = admin_client.post(CREATE_URL, event_payload, format="json")

        assert response.status_code == 400
        assert "End time" in str(response.data)
        assert Event.objects.count() == 0

    def test_create_rejects_equal_start_and_end_times(
        self, admin_client, db, event_payload
    ):
        """A zero-length event is nonsense -- the rule is strictly 'after'."""
        start = timezone.now() + timedelta(days=5)
        event_payload["start_time"] = start.isoformat()
        event_payload["end_time"] = start.isoformat()

        response = admin_client.post(CREATE_URL, event_payload, format="json")

        assert response.status_code == 400
        assert Event.objects.count() == 0

    def test_patch_rejects_end_time_that_runs_before_the_stored_start_time(
        self, admin_client, event
    ):
        """
        REGRESSION TEST -- expected to fail until Bug 2 is finished.

        This PATCH sends ONLY end_time. The serializer must fall back to the
        stored start_time via self.instance; otherwise the guard
        `if start_time and end_time` is skipped entirely because start_time is
        absent from the payload, and an invalid event gets saved with a 200.
        """
        response = admin_client.patch(
            update_url(event.id),
            {"end_time": (event.start_time - timedelta(hours=2)).isoformat()},
            format="json",
        )

        assert response.status_code == 400

        event.refresh_from_db()
        assert event.end_time > event.start_time

    def test_patch_accepts_a_valid_end_time_change(self, admin_client, event):
        new_end = event.start_time + timedelta(hours=3)

        response = admin_client.patch(
            update_url(event.id),
            {"end_time": new_end.isoformat()},
            format="json",
        )

        assert response.status_code == 200

        event.refresh_from_db()
        assert event.end_time == new_end


# ---------------------------------------------------------------------------
# Atomicity (Bug 1 regression)
# ---------------------------------------------------------------------------


class TestCreateEventAtomicity:
    def test_event_is_rolled_back_when_a_tier_insert_fails(
        self, admin_client, db, event_payload, monkeypatch
    ):
        """
        Bug 1 regression test.

        We force the *second* tier insert to blow up at the DB layer. Without
        `transaction.atomic()` around create_event, the Event row is already
        committed by then, so the failure leaves an orphaned event with a single
        tier -- data the client never successfully created.

        Patching the manager (rather than sending bad data) is deliberate: bad
        data would be rejected by the serializer *before* anything is written,
        which would test validation, not atomicity.
        """
        real_create = TicketTier.objects.create
        calls = {"count": 0}

        def failing_create(*args, **kwargs):
            calls["count"] += 1
            if calls["count"] == 2:
                raise IntegrityError("simulated failure on the second tier")
            return real_create(*args, **kwargs)

        monkeypatch.setattr(TicketTier.objects, "create", failing_create)

        with pytest.raises(IntegrityError):
            admin_client.post(CREATE_URL, event_payload, format="json")

        assert Event.objects.count() == 0, "orphaned Event left behind!"
        assert TicketTier.objects.count() == 0, "partial tiers left behind!"


# ---------------------------------------------------------------------------
# Admin update
# ---------------------------------------------------------------------------


class TestAdminUpdateEvent:
    def test_patch_updates_a_single_field(self, admin_client, event):
        response = admin_client.patch(
            update_url(event.id), {"title": "Renamed Summit"}, format="json"
        )

        assert response.status_code == 200
        event.refresh_from_db()
        assert event.title == "Renamed Summit"

    def test_patch_leaves_unsupplied_fields_alone(self, admin_client, event):
        """PATCH is partial by definition -- everything else must survive."""
        original_location = event.location
        original_description = event.description

        admin_client.patch(update_url(event.id), {"title": "Only Title"}, format="json")

        event.refresh_from_db()
        assert event.location == original_location
        assert event.description == original_description

    def test_patch_returns_the_updated_event(self, admin_client, event):
        response = admin_client.patch(
            update_url(event.id), {"location": "Mombasa"}, format="json"
        )

        assert response.data["location"] == "Mombasa"

    def test_patching_an_unknown_event_is_404(self, admin_client, db):
        response = admin_client.patch(
            update_url(999_999), {"title": "Ghost"}, format="json"
        )

        assert response.status_code == 404


# ---------------------------------------------------------------------------
# Admin delete
# ---------------------------------------------------------------------------


class TestAdminDeleteEvent:
    def test_admin_can_delete_an_event(self, admin_client, event):
        response = admin_client.delete(delete_url(event.id))

        assert response.status_code == 200
        assert not Event.objects.filter(id=event.id).exists()

    def test_deleting_an_event_also_deletes_its_tiers(self, admin_client, tier):
        """TicketTier.event uses on_delete=CASCADE -- no orphan tiers."""
        event_id = tier.event_id

        admin_client.delete(delete_url(event_id))

        assert TicketTier.objects.filter(event_id=event_id).count() == 0

    def test_deleting_an_unknown_event_is_404(self, admin_client, db):
        response = admin_client.delete(delete_url(999_999))

        assert response.status_code == 404
