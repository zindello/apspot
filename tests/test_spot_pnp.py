"""Tests for the spot_pnp lambda: per-program validation and routing."""
import json

import spot_pnp
from conftest import FakeResponse


def test_sendpnpspot_success(http):
    captured = {}

    def fake_post(url, json=None, **kw):
        captured["url"] = url
        captured["json"] = json
        return FakeResponse(200, text='{"result":"Success"}')

    http(spot_pnp, post=fake_post)
    result = spot_pnp.sendpnpspot("WWFF", "VK1ABC", "VKFF-1929", "SSB", "7.144", "CQ")
    assert captured["json"]["userID"] == "APSPOT"
    assert captured["json"]["APIKey"] == "TESTKEY"
    assert captured["url"].endswith("/SPOT")
    assert "SUCCESSFULLY SPOTTED" in result


def test_sendpnpspot_aptest_uses_debug(http):
    captured = {}

    def fake_post(url, json=None, **kw):
        captured["url"] = url
        return FakeResponse(200, text='{"result":"Success"}')

    http(spot_pnp, post=fake_post)
    result = spot_pnp.sendpnpspot("WWFF", "VK1ABC", "VKFF-1929", "SSB", "7.144", "APTEST")
    assert captured["url"].endswith("/SPOT/DEBUG")
    assert "TEST SPOTTED" in result


def test_handler_wwff_happy_path(http):
    def fake_get(url, *a, **k):
        if "/callsign/" in url:
            return FakeResponse(200, text='["VK1ABC"]')
        if "/PARK/WWFF/" in url:
            return FakeResponse(200, text='{"ref":"VKFF-1929","Status":"active"}')
        return FakeResponse(404)

    http(spot_pnp, get=fake_get, post=FakeResponse(200, text='{"result":"Success"}'))
    event = {"queryStringParameters": {
        "pnpSpotType": "WWFF", "callsign": "VK1ABC", "ref": "VKFF-1929",
        "freq": "7.144", "mode": "SSB", "comment": "CQ"}}
    result = spot_pnp.lambda_handler(event, None)
    body = json.loads(result["body"])
    assert "SUCCESSFULLY SPOTTED" in body["response"]


def test_handler_unknown_spot_type(http):
    http(spot_pnp, get=FakeResponse(200, text='["VK1ABC"]'), post=FakeResponse(200))
    event = {"queryStringParameters": {
        "pnpSpotType": "BOGUS", "callsign": "VK1ABC", "ref": "X",
        "freq": "7.144", "mode": "SSB", "comment": "CQ"}}
    result = spot_pnp.lambda_handler(event, None)
    body = json.loads(result["body"])
    assert "NOT IN DB" in body["response"]
