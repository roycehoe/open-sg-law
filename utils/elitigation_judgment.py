import re
from typing import Optional

from bs4 import BeautifulSoup

_NEUTRAL_CITATION_PATTERN = re.compile(r"^\[\d{4}\] SG[A-Z]+(?:\([A-Z]\))? ?\d+$")


def get_neutral_citation_of_tree(judgment_tree: BeautifulSoup) -> Optional[str]:
    title_element = judgment_tree.title
    if title_element is None:
        return None
    title = title_element.get_text(strip=True)
    if _NEUTRAL_CITATION_PATTERN.match(title) is None:
        return None
    return title


def get_elitigation_neutral_citation(judgment_html: str) -> Optional[str]:
    return get_neutral_citation_of_tree(BeautifulSoup(judgment_html, "html.parser"))
