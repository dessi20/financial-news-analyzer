import json
import os
import pytest
from db import init_db, save_analysis, get_history, search_analyses, get_by_id


@pytest.fixture
def tmp_db(tmp_path, monkeypatch):
    db_path = str(tmp_path / "test.db")
    monkeypatch.setenv("FNA_DB_PATH", db_path)
    init_db()
    return db_path


def _sample(source="http://example.com", tickers=None, sentiment="bullish"):
    return dict(
        source=source,
        headline="Markets rally on Fed pivot",
        key_takeaways=["Fed paused rate hikes", "S&P up 2%"],
        market_impact="Short-term bullish for equities.",
        tickers=tickers or ["SPY", "QQQ"],
        sentiment=sentiment,
        raw_input="Full article text here.",
    )


def test_save_and_get_by_id(tmp_db):
    row_id = save_analysis(**_sample())
    result = get_by_id(row_id)
    assert result["headline"] == "Markets rally on Fed pivot"
    assert result["tickers"] == ["SPY", "QQQ"]
    assert result["sentiment"] == "bullish"


def test_get_history_limit(tmp_db):
    for i in range(5):
        save_analysis(**_sample(source=f"http://example.com/{i}"))
    rows = get_history(limit=3)
    assert len(rows) == 3


def test_get_history_order(tmp_db):
    save_analysis(**_sample(source="http://first.com"))
    save_analysis(**_sample(source="http://second.com"))
    rows = get_history(limit=10)
    assert rows[0]["source"] == "http://second.com"  # most recent first


def test_search_by_ticker(tmp_db):
    save_analysis(**_sample(tickers=["AAPL", "MSFT"]))
    save_analysis(**_sample(tickers=["TSLA"]))
    results = search_analyses("AAPL")
    assert len(results) == 1
    assert "AAPL" in results[0]["tickers"]


def test_search_by_headline(tmp_db):
    save_analysis(**_sample())
    results = search_analyses("Fed pivot")
    assert len(results) == 1


def test_search_no_match(tmp_db):
    save_analysis(**_sample())
    results = search_analyses("NVDA")
    assert len(results) == 0
