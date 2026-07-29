from __future__ import annotations

import pytest

from vlm_radar import http


def test_build_url_appends_and_expands_sequences():
    assert http.build_url("https://e.com/a", {"q": "x y", "n": 2}) == "https://e.com/a?q=x+y&n=2"
    assert http.build_url("https://e.com/a?p=1", {"q": "x"}) == "https://e.com/a?p=1&q=x"
    assert http.build_url("https://e.com/a", {"t": ["a", "b"]}) == "https://e.com/a?t=a&t=b"
    assert http.build_url("https://e.com/a", {"skip": None}) == "https://e.com/a"
    assert http.build_url("https://e.com/a", None) == "https://e.com/a"


def test_errors_never_echo_credentials(monkeypatch):
    def explode(*args, **kwargs):
        raise TimeoutError("boom")

    monkeypatch.setattr(http.urllib.request, "urlopen", explode)
    with pytest.raises(http.HttpError) as error:
        http.get_text(
            "https://api.example.com/search",
            params={"query": "vlm", "api_key": "super-secret", "token": "abc"},
            retries=1,
        )
    message = str(error.value)
    assert "super-secret" not in message
    assert "abc" not in message
    assert "REDACTED" in message
    assert "query=vlm" in message


def test_retries_stop_at_the_configured_limit(monkeypatch):
    calls = {"count": 0}

    def explode(*args, **kwargs):
        calls["count"] += 1
        raise TimeoutError("boom")

    monkeypatch.setattr(http.urllib.request, "urlopen", explode)
    monkeypatch.setattr(http.time, "sleep", lambda seconds: None)
    with pytest.raises(http.HttpError):
        http.get_text("https://api.example.com/x", retries=3)
    assert calls["count"] == 3


def test_github_headers_include_a_token_only_when_present(monkeypatch):
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    assert "Authorization" not in http.github_headers()

    monkeypatch.setenv("GITHUB_TOKEN", "ghp_example")
    assert http.github_headers()["Authorization"] == "Bearer ghp_example"


def test_user_agent_identifies_the_project():
    assert http.USER_AGENT.startswith("vlm-radar/")
