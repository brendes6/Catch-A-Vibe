"""Tests for the deterministic point-id hashing in data-processing.
"""

import process_data


def test_stable_point_id_is_deterministic():
    assert process_data._stable_point_id("Drake|||One Dance") == \
        process_data._stable_point_id("Drake|||One Dance")


def test_stable_point_id_within_63_bits():
    pid = process_data._stable_point_id("some-song-key")
    assert 0 <= pid < 2 ** 63


def test_stable_point_id_differs_for_different_songs():
    a = process_data._stable_point_id("artist-a|||track-a")
    b = process_data._stable_point_id("artist-b|||track-b")
    assert a != b
