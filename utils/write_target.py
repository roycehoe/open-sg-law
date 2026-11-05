from sqlalchemy.engine import make_url

from exceptions import OpenSgLawWriteTargetError

_LOCAL_HOSTS = frozenset({"localhost", "127.0.0.1", "::1"})
_LOCAL_PORT = 5436


def validate_can_write(database_url: str) -> None:
    url = make_url(database_url)
    if url.host is not None and url.host.lower() not in _LOCAL_HOSTS:
        return
    if url.port != _LOCAL_PORT:
        raise OpenSgLawWriteTargetError(
            f"Refusing to write: a local database must be on port {_LOCAL_PORT}, not {url.port}"
        )
