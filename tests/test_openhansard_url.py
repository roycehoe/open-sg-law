from utils.openhansard_url import get_openhansard_report_url


def test_a_report_id_loses_its_trailing_hash() -> None:
    assert (
        get_openhansard_report_url("00004663-WA.00000937-WA_1#")
        == "https://openhansard.sg/reports/00004663-WA.00000937-WA_1"
    )


def test_an_inner_hash_is_percent_encoded() -> None:
    assert (
        get_openhansard_report_url(
            "00069034-ZZ.00050649-ZZ_1#id006_19611130_S0005_T00052-motion#"
        )
        == "https://openhansard.sg/reports/00069034-ZZ.00050649-ZZ_1%23id006_19611130_S0005_T00052-motion"
    )


def test_every_trailing_hash_is_removed() -> None:
    assert (
        get_openhansard_report_url("00004663-WA.00000937-WA_1##")
        == "https://openhansard.sg/reports/00004663-WA.00000937-WA_1"
    )
