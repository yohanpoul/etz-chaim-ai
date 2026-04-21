"""Extract clean text from Peterson's Lemegeton HTML files.
HTML 2.0 source has unclosed <p> tags causing catastrophic nesting.
Solution: add newlines before block tags via replace_with, then get_text once."""
from bs4 import BeautifulSoup, NavigableString
from pathlib import Path
import re

HERE = Path(__file__).parent
FILES = ["goetia", "theurgia", "paulina", "almadel", "notoria"]
BLOCK_NAMES = {"h1", "h2", "h3", "h4", "h5", "p", "li", "br", "tr", "div", "blockquote"}

def extract(html_path: Path) -> str:
    raw = html_path.read_bytes()
    try:
        html = raw.decode("utf-8")
    except UnicodeDecodeError:
        html = raw.decode("latin-1")
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "meta", "link", "head"]):
        tag.decompose()
    for tag in soup.find_all(list(BLOCK_NAMES)):
        tag.insert_before(NavigableString("\n"))
        if tag.name.startswith("h"):
            level = int(tag.name[1])
            tag.insert_before(NavigableString("\n" + "#" * level + " "))
            tag.insert_after(NavigableString("\n"))
        elif tag.name == "li":
            tag.insert_before(NavigableString("- "))
    text = soup.get_text(separator=" ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r" *\n *", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()

for name in FILES:
    html_path = HERE / f"{name}.html"
    if not html_path.exists():
        print(f"MISSING: {name}")
        continue
    txt = extract(html_path)
    out_path = HERE / f"{name}.txt"
    out_path.write_text(txt, encoding="utf-8")
    print(f"{name:10} {len(txt):>7} chars  {out_path.name}")
