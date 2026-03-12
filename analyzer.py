import json
import os
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

MODEL = os.environ.get("FNA_MODEL", "claude-haiku-4-5-20251001")

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
    if not message.content:
        raise ParseError("Claude returned an empty response.")
    raw = message.content[0].text.strip()
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[-1]  # drop opening ```json line
        raw = raw.rsplit("```", 1)[0].strip()  # drop closing ```
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ParseError(f"Claude returned non-JSON response: {raw[:200]}") from exc


SENTIMENT_COLORS = {"bullish": "green", "bearish": "red", "neutral": "yellow"}


def _render_analysis(row: dict) -> None:
    sentiment = row.get("sentiment") or "neutral"
    color = SENTIMENT_COLORS.get(sentiment.lower(), "white")
    tickers_str = "  ".join(f"[bold cyan]{t}[/bold cyan]" for t in row["tickers"]) or "—"

    takeaways = "\n".join(f"  • {t}" for t in row["key_takeaways"])

    body = (
        f"[bold]Headline:[/bold]  {row['headline']}\n"
        f"[bold]Sentiment:[/bold] [{color}]{sentiment.capitalize()}[/{color}]\n"
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
        except (anthropic.APIError, anthropic.APIConnectionError) as exc:
            console.print(f"[red]Claude API error:[/red] {exc}")
            raise typer.Exit(1)

    db.init_db()
    row_id = db.save_analysis(
        source=source,
        headline=result.get("headline", ""),
        key_takeaways=result.get("key_takeaways", []),
        market_impact=result.get("market_impact", ""),
        tickers=result.get("tickers", []),
        sentiment=result.get("sentiment", "neutral"),
        raw_input=article_text,
    )
    row = db.get_by_id(row_id)
    _render_analysis(row)


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
        sentiment = row.get("sentiment") or "neutral"
        color = SENTIMENT_COLORS.get(sentiment.lower(), "white")
        table.add_row(
            str(row["id"]),
            row["created_at"][:10],
            row["headline"],
            ", ".join(row["tickers"]),
            f"[{color}]{sentiment}[/{color}]",
            row["source"][:50],
        )
    console.print(table)


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
        sentiment = row.get("sentiment") or "neutral"
        color = SENTIMENT_COLORS.get(sentiment.lower(), "white")
        table.add_row(
            str(row["id"]),
            row["created_at"][:10],
            row["headline"],
            ", ".join(row["tickers"]),
            f"[{color}]{sentiment}[/{color}]",
        )
    console.print(table)


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
