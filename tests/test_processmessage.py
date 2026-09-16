"""Tests for the central processmessage lambda: pure helpers + routing."""
import json

import processmessage as pm
from conftest import FakeResponse


# --- pure helpers -----------------------------------------------------------

def test_isfloat():
    assert pm.isfloat("7.144") is True
    assert pm.isfloat("14") is True
    assert pm.isfloat("SSB") is False


def test_getcomment_appends_tag():
    msg = "POTA VK-3024 7.195 SSB HELLO THERE".split()
    assert pm.getcomment(msg) == "HELLO THERE [APSPOT]"


def test_getcomment_no_comment():
    msg = "POTA VK-3024 7.195 SSB".split()
    assert pm.getcomment(msg) == " [APSPOT]"


def test_get_val_default():
    assert pm.get_val(["a"], 5, "NONE") == "NONE"
    assert pm.get_val(["a", "b"], 1, "NONE") == "b"


# --- message validation -----------------------------------------------------

def test_validatemessage_valid():
    assert pm.validatemessage(["POTA", "VK-3024", "7.195", "SSB", "CQCQ"]) is True


def test_validatemessage_too_short():
    result = pm.validatemessage(["POTA", "VK-3024", "7.195"])
    assert "INVALID SPOT" in result


def test_validatemessage_dots_not_spaces():
    # A single dot-delimited blob should get the "use spaces not dots" hint.
    result = pm.validatemessage(["POTA.VK-3024.7.195.SSB.CQCQ"])
    assert "SPACES NOT DOTS" in result


def test_validatemessage_bad_frequency():
    result = pm.validatemessage(["POTA", "VK-3024", "SEVEN", "SSB", "CQ"])
    assert "INVALID FREQUENCY" in result


def test_validatemessage_bad_mode():
    result = pm.validatemessage(["POTA", "VK-3024", "7.195", "BOGUS", "CQ"])
    assert "INVALID MODE" in result


def test_validatemessage_ft8_only_for_pota():
    assert pm.validatemessage(["POTA", "POTA", "7.074", "FT8", "CQ"]) is True
    assert "INVALID MODE" in pm.validatemessage(["SOTA", "VK", "7.074", "FT8", "CQ"])


# --- usage lookup -----------------------------------------------------------

def test_usage_known_target():
    assert pm.usage("USAGE POTA") == ['EXAMPLE: "! POTA VK-3024 7.195 SSB CQCQ"']


def test_usage_unknown_target():
    # This is the "USAGE SMS"-style path seen in the RF logs: not an error to fix.
    result = pm.usage("USAGE SMS")
    assert '"USAGE SMS" NOT SUPPORTED' in result[0]
    assert "SEND \"USAGE\" FOR MORE INFO" in result[1]


# --- routing (lambda_handler) ----------------------------------------------

def _event(action, message, activator=None):
    qs = {"action": action, "message": message}
    if activator is not None:
        qs["activator"] = activator
    return {"queryStringParameters": qs}


def test_handler_spots_routes_to_api(http):
    http(pm, get=FakeResponse(200, json_body={"response": ["SPOT 1: X"]}))
    result = pm.lambda_handler(_event("spots", "POTA"), None)
    assert result["statusCode"] == 200
    body = json.loads(result["body"])
    assert body["response"] == ["SPOT 1: X"]


def test_handler_spots_api_error(http):
    http(pm, get=FakeResponse(500, text=""))
    result = pm.lambda_handler(_event("spots", "POTA"), None)
    body = json.loads(result["body"])
    assert body["response"] == ["Error connecting to APSPOT API"]


def test_handler_usage_default(http):
    result = pm.lambda_handler(_event("usage", ""), None)
    body = json.loads(result["body"])
    assert body["response"][0].startswith("APSPOT USAGE INFORMATION")


def test_callapspotapi_unsupported_target():
    resp = pm.callapspotapi("spot", ["BOGUS", "REF", "7.1", "SSB", "CQ"], "VK1ABC")
    assert resp == ["Target not supported"]
