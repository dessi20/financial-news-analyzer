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
