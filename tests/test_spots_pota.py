"""Tests for the spots_pota lambda: sorting, mode filter, formatting, limits."""
import json

import spots_pota
from conftest import FakeResponse

SPOTS = [
    {"spotId": "10", "activator": "VK1ABC", "reference": "K-1", "frequency": "7195", "mode": "SSB"},
    {"spotId": "30", "activator": "VK2DEF", "reference": "K-2", "frequency": "14285", "mode": "CW"},
    {"spotId": "20", "activator": "VK3GHI", "reference": "K-3", "frequency": "7090", "mode": "SSB"},
]


def _event(num, mode=None):
    qs = {"numSpots": str(num)}
    if mode is not None:
        qs["mode"] = mode
    return {"queryStringParameters": qs}


def test_extract_potaid():
    assert spots_pota.extract_potaid({"spotId": "42"}) == 42
    assert spots_pota.extract_potaid({}) == 0


def test_sorted_desc_and_limited(http):
    http(spots_pota, get=FakeResponse(200, json_body=SPOTS))
    result = spots_pota.lambda_handler(_event(2), None)
    body = json.loads(result["body"])
    assert len(body["response"]) == 2
    # Highest spotId (30, VK2DEF) first.
    assert "VK2DEF" in body["response"][0]
    assert "VK3GHI" in body["response"][1]


def test_mode_filter(http):
    http(spots_pota, get=FakeResponse(200, json_body=SPOTS))
    result = spots_pota.lambda_handler(_event(5, mode="CW"), None)
    body = json.loads(result["body"])
    assert len(body["response"]) == 1
    assert "VK2DEF" in body["response"][0]


def test_no_spots(http):
    http(spots_pota, get=FakeResponse(200, text="[]"))
    result = spots_pota.lambda_handler(_event(3), None)
    body = json.loads(result["body"])
    assert body["response"] == ["No current POTA spots in pota.app"]


def test_no_matching_mode(http):
    http(spots_pota, get=FakeResponse(200, json_body=SPOTS))
    result = spots_pota.lambda_handler(_event(5, mode="FT8"), None)
    body = json.loads(result["body"])
    assert body["response"][0] == "No current FT8 POTA spots in pota.app"
