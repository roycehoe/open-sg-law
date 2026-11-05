from enums import SourceName

SITE_ROLE_NAME = "open_sg_law_site"

TABLE_NAME_TO_SOURCES: dict[str, frozenset[SourceName]] = {
    "source": frozenset(),
    "legislation": frozenset({SourceName.SSO, SourceName.INTERNET_ARCHIVE}),
    "legislation_version": frozenset({SourceName.SSO, SourceName.INTERNET_ARCHIVE}),
    "legislation_section": frozenset({SourceName.SSO, SourceName.INTERNET_ARCHIVE}),
    "legislation_alias": frozenset({SourceName.SSO, SourceName.INTERNET_ARCHIVE}),
    "bill": frozenset({SourceName.OPENHANSARD_LINKS}),
    "bill_report": frozenset({SourceName.OPENHANSARD_LINKS}),
    "act_history_entry": frozenset({SourceName.OPENHANSARD_LINKS, SourceName.SSO}),
}


def get_table_names_to_grant(published_sources: frozenset[SourceName]) -> list[str]:
    return sorted(
        table_name
        for table_name, sources in TABLE_NAME_TO_SOURCES.items()
        if sources.issubset(published_sources)
    )
