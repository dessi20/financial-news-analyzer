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
