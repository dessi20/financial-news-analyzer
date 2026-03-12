import json
import pytest
from unittest.mock import MagicMock, patch
from analyzer import call_claude, ParseError


MOCK_JSON = {
    "headline": "Fed holds rates",
    "key_takeaways": ["Rates unchanged", "Inflation at 3.1%"],
    "market_impact": "Bonds rally, equities mixed.",
    "tickers": ["TLT", "SPY"],
    "sentiment": "neutral",
}


def test_call_claude_returns_parsed_dict(monkeypatch):
    mock_client = MagicMock()
    mock_client.messages.create.return_value.content = [
        MagicMock(text=json.dumps(MOCK_JSON))
    ]
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")

    with patch("analyzer.anthropic.Anthropic", return_value=mock_client):
        result = call_claude("Some article text here.")

    assert result["headline"] == "Fed holds rates"
    assert result["tickers"] == ["TLT", "SPY"]
    assert result["sentiment"] == "neutral"


def test_call_claude_handles_fenced_json(monkeypatch):
    mock_client = MagicMock()
    fenced = f"```json\n{json.dumps(MOCK_JSON)}\n```"
    mock_client.messages.create.return_value.content = [MagicMock(text=fenced)]
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")

    with patch("analyzer.anthropic.Anthropic", return_value=mock_client):
        result = call_claude("Some article text here.")

    assert result["headline"] == "Fed holds rates"


def test_call_claude_raises_on_bad_json(monkeypatch):
    mock_client = MagicMock()
    mock_client.messages.create.return_value.content = [
        MagicMock(text="Sorry, I cannot analyze this.")
    ]
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")

    with patch("analyzer.anthropic.Anthropic", return_value=mock_client):
        with pytest.raises(ParseError):
            call_claude("Some article text here.")
