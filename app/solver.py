from collections import defaultdict

from app.models import AssignmentRequest, AssignmentResponse, TrackAssignment


def solve_tracks(request: AssignmentRequest) -> AssignmentResponse:
    subtitles = request.subtitles
    track_count = request.track_count

    # Same-speaker neighbours are ordered by time, not necessarily by input order.
    indices_by_speaker: dict[str, list[int]] = defaultdict(list)
    for index, subtitle in enumerate(subtitles):
        indices_by_speaker[subtitle.speaker].append(index)

    adjacent_pairs: list[tuple[int, int]] = []
    for indices in indices_by_speaker.values():
        indices.sort(
            key=lambda i: (
                subtitles[i].start_ms,
                subtitles[i].end_ms,
                i,
            )
        )
        adjacent_pairs.extend(zip(indices, indices[1:]))

    occupied_intervals: list[list[tuple[int, int]]] = [
        [] for _ in range(track_count)
    ]
    assignment_by_input_index = [0] * len(subtitles)
    best_assignment: list[int] | None = None
    best_changes = len(subtitles) + 1
    current_changes = 0

    def has_overlap(track: int, start: int, end: int) -> bool:
        # Intervals are [start, end), so equal endpoints do not overlap.
        for other_start, other_end in occupied_intervals[track]:
            if start < other_end and other_start < end:
                return True
        return False

    def incremental_change_count(
        input_index: int,
        track: int,
    ) -> int:
        added_changes = 0
        for previous_index, current_index in adjacent_pairs:
            if current_index == input_index:
                previous_track = assignment_by_input_index[previous_index]
                if previous_track != 0 and previous_track != track:
                    added_changes += 1
            elif previous_index == input_index:
                current_track = assignment_by_input_index[current_index]
                if current_track != 0 and current_track != track:
                    added_changes += 1
        return added_changes

    def search(input_index: int) -> None:
        nonlocal best_assignment, best_changes, current_changes

        # Searching in lexicographic order means the first solution with a given
        # score is already the tie-breaker; equal or larger prefixes cannot win.
        if current_changes >= best_changes:
            return

        if input_index == len(subtitles):
            best_changes = current_changes
            best_assignment = assignment_by_input_index.copy()
            return

        subtitle = subtitles[input_index]
        if subtitle.locked_track is not None:
            candidates = (subtitle.locked_track,)
        else:
            candidates = range(1, track_count + 1)

        # Ascending track order makes complete solutions visited in lexicographic
        # order of their input-order track sequence.
        for track in candidates:
            track_index = track - 1
            if has_overlap(track_index, subtitle.start_ms, subtitle.end_ms):
                continue

            assignment_by_input_index[input_index] = track
            added_changes = incremental_change_count(input_index, track)
            current_changes += added_changes
            occupied_intervals[track_index].append(
                (subtitle.start_ms, subtitle.end_ms)
            )

            search(input_index + 1)

            occupied_intervals[track_index].pop()
            current_changes -= added_changes
            assignment_by_input_index[input_index] = 0

    search(0)

    if best_assignment is None:
        return AssignmentResponse(
            solvable=False,
            assignments=[],
            track_changes=0,
        )

    return AssignmentResponse(
        solvable=True,
        assignments=[
            TrackAssignment(
                id=subtitle.id,
                track=best_assignment[index],
            )
            for index, subtitle in enumerate(subtitles)
        ],
        track_changes=best_changes,
    )
