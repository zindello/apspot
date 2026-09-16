"""Tests for the sns_email lambda: Winlink-only spotting + routing."""
import json

import sns_email


def _event(subject, mail_from, mail_to="spot@apspot.radio"):
    payload = {"mail": {"commonHeaders": {
        "from": [mail_from], "to": [mail_to], "subject": subject}}}
    return {"Records": [{"Sns": {"Message": json.dumps(payload)}}]}


def _spy(monkeypatch):
    calls = {"process": [], "sent": []}
    monkeypatch.setattr(sns_email, "processmessage",
                        lambda action, message, activator="": (
                            calls["process"].append((action, message, activator))
                            or ["OK"]))
    monkeypatch.setattr(sns_email, "sendmessage",
                        lambda message, destination, source:
                        calls["sent"].append(message))
    return calls


def test_spot_from_winlink_allowed(monkeypatch):
    calls = _spy(monkeypatch)
    sns_email.lambda_handler(
        _event("! POTA VK-3024 7.195 SSB CQ", "VK1ABC@winlink.org"), None)
    assert calls["process"][0][0] == "spot"
    assert "[WL]" in calls["process"][0][1]
    assert calls["process"][0][2] == "VK1ABC"


def test_spot_from_non_winlink_rejected(monkeypatch):
    calls = _spy(monkeypatch)
    sns_email.lambda_handler(
        _event("! POTA VK-3024 7.195 SSB CQ", "VK1ABC@gmail.com"), None)
    # No spot processed; a rejection message is sent instead.
    assert calls["process"] == []
    assert any("Winlink" in line for line in calls["sent"][0])


def test_usage_from_any_sender(monkeypatch):
    calls = _spy(monkeypatch)
    sns_email.lambda_handler(_event("HELLO", "someone@gmail.com"), None)
    assert calls["process"][0][0] == "usage"
