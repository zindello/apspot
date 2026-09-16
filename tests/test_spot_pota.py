"""Tests for the spot_pota lambda: validation, payload, routing."""
import json

import spot_pota
from conftest import FakeResponse


def test_validatecall_ok(http):
    http(spot_pota, get=FakeResponse(200, text='{"callsign":"VK1ABC"}'))
    assert spot_pota.validatecall_pota("VK1ABC") is True


def test_validatecall_not_found(http):
    http(spot_pota, get=FakeResponse(404, text="not found"))
    assert spot_pota.validatecall_pota("VK1ABC") is False


def test_validatepark_ktest_bypass():
    # K-TEST is the reserved park that skips the DB lookup.
    assert spot_pota.validatepark_pota("K-TEST") is True


def test_validatepark_active(http):
    http(spot_pota, get=FakeResponse(200, text='{"active": 1}'))
    assert spot_pota.validatepark_pota("K-1234") is True


def test_validatepark_inactive(http):
    http(spot_pota, get=FakeResponse(200, text='{"active": 0}'))
    assert spot_pota.validatepark_pota("K-1234") is False


def test_sendpotaspot_payload_and_freq(http):
    captured = {}

    def fake_post(url, json=None, **kw):
        captured["url"] = url
        captured["json"] = json
        return FakeResponse(200, text='{"activator":"VK1ABC"}')

    http(spot_pota, post=fake_post)
    result = spot_pota.sendpotaspot("VK1ABC", "K-1234", "SSB", "7.195", "CQ [APSPOT]")

    # Frequency is converted MHz -> kHz.
    assert captured["json"]["frequency"] == "7195.0"
    assert captured["json"]["reference"] == "K-1234"
    assert captured["url"].endswith("/spot")
    assert "SUCCESSFULLY SPOTTED" in result


def test_sendpotaspot_aptest_uses_dev(http):
    captured = {}

    def fake_post(url, json=None, **kw):
        captured["url"] = url
        return FakeResponse(200, text='{"activator":"VK1ABC"}')

    http(spot_pota, post=fake_post)
    result = spot_pota.sendpotaspot("VK1ABC", "K-1234", "SSB", "7.195", "APTEST")
    assert captured["url"].startswith("https://devapi.pota.test")
    assert "TEST SPOTTED" in result


def test_handler_happy_path(http):
    def fake_get(url, *a, **k):
        if "/stats/user/" in url:
            return FakeResponse(200, text='{"callsign":"VK1ABC"}')
        if "/park/" in url:
            return FakeResponse(200, text='{"active": 1}')
        return FakeResponse(404)

    http(spot_pota, get=fake_get,
         post=FakeResponse(200, text='{"activator":"VK1ABC"}'))

    event = {"queryStringParameters": {
        "callsign": "VK1ABC", "ref": "K-1234", "freq": "7.195",
        "mode": "SSB", "comment": "CQ [APSPOT]"}}
    result = spot_pota.lambda_handler(event, None)
    body = json.loads(result["body"])
    assert "SUCCESSFULLY SPOTTED" in body["response"]


def test_handler_unknown_call(http):
    http(spot_pota, get=FakeResponse(404), post=FakeResponse(200))
    event = {"queryStringParameters": {
        "callsign": "NOPE", "ref": "K-TEST", "freq": "7.195",
        "mode": "SSB", "comment": "CQ"}}
    result = spot_pota.lambda_handler(event, None)
    body = json.loads(result["body"])
    assert "NOT IN DB" in body["response"]
