from enum import StrEnum


class SourceName(StrEnum):
    SSO = "SSO"
    INTERNET_ARCHIVE = "INTERNET_ARCHIVE"
    EGAZETTE = "EGAZETTE"
    DATA_GOV_SG = "DATA_GOV_SG"
    ELITIGATION = "ELITIGATION"
    OPENHANSARD_LINKS = "OPENHANSARD_LINKS"


class PublishStatus(StrEnum):
    PUBLISHED = "PUBLISHED"
    UNPUBLISHED = "UNPUBLISHED"


class SsoAccessState(StrEnum):
    UNTESTED = "UNTESTED"
    SERVING = "SERVING"
    CHALLENGED = "CHALLENGED"


class HarvestRunStatus(StrEnum):
    RUNNING = "RUNNING"
    SUCCEEDED = "SUCCEEDED"
    HALTED = "HALTED"
    FAILED = "FAILED"


class ResponseKind(StrEnum):
    LISTING_PAGE = "LISTING_PAGE"
    DOCUMENT = "DOCUMENT"
    CDX_ANSWER = "CDX_ANSWER"
    ROBOTS_FILE = "ROBOTS_FILE"


class SsoAnswer(StrEnum):
    EXPECTED = "EXPECTED"
    FAILURE = "FAILURE"
