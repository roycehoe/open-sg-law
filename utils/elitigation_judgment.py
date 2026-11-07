from typing import Optional

from bs4 import BeautifulSoup


def get_elitigation_neutral_citation(judgment_html: str) -> Optional[str]:
    citation_element = BeautifulSoup(judgment_html, "html.parser").select_one(
        ".HN-NeutralCit"
    )
    if citation_element is None:
        return None
    return citation_element.get_text(strip=True)
