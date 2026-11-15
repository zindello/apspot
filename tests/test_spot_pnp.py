"""Tests for the spot_pnp lambda against the new On The Air platform API."""
import json

import spot_pnp
from conftest import FakeResponse


def asset(asset_type="wwff park", code="VKFF-1929", is_active=True):
    return FakeResponse(200, json_body=[
        {"asset_type": asset_type, "code": code, "is_active": is_active}])


def test_mhz_to_khz():
    assert spot_pnp.mhz_to_khz("7.144") == "7144"
    assert spot_pnp.mhz_to_khz("14.0745") == "14074.5"
    assert spot_pnp.mhz_to_khz("garbage") == "garbage"


def test_sendpnpspot_success(http):
    captured = {}

    def fake_post(url, data=None, **kw):
        captured["url"] = url
        captured["data"] = data
        return FakeResponse(200, json_body={"success": True, "message": "Thanks for the data!"})

    http(spot_pnp, post=fake_post)
    result = spot_pnp.sendpnpspot("WWFF", "VK1ABC", "VKFF-1929", "SSB", "7.144", "CQ")
    assert captured["url"].endswith("/spots")
    assert captured["data"]["userID"] == "APSPOT"
    assert captured["data"]["APIKey"] == "TESTKEY"
    assert captured["data"]["activator"] == "VK1ABC"
    assert captured["data"]["spotter"] == "VK1ABC"
    assert captured["data"]["reference"] == "VKFF-1929"
    assert captured["data"]["frequency"] == "7144"
    assert captured["data"]["comments"] == "CQ"
    assert "SUCCESSFULLY SPOTTED" in result


def test_sendpnpspot_aptest_adds_debug_comment(http):
    captured = {}

    def fake_post(url, data=None, **kw):
        captured["url"] = url
        captured["data"] = data
        return FakeResponse(200, json_body={"success": True, "message": "Thanks for the data!"})

    http(spot_pnp, post=fake_post)
    result = spot_pnp.sendpnpspot("WWFF", "VK1ABC", "VKFF-1929", "SSB", "7.144", "APTEST")
    assert captured["url"].endswith("/spots")
    assert "DEBUG" in captured["data"]["comments"]
    assert "TEST SPOTTED" in result


def test_sendpnpspot_failure_response(http):
    http(spot_pnp, post=FakeResponse(200, json_body={"success": False, "message": "Authentication failed!"}))
    result = spot_pnp.sendpnpspot("WWFF", "VK1ABC", "VKFF-1929", "SSB", "7.144", "CQ")
    assert "ERRPNP" in result


def test_handler_wwff_happy_path(http):
    def fake_get(url, *a, **k):
        if url.endswith("/assets"):
            return asset("wwff park", "VKFF-1929")
        return FakeResponse(404)

    http(spot_pnp, get=fake_get,
         post=FakeResponse(200, json_body={"success": True, "message": "Thanks for the data!"}))
    event = {"queryStringParameters": {
        "pnpSpotType": "WWFF", "callsign": "VK1ABC", "ref": "VKFF-1929",
        "freq": "7.144", "mode": "SSB", "comment": "CQ"}}
    result = spot_pnp.lambda_handler(event, None)
    body = json.loads(result["body"])
    assert "SUCCESSFULLY SPOTTED" in body["response"]


def test_handler_sota_ref_slash_sent_as_underscore(http):
    captured = {}

    def fake_get(url, params=None, **k):
        captured["params"] = params
        return asset("summit", "VK3/VC-001")

    http(spot_pnp, get=fake_get,
         post=FakeResponse(200, json_body={"success": True, "message": "Thanks for the data!"}))
    event = {"queryStringParameters": {
        "pnpSpotType": "SOTA", "callsign": "VK1ABC", "ref": "VK3/VC-001",
        "freq": "7.090", "mode": "CW", "comment": "CQ"}}
    result = spot_pnp.lambda_handler(event, None)
    body = json.loads(result["body"])
    assert captured["params"]["code"] == "VK3_VC-001"
    assert "SUCCESSFULLY SPOTTED" in body["response"]


def test_handler_ref_of_wrong_type_rejected(http):
    # A POTA park code must not validate a WWFF spot.
    http(spot_pnp, get=asset("pota park", "AU-0001"),
         post=FakeResponse(200, json_body={"success": True}))
    event = {"queryStringParameters": {
        "pnpSpotType": "WWFF", "callsign": "VK1ABC", "ref": "AU-0001",
        "freq": "7.144", "mode": "SSB", "comment": "CQ"}}
    result = spot_pnp.lambda_handler(event, None)
    body = json.loads(result["body"])
    assert "NOT IN DB" in body["response"]


def test_handler_inactive_ref_rejected(http):
    http(spot_pnp, get=asset("wwff park", "VKFF-1929", is_active=False),
         post=FakeResponse(200, json_body={"success": True}))
    event = {"queryStringParameters": {
        "pnpSpotType": "WWFF", "callsign": "VK1ABC", "ref": "VKFF-1929",
        "freq": "7.144", "mode": "SSB", "comment": "CQ"}}
    result = spot_pnp.lambda_handler(event, None)
    body = json.loads(result["body"])
    assert "NOT IN DB" in body["response"]


def test_handler_unknown_ref_rejected(http):
    http(spot_pnp, get=FakeResponse(200, text='[]'),
         post=FakeResponse(200, json_body={"success": True}))
    event = {"queryStringParameters": {
        "pnpSpotType": "WWFF", "callsign": "VK1ABC", "ref": "VKFF-9999",
        "freq": "7.144", "mode": "SSB", "comment": "CQ"}}
    result = spot_pnp.lambda_handler(event, None)
    body = json.loads(result["body"])
    assert "NOT IN DB" in body["response"]


def test_handler_unknown_spot_type(http):
    http(spot_pnp, get=FakeResponse(200, text='[]'), post=FakeResponse(200))
    event = {"queryStringParameters": {
        "pnpSpotType": "BOGUS", "callsign": "VK1ABC", "ref": "X",
        "freq": "7.144", "mode": "SSB", "comment": "CQ"}}
    result = spot_pnp.lambda_handler(event, None)
    body = json.loads(result["body"])
    assert "NOT IN DB" in body["response"]
