"""Tests for the sns_sms lambda: transport tagging + command routing."""
import json

import sns_sms


def _event(body, origin="+61400000000", dest="+61411111111"):
    payload = {"messageBody": body, "originationNumber": origin,
               "destinationNumber": dest}
    return {"Records": [{"Sns": {"Message": json.dumps(payload)}}]}


def _spy(monkeypatch):
    """Capture processmessage() calls and sendmessage() replies."""
    calls = {"process": [], "sent": []}
    monkeypatch.setattr(sns_sms, "processmessage",
                        lambda action, message, activator="": (
                            calls["process"].append((action, message, activator))
                            or ["OK"]))
    monkeypatch.setattr(sns_sms, "sendmessage",
                        lambda message, destination, awsNumber: (
                            calls["sent"].append(message)))
    return calls


def test_sms_tag_added_on_usage(monkeypatch):
    calls = _spy(monkeypatch)
    sns_sms.lambda_handler(_event("HELLO"), None)
    action, message, _ = calls["process"][0]
    assert action == "usage"
    assert message.endswith("[SMS]")


def test_inreach_tag(monkeypatch):
    calls = _spy(monkeypatch)
    sns_sms.lambda_handler(_event("HELLO INREACHLINK http://x"), None)
    action, message, _ = calls["process"][0]
    assert "[InReach]" in message
    assert "[SMS]" not in message


def test_spot_routing(monkeypatch):
    calls = _spy(monkeypatch)
    sns_sms.lambda_handler(_event("! POTA VK-3024 7.195 SSB CQ"), None)
    assert calls["process"][0][0] == "spot"


def test_spots_truncated_to_message_limit(monkeypatch):
    calls = {"sent": []}
    monkeypatch.setattr(sns_sms, "processmessage",
                        lambda *a, **k: [f"SPOT {i}" for i in range(10)])
    monkeypatch.setattr(sns_sms, "sendmessage",
                        lambda message, destination, awsNumber:
                        calls["sent"].append(message))
    sns_sms.lambda_handler(_event("SPOTS POTA"), None)
    assert len(calls["sent"]) == sns_sms.messageLimit
