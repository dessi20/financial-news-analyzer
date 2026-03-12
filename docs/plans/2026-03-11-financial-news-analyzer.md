# Financial News Analyzer CLI Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a Python CLI tool using Anthropic Claude to analyze financial news articles (URL or raw text) with structured output and SQLite storage for past analyses.

**Architecture:** Three source files (`db.py`, `fetcher.py`, `analyzer.py`) plus a `tests/` directory. `analyzer.py` is the typer CLI entry point; it delegates URL fetching to `fetcher.py` and all database operations to `db.py`. Claude (`claude-haiku-4-5-20251001`) returns structured JSON that is stored and rendered via `rich`.

**Tech Stack:** `anthropic`, `typer[all]`, `rich`, `requests`, `beautifulsoup4`, `lxml`, `pytest`, `pytest-mock`, Python's built-in `sqlite3`.

> **Note:** User manages all git commits — do NOT run any `git commit` commands.

---

### Task 1: Project Setup

**Files:**
- Create: `requirements.txt`
- Create: `tests/__init__.py`

**Step 1: Write `requirements.txt`**

```
anthropic>=0.40.0
typer[all]>=0.12.0
rich>=13.0.0
requests>=2.32.0
beautifulsoup4>=4.12.0
lxml>=5.0.0
pytest>=8.0.0
pytest-mock>=3.14.0
```

**Step 2: Create empty test package**

Create `tests/__init__.py` as an empty file.

**Step 3: Install dependencies**

```bash
pip install -r requirements.txt
```

Expected: all packages install without errors.

**Step 4: Verify install**

```bash
python -c "import anthropic, typer, rich, requests, bs4; print('OK')"
```

Expected: prints `OK`.

---

### Task 2: Database Layer (`db.py`)

**Files:**
- Create: `db.py`
- Create: `tests/test_db.py`

**Step 1: Write the failing tests**

Create `tests/test_db.py`:

```python
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
```

**Step 2: Run tests to verify they fail**

```bash
pytest tests/test_db.py -v
```

Expected: `ModuleNotFoundError: No module named 'db'`

**Step 3: Implement `db.py`**

```python
import json
import os
import sqlite3
from typing import Any


def _db_path() -> str:
    return os.environ.get("FNA_DB_PATH", "analyses.db")


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(_db_path())
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with _connect() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS analyses (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at  TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%S', 'now')),
                source      TEXT    NOT NULL,
                headline    TEXT    NOT NULL,
                key_takeaways TEXT  NOT NULL,
                market_impact TEXT  NOT NULL,
                tickers     TEXT    NOT NULL,
                sentiment   TEXT    NOT NULL,
                raw_input   TEXT    NOT NULL
            )
        """)


def save_analysis(
    source: str,
    headline: str,
    key_takeaways: list[str],
    market_impact: str,
    tickers: list[str],
    sentiment: str,
    raw_input: str,
) -> int:
    with _connect() as conn:
        cursor = conn.execute(
            """
            INSERT INTO analyses
                (source, headline, key_takeaways, market_impact, tickers, sentiment, raw_input)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                source,
                headline,
                json.dumps(key_takeaways),
                market_impact,
                json.dumps(tickers),
                sentiment,
                raw_input,
            ),
        )
        return cursor.lastrowid


def _deserialize(row: sqlite3.Row) -> dict[str, Any]:
    d = dict(row)
    d["key_takeaways"] = json.loads(d["key_takeaways"])
    d["tickers"] = json.loads(d["tickers"])
    return d


def get_history(limit: int = 10) -> list[dict[str, Any]]:
    with _connect() as conn:
        rows = conn.execute(
            "SELECT * FROM analyses ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
    return [_deserialize(r) for r in rows]


def search_analyses(keyword: str) -> list[dict[str, Any]]:
    pattern = f"%{keyword}%"
    with _connect() as conn:
        rows = conn.execute(
            """
            SELECT * FROM analyses
            WHERE headline LIKE ?
               OR tickers   LIKE ?
               OR market_impact LIKE ?
            ORDER BY id DESC
            """,
            (pattern, pattern, pattern),
        ).fetchall()
    return [_deserialize(r) for r in rows]


def get_by_id(row_id: int) -> dict[str, Any] | None:
    with _connect() as conn:
        row = conn.execute(
            "SELECT * FROM analyses WHERE id = ?", (row_id,)
        ).fetchone()
    return _deserialize(row) if row else None
```

**Step 4: Run tests to verify they pass**

```bash
pytest tests/test_db.py -v
```

Expected: all 6 tests PASS.

---

### Task 3: URL Fetcher (`fetcher.py`)

**Files:**
- Create: `fetcher.py`
- Create: `tests/test_fetcher.py`

**Step 1: Write the failing tests**

Create `tests/test_fetcher.py`:

```python
import pytest
from fetcher import fetch_text, FetchError


def test_fetch_extracts_paragraphs(requests_mock):
    html = """
    <html><body>
      <article>
        <p>The Federal Reserve held rates steady.</p>
        <p>Markets reacted positively to the news.</p>
      </article>
    </body></html>
    """
    requests_mock.get("http://example.com/article", text=html)
    text = fetch_text("http://example.com/article")
    assert "Federal Reserve" in text
    assert "Markets reacted" in text


def test_fetch_raises_on_http_error(requests_mock):
    requests_mock.get("http://example.com/404", status_code=404)
    with pytest.raises(FetchError, match="404"):
        fetch_text("http://example.com/404")


def test_fetch_raises_on_empty_content(requests_mock):
    requests_mock.get("http://example.com/empty", text="<html><body></body></html>")
    with pytest.raises(FetchError, match="No readable text"):
        fetch_text("http://example.com/empty")
```

**Step 2: Install `requests-mock` for tests**

```bash
pip install requests-mock
```

Add `requests-mock>=1.11.0` to `requirements.txt`.

**Step 3: Run tests to verify they fail**

```bash
pytest tests/test_fetcher.py -v
```

Expected: `ModuleNotFoundError: No module named 'fetcher'`

**Step 4: Implement `fetcher.py`**

```python
import requests
from bs4 import BeautifulSoup


class FetchError(Exception):
    pass


def fetch_text(url: str, timeout: int = 15) -> str:
    try:
        response = requests.get(
            url,
            timeout=timeout,
            headers={"User-Agent": "Mozilla/5.0 (financial-news-analyzer/1.0)"},
        )
    except requests.RequestException as exc:
        raise FetchError(f"Request failed: {exc}") from exc

    if not response.ok:
        raise FetchError(f"HTTP {response.status_code} for {url}")

    soup = BeautifulSoup(response.text, "lxml")

    # Remove noise
    for tag in soup(["script", "style", "nav", "header", "footer", "aside"]):
        tag.decompose()

    paragraphs = [p.get_text(strip=True) for p in soup.find_all("p") if p.get_text(strip=True)]

    if not paragraphs:
        raise FetchError("No readable text found. Try pasting the article text with --text.")

    return "\n\n".join(paragraphs)
```

**Step 5: Run tests to verify they pass**

```bash
pytest tests/test_fetcher.py -v
```

Expected: all 3 tests PASS.

---

### Task 4: Claude API Integration (analysis logic)

**Files:**
- Create: `tests/test_analyzer_logic.py`
- Modify: `analyzer.py` (create it with just the `call_claude` function for now)

**Step 1: Write the failing tests**

Create `tests/test_analyzer_logic.py`:

```python
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


def test_call_claude_raises_on_bad_json(monkeypatch):
    mock_client = MagicMock()
    mock_client.messages.create.return_value.content = [
        MagicMock(text="Sorry, I cannot analyze this.")
    ]
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")

    with patch("analyzer.anthropic.Anthropic", return_value=mock_client):
        with pytest.raises(ParseError):
            call_claude("Some article text here.")
```

**Step 2: Run tests to verify they fail**

```bash
pytest tests/test_analyzer_logic.py -v
```

Expected: `ModuleNotFoundError: No module named 'analyzer'`

**Step 3: Create `analyzer.py` with `call_claude` only**

```python
import json
import os
import sys
import anthropic
import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich import box

import db
from fetcher import fetch_text, FetchError

app = typer.Typer(help="Financial news analyzer powered by Claude.")
console = Console()

MODEL = "claude-haiku-4-5-20251001"

SYSTEM_PROMPT = """\
You are a financial analyst assistant. Analyze the provided news article and respond ONLY with valid JSON matching this exact schema:
{
  "headline": "<concise article headline>",
  "key_takeaways": ["<point 1>", "<point 2>", "<point 3>"],
  "market_impact": "<1-2 sentence assessment of potential market impact>",
  "tickers": ["<TICKER1>", "<TICKER2>"],
  "sentiment": "<bullish|bearish|neutral>"
}
Do not include any text outside the JSON object."""


class ParseError(Exception):
    pass


def call_claude(text: str) -> dict:
    client = anthropic.Anthropic()
    message = client.messages.create(
        model=MODEL,
        max_tokens=1024,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": f"Article:\n\n{text}"}],
    )
    raw = message.content[0].text
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ParseError(f"Claude returned non-JSON response: {raw[:200]}") from exc
```

**Step 4: Run tests to verify they pass**

```bash
pytest tests/test_analyzer_logic.py -v
```

Expected: all 2 tests PASS.

---

### Task 5: `analyze` Command

**Files:**
- Modify: `analyzer.py` (add `analyze` command + `_render_analysis` helper)

**Step 1: Add `_render_analysis` helper and `analyze` command to `analyzer.py`**

Append after the `call_claude` function:

```python
SENTIMENT_COLORS = {"bullish": "green", "bearish": "red", "neutral": "yellow"}


def _render_analysis(row: dict) -> None:
    color = SENTIMENT_COLORS.get(row["sentiment"].lower(), "white")
    tickers_str = "  ".join(f"[bold cyan]{t}[/bold cyan]" for t in row["tickers"]) or "—"

    takeaways = "\n".join(f"  • {t}" for t in row["key_takeaways"])

    body = (
        f"[bold]Headline:[/bold]  {row['headline']}\n"
        f"[bold]Sentiment:[/bold] [{color}]{row['sentiment'].capitalize()}[/{color}]\n"
        f"[bold]Tickers:[/bold]   {tickers_str}\n"
        f"[bold]Source:[/bold]    {row['source']}\n\n"
        f"[bold]Key Takeaways[/bold]\n{takeaways}\n\n"
        f"[bold]Market Impact[/bold]\n  {row['market_impact']}"
    )
    title = f"Analysis #{row['id']} · {row['created_at'][:10]}"
    console.print(Panel(body, title=title, border_style="blue"))


@app.command()
def analyze(
    url: str = typer.Option(None, "--url", "-u", help="URL of the news article to fetch"),
    text: str = typer.Option(None, "--text", "-t", help="Raw article text to analyze"),
):
    """Analyze a financial news article from a URL or raw text."""
    if not url and not text:
        console.print("[red]Provide --url or --text.[/red]")
        raise typer.Exit(1)
    if url and text:
        console.print("[red]Provide only one of --url or --text, not both.[/red]")
        raise typer.Exit(1)

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        console.print("[red]ANTHROPIC_API_KEY environment variable is not set.[/red]")
        raise typer.Exit(1)

    source = url or "raw text"

    if url:
        with console.status("Fetching article..."):
            try:
                article_text = fetch_text(url)
            except FetchError as exc:
                console.print(f"[red]Fetch failed:[/red] {exc}")
                raise typer.Exit(1)
    else:
        article_text = text

    with console.status("Analyzing with Claude..."):
        try:
            result = call_claude(article_text)
        except ParseError as exc:
            console.print(f"[yellow]Warning:[/yellow] {exc}")
            console.print(article_text[:500])
            raise typer.Exit(1)
        except anthropic.APIError as exc:
            console.print(f"[red]Claude API error:[/red] {exc}")
            raise typer.Exit(1)

    db.init_db()
    row_id = db.save_analysis(
        source=source,
        headline=result["headline"],
        key_takeaways=result.get("key_takeaways", []),
        market_impact=result.get("market_impact", ""),
        tickers=result.get("tickers", []),
        sentiment=result.get("sentiment", "neutral"),
        raw_input=article_text,
    )
    row = db.get_by_id(row_id)
    _render_analysis(row)
```

**Step 2: Smoke-test the command (requires real API key)**

```bash
python analyzer.py analyze --text "Apple reported record Q1 earnings, beating estimates by 15%. Revenue hit $130B driven by iPhone sales in emerging markets. CEO Tim Cook cited strong demand in India."
```

Expected: a rich panel with headline, tickers, sentiment, key takeaways, market impact printed.

---

### Task 6: `history` Command

**Files:**
- Modify: `analyzer.py` (add `history` command)

**Step 1: Add `history` command**

```python
@app.command()
def history(
    limit: int = typer.Option(10, "--limit", "-n", help="Number of past analyses to show"),
):
    """List recent analyses."""
    db.init_db()
    rows = db.get_history(limit=limit)
    if not rows:
        console.print("[yellow]No analyses found. Run 'analyze' first.[/yellow]")
        return

    table = Table(title=f"Last {len(rows)} Analyses", box=box.ROUNDED)
    table.add_column("ID", style="dim", width=4)
    table.add_column("Date", width=10)
    table.add_column("Headline", no_wrap=False)
    table.add_column("Tickers", width=20)
    table.add_column("Sentiment", width=10)
    table.add_column("Source", no_wrap=False)

    for row in rows:
        color = SENTIMENT_COLORS.get(row["sentiment"].lower(), "white")
        table.add_row(
            str(row["id"]),
            row["created_at"][:10],
            row["headline"],
            ", ".join(row["tickers"]),
            f"[{color}]{row['sentiment']}[/{color}]",
            row["source"][:50],
        )
    console.print(table)
```

**Step 2: Smoke-test**

```bash
python analyzer.py history --limit 5
```

Expected: a rich table of past analyses (or the "No analyses found" message).

---

### Task 7: `search` Command

**Files:**
- Modify: `analyzer.py` (add `search` command)

**Step 1: Add `search` command**

```python
@app.command()
def search(
    keyword: str = typer.Argument(..., help="Ticker symbol or keyword to search"),
):
    """Search past analyses by ticker or keyword."""
    db.init_db()
    rows = db.search_analyses(keyword)
    if not rows:
        console.print(f"[yellow]No analyses found matching '{keyword}'.[/yellow]")
        return

    table = Table(title=f"Search results for '{keyword}'", box=box.ROUNDED)
    table.add_column("ID", style="dim", width=4)
    table.add_column("Date", width=10)
    table.add_column("Headline", no_wrap=False)
    table.add_column("Tickers", width=20)
    table.add_column("Sentiment", width=10)

    for row in rows:
        color = SENTIMENT_COLORS.get(row["sentiment"].lower(), "white")
        table.add_row(
            str(row["id"]),
            row["created_at"][:10],
            row["headline"],
            ", ".join(row["tickers"]),
            f"[{color}]{row['sentiment']}[/{color}]",
        )
    console.print(table)
```

**Step 2: Smoke-test**

```bash
python analyzer.py search AAPL
python analyzer.py search "Fed"
```

Expected: matching analyses in a table, or a "no results" message.

---

### Task 8: `show` Command

**Files:**
- Modify: `analyzer.py` (add `show` command + `if __name__ == "__main__"` block)

**Step 1: Add `show` command and entry point**

```python
@app.command()
def show(
    analysis_id: int = typer.Argument(..., help="ID of the analysis to display"),
):
    """Show full detail of a past analysis by ID."""
    db.init_db()
    row = db.get_by_id(analysis_id)
    if not row:
        console.print(f"[red]No analysis found with ID {analysis_id}.[/red]")
        raise typer.Exit(1)
    _render_analysis(row)
    console.print(Panel(row["raw_input"][:1000] + ("..." if len(row["raw_input"]) > 1000 else ""),
                        title="Original Text", border_style="dim"))


if __name__ == "__main__":
    app()
```

**Step 2: Smoke-test**

```bash
python analyzer.py show 1
```

Expected: full analysis panel plus truncated original article text.

**Step 3: Verify all commands work end-to-end**

```bash
python analyzer.py --help
python analyzer.py analyze --help
python analyzer.py history --help
python analyzer.py search --help
python analyzer.py show --help
```

Expected: help text for each command.

---

### Task 9: Full Test Suite Verification

**Step 1: Run all tests**

```bash
pytest tests/ -v
```

Expected: all tests pass.

**Step 2: Check for import issues in the full module**

```bash
python -c "import analyzer; print('OK')"
```

Expected: prints `OK` (no import errors at module load time).

---

### Task 10: README

**Files:**
- Modify: `README.md`

**Step 1: Write final README**

Replace the current `README.md` content with:

```markdown
# Financial News Analyzer

A Python CLI tool that uses the Anthropic Claude API to analyze financial news articles. Paste a URL or raw text and get structured summaries with key takeaways, market impact, and relevant ticker symbols. All analyses are stored locally in SQLite.

## Setup

**1. Install dependencies**
```bash
pip install -r requirements.txt
```

**2. Set your Anthropic API key**
```bash
export ANTHROPIC_API_KEY="your-key-here"
```

## Usage

### Analyze an article from a URL
```bash
python analyzer.py analyze --url "https://example.com/article"
```

### Analyze pasted text
```bash
python analyzer.py analyze --text "Apple reported record earnings..."
```

### View recent analyses
```bash
python analyzer.py history
python analyzer.py history --limit 20
```

### Search past analyses
```bash
python analyzer.py search AAPL
python analyzer.py search "Federal Reserve"
```

### Show a specific analysis by ID
```bash
python analyzer.py show 42
```

## Output Example

```
╭─ Analysis #42 · 2026-03-11 ──────────────────────────────╮
│ Headline:  Fed signals rate pause amid inflation data      │
│ Sentiment: Bearish                                         │
│ Tickers:   SPY  TLT  GLD                                  │
│ Source:    https://example.com/article                     │
│                                                            │
│ Key Takeaways                                              │
│   • Fed held rates at 5.25%                               │
│   • Inflation came in at 3.1%, above expectations         │
│   • Markets sold off on the news                          │
│                                                            │
│ Market Impact                                              │
│   Bond prices likely to fall short-term as traders        │
│   reprice rate-cut expectations.                          │
╰────────────────────────────────────────────────────────────╯
```

## Database

Analyses are stored in `analyses.db` in the project directory. Override the path with:
```bash
export FNA_DB_PATH="/path/to/custom.db"
```
```

---

## Execution Checklist

- [ ] Task 1: Project setup (requirements.txt, test package)
- [ ] Task 2: `db.py` with full test coverage
- [ ] Task 3: `fetcher.py` with full test coverage
- [ ] Task 4: `analyzer.py` — `call_claude` function with tests
- [ ] Task 5: `analyze` command
- [ ] Task 6: `history` command
- [ ] Task 7: `search` command
- [ ] Task 8: `show` command + entry point
- [ ] Task 9: Full test suite passes
- [ ] Task 10: README updated
