# Financial News Analyzer CLI — Design Doc
**Date:** 2026-03-11

## Overview

A Python CLI tool that uses the Anthropic Claude API to analyze and summarize financial news articles. Users paste a URL or raw text; the tool returns a structured summary and stores all analyses in a local SQLite database for later querying.

---

## Architecture

Single-user local tool. Three files plus entry point:

```
financial-news-analyzer/
├── analyzer.py        # CLI entry point (typer commands)
├── db.py              # SQLite setup + queries
├── fetcher.py         # URL → plain text via requests + BeautifulSoup
├── requirements.txt
└── README.md
```

No package/src layout — intentionally kept flat for simplicity.

---

## Commands

| Command | Purpose |
|---|---|
| `analyze` | Analyze a URL (`--url`) or raw text (`--text`); stores + prints result |
| `history` | List last N analyses in a rich table (`--limit`, default 10) |
| `search` | Search stored analyses by keyword (ticker, headline text) |
| `show` | Display full detail of one past analysis by ID |

---

## Data Flow (`analyze`)

1. Input: `--url` → `fetcher.py` scrapes article text via `requests` + `BeautifulSoup`; or `--text` passed directly
2. Text sent to Claude (`claude-haiku-4-5-20251001`) with a structured JSON-output prompt
3. Claude returns: `{ headline, key_takeaways[], market_impact, tickers[], sentiment }`
4. Result stored in SQLite with timestamp + source
5. Rich panel printed to terminal

---

## Database Schema

Table: `analyses`

| Column | Type | Notes |
|---|---|---|
| `id` | INTEGER PK | auto-increment |
| `created_at` | TEXT | ISO 8601 timestamp |
| `source` | TEXT | URL or "raw text" |
| `headline` | TEXT | extracted by Claude |
| `key_takeaways` | TEXT | JSON array |
| `market_impact` | TEXT | paragraph string |
| `tickers` | TEXT | JSON array e.g. `["AAPL","MSFT"]` |
| `sentiment` | TEXT | bullish / bearish / neutral |
| `raw_input` | TEXT | original article text |

---

## Terminal Output (analyze)

```
╭─ Analysis #42 · 2026-03-11 ──────────────────────────╮
│ Headline:  Fed signals rate pause amid inflation data  │
│ Sentiment: Bearish                                     │
│ Tickers:   SPY, TLT, GLD                              │
├───────────────────────────────────────────────────────┤
│ Key Takeaways                                          │
│  • Fed held rates at 5.25%                            │
│  • Inflation came in at 3.1%, above expectations      │
│ Market Impact                                          │
│  • Bond prices likely to fall short-term...           │
╰───────────────────────────────────────────────────────╯
```

---

## Error Handling

- **URL fetch fails** (blocked, timeout, 404): print clear error, suggest `--text` fallback
- **Claude API error** (rate limit, auth): surface API message, hint to check `ANTHROPIC_API_KEY`
- **API key missing**: check at startup, print actionable message and exit
- **Malformed Claude JSON response**: store/display raw text with a warning
- **Empty article text**: warn before sending to Claude

API key sourced from `ANTHROPIC_API_KEY` environment variable — no `.env` file.

---

## Dependencies

- `anthropic` — Claude API client
- `typer` — CLI framework
- `rich` — terminal styling (panels, tables)
- `requests` — HTTP fetching
- `beautifulsoup4` — HTML parsing
- `lxml` — BS4 parser backend
