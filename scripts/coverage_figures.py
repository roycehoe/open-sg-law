import argparse
from pathlib import Path
from typing import Optional

from sqlmodel import Session

from database.init import engine
from exceptions import OpenSgLawWriteCheckError
from logs import logger
from populate.coverage_figures import CoverageFigures, get_coverage_figures

_PERCENT = 100
_NO_SHARE = "n/a"
_PARKED_LINE = "Judgment and subsidiary legislation figures wait for their parked steps"


def _get_percent(share: Optional[float]) -> str:
    if share is None:
        return _NO_SHARE
    return f"{_PERCENT * share:.2f}%"


def _build_lines(coverage_figures: CoverageFigures) -> list[str]:
    lines = [
        f"Headline, current Acts the site can read section by section: {coverage_figures.readable_current_legislation_count} of {coverage_figures.current_legislation_count} ({_get_percent(coverage_figures.readable_current_legislation_share)})",
        f"Current Acts with a parsed newest version: {coverage_figures.parsed_current_legislation_count}",
        f"Site role reads legislation, versions and sections: {'yes' if coverage_figures.is_section_text_readable else 'no'}",
        f"Acts listed: {coverage_figures.legislation_count}",
    ]
    lines.extend(
        f"Acts with a version from {source_count.source}: {source_count.legislation_count}"
        for source_count in coverage_figures.source_counts
    )
    lines.append(
        f"Acts with no version: {coverage_figures.legislation_without_version_count}"
    )
    lines.extend(
        f"Newest versions printed in {version_year_count.version_year}: {version_year_count.version_count}"
        for version_year_count in coverage_figures.newest_version_year_counts
    )
    lines.append(
        f"Newest versions with no printed date: {coverage_figures.newest_version_without_date_count}"
    )
    lines.append(f"Versions parsed: {coverage_figures.parsed_version_count}")
    lines.append(f"Versions not parsed: {coverage_figures.unparsed_version_count}")
    lines.extend(
        f"Sections of kind {section_kind_count.kind}: {section_kind_count.section_count}"
        for section_kind_count in coverage_figures.section_kind_counts
    )
    lines.append(f"Repealed sections: {coverage_figures.repealed_section_count}")
    lines.append(
        f"Sections on image pages: {coverage_figures.image_page_section_count}"
    )
    lines.append(
        f"Text share, all parsed versions: {_get_percent(coverage_figures.overall_text_share)}"
    )
    lines.append(
        f"Versions under 99% text share: {coverage_figures.versions_under_high_share_count}"
    )
    lines.append(
        f"Versions under 90% text share: {coverage_figures.versions_under_low_share_count}"
    )
    lines.extend(
        f"Lowest text share: {version_text_share.sso_code} {_get_percent(version_text_share.text_share)}"
        for version_text_share in coverage_figures.lowest_text_shares
    )
    lines.append(f"Bills: {coverage_figures.bill_count}")
    lines.append(f"History entries: {coverage_figures.history_entry_count}")
    lines.append(
        f"History entries linked to a bill: {coverage_figures.linked_history_entry_count}"
    )
    lines.append(_PARKED_LINE)
    return lines


def coverage_figures(output: Optional[Path]) -> None:
    with Session(engine) as session:
        lines = _build_lines(get_coverage_figures(session))
    for line in lines:
        logger.info(line)
    if output is None:
        return
    output.parent.mkdir(parents=True, exist_ok=True)
    try:
        with output.open("x") as output_file:
            output_file.write("\n".join(lines) + "\n")
    except FileExistsError as error:
        raise OpenSgLawWriteCheckError(f"{output} exists") from error


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="The coverage figures for legislation versions, sections and Hansard links"
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="also write the lines to this new file, such as docs/figures/2026-11-05-first-write.txt",
    )
    coverage_figures(parser.parse_args().output)
