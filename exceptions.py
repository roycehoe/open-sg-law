class OpenSgLawError(Exception):
    pass


class OpenSgLawTestGuardError(OpenSgLawError):
    pass


class OpenSgLawWriteTargetError(OpenSgLawError):
    pass


class OpenSgLawHarvestRunError(OpenSgLawError):
    pass


class OpenSgLawWriteCheckError(OpenSgLawError):
    pass
