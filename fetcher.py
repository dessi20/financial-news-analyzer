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
