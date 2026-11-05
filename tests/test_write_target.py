import pytest

from exceptions import OpenSgLawWriteTargetError
from utils.write_target import validate_can_write


def test_a_local_url_on_port_5432_is_refused() -> None:
    with pytest.raises(OpenSgLawWriteTargetError):
        validate_can_write("postgresql://user:password@localhost:5432/anything")


def test_a_local_url_on_the_hansard_replica_port_is_refused() -> None:
    with pytest.raises(OpenSgLawWriteTargetError):
        validate_can_write("postgresql://user:password@localhost:5435/anything")


def test_an_uppercase_localhost_on_the_hansard_replica_port_is_refused() -> None:
    with pytest.raises(OpenSgLawWriteTargetError):
        validate_can_write("postgresql://user:password@LOCALHOST:5435/anything")


def test_a_local_url_on_port_0_is_refused() -> None:
    with pytest.raises(OpenSgLawWriteTargetError):
        validate_can_write("postgresql://user:password@localhost:0/anything")


def test_a_local_url_without_a_port_is_refused() -> None:
    with pytest.raises(OpenSgLawWriteTargetError):
        validate_can_write("postgresql://user:password@localhost/anything")


def test_a_url_without_a_host_or_port_is_refused() -> None:
    with pytest.raises(OpenSgLawWriteTargetError):
        validate_can_write("postgresql:///anything")


def test_localhost_on_port_5436_is_allowed() -> None:
    validate_can_write("postgresql://user:password@localhost:5436/anything")


def test_the_ipv4_loopback_on_port_5436_is_allowed() -> None:
    validate_can_write("postgresql://user:password@127.0.0.1:5436/anything")


def test_the_ipv6_loopback_on_port_5436_is_allowed() -> None:
    validate_can_write("postgresql://user:password@[::1]:5436/anything")


def test_a_remote_host_is_allowed() -> None:
    validate_can_write("postgresql://user:password@db.example.org:6543/anything")
