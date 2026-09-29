from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_basic_allocation_preserves_speaker_tracks_and_input_order():
    response = client.post(
        "/assign",
        json={
            "track_count": 2,
            "subtitles": [
                {"id": "a1", "speaker": "A", "start_ms": 0, "end_ms": 1000},
                {"id": "b1", "speaker": "B", "start_ms": 500, "end_ms": 1500},
                {"id": "a2", "speaker": "A", "start_ms": 1000, "end_ms": 2000},
                {"id": "b2", "speaker": "B", "start_ms": 1500, "end_ms": 2500},
            ],
        },
    )

    assert response.status_code == 200
    assert response.json() == {
        "solvable": True,
        "assignments": [
            {"id": "a1", "track": 1},
            {"id": "b1", "track": 2},
            {"id": "a2", "track": 1},
            {"id": "b2", "track": 2},
        ],
        "track_changes": 0,
    }


def test_minimizes_track_changes_by_speaker_time_order():
    # a2 is supplied before a1. Temporally a1 remains track 1, while locked a2
    # uses track 2, so A has exactly one change.
    response = client.post(
        "/assign",
        json={
            "track_count": 2,
            "subtitles": [
                {
                    "id": "a2",
                    "speaker": "A",
                    "start_ms": 200,
                    "end_ms": 300,
                    "locked_track": 2,
                },
                {"id": "a1", "speaker": "A", "start_ms": 0, "end_ms": 100},
                {
                    "id": "c1",
                    "speaker": "C",
                    "start_ms": 0,
                    "end_ms": 100,
                    "locked_track": 2,
                },
            ],
        },
    )

    assert response.status_code == 200
    assert response.json() == {
        "solvable": True,
        "assignments": [
            {"id": "a2", "track": 2},
            {"id": "a1", "track": 1},
            {"id": "c1", "track": 2},
        ],
        "track_changes": 1,
    }


def test_lexicographically_smallest_input_order_sequence_wins_ties():
    # All intervals are disjoint. Zero changes has many solutions; all track 1
    # is lexicographically smallest in input order.
    response = client.post(
        "/assign",
        json={
            "track_count": 3,
            "subtitles": [
                {"id": "1", "speaker": "A", "start_ms": 0, "end_ms": 10},
                {"id": "2", "speaker": "B", "start_ms": 20, "end_ms": 30},
                {"id": "3", "speaker": "A", "start_ms": 40, "end_ms": 50},
            ],
        },
    )

    assert response.status_code == 200
    assert [item["track"] for item in response.json()["assignments"]] == [
        1,
        1,
        1,
    ]
    assert response.json()["track_changes"] == 0


def test_locked_overlap_returns_empty_solution():
    response = client.post(
        "/assign",
        json={
            "track_count": 2,
            "subtitles": [
                {
                    "id": "a1",
                    "speaker": "A",
                    "start_ms": 0,
                    "end_ms": 100,
                    "locked_track": 1,
                },
                {
                    "id": "b1",
                    "speaker": "B",
                    "start_ms": 50,
                    "end_ms": 150,
                    "locked_track": 1,
                },
            ],
        },
    )

    assert response.status_code == 200
    assert response.json() == {
        "solvable": False,
        "assignments": [],
        "track_changes": 0,
    }


def test_three_simultaneous_subtitles_cannot_fit_two_tracks():
    response = client.post(
        "/assign",
        json={
            "track_count": 2,
            "subtitles": [
                {"id": "a", "speaker": "A", "start_ms": 0, "end_ms": 100},
                {"id": "b", "speaker": "B", "start_ms": 10, "end_ms": 90},
                {"id": "c", "speaker": "C", "start_ms": 20, "end_ms": 80},
            ],
        },
    )

    assert response.status_code == 200
    assert response.json()["solvable"] is False
    assert response.json()["assignments"] == []


def test_endpoint_contact_is_allowed():
    response = client.post(
        "/assign",
        json={
            "track_count": 2,
            "subtitles": [
                {"id": "a", "speaker": "A", "start_ms": 0, "end_ms": 100},
                {"id": "b", "speaker": "B", "start_ms": 100, "end_ms": 200},
            ],
        },
    )

    assert response.status_code == 200
    assert [item["track"] for item in response.json()["assignments"]] == [
        1,
        1,
    ]


def test_same_speaker_overlap_is_422():
    response = client.post(
        "/assign",
        json={
            "track_count": 2,
            "subtitles": [
                {"id": "a1", "speaker": "A", "start_ms": 0, "end_ms": 100},
                {"id": "a2", "speaker": "A", "start_ms": 50, "end_ms": 150},
            ],
        },
    )

    assert response.status_code == 422


def test_invalid_interval_duplicate_id_and_missing_track_is_422():
    response = client.post(
        "/assign",
        json={
            "subtitles": [
                {"id": "same", "speaker": "A", "start_ms": 100, "end_ms": 100},
                {"id": "same", "speaker": "B", "start_ms": 0, "end_ms": 50},
            ]
        },
    )

    assert response.status_code == 422


def test_locked_track_outside_range_is_422():
    response = client.post(
        "/assign",
        json={
            "track_count": 2,
            "subtitles": [
                {
                    "id": "a",
                    "speaker": "A",
                    "start_ms": 0,
                    "end_ms": 100,
                    "locked_track": 3,
                }
            ],
        },
    )

    assert response.status_code == 422


def test_boolean_integer_is_rejected():
    response = client.post(
        "/assign",
        json={
            "track_count": True,
            "subtitles": [
                {"id": "a", "speaker": "A", "start_ms": 0, "end_ms": 100}
            ],
        },
    )

    assert response.status_code == 422
