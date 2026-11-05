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


class OpenSgLawSourceStateError(OpenSgLawError):
    pass


class OpenSgLawReasonError(OpenSgLawError):
    pass


class OpenSgLawSourceRowError(OpenSgLawError):
    pass


class OpenSgLawGatewayError(OpenSgLawError):
    pass
