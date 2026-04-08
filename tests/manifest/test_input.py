import pytest
from unittest.mock import MagicMock
from pydantic import ValidationError
from jihanki.pipeline.input import Input
from jihanki.pipeline.schema import InputSchema


def test_empty_input():
    s = InputSchema()
    inp = Input(s)
    assert inp.environment_variables == {}
    assert inp.files == []


def test_field_environment_variable():
    s = InputSchema(
        environment={
            "MY_VAR": {"source": "field", "fieldname": "my_var"},
        },
    )
    inp = Input(s)
    assert "MY_VAR" in inp.environment_variables
    assert inp.get_env_variables({"my_var": "hello"}) == {"MY_VAR": "hello"}


def test_static_environment_variable():
    s = InputSchema(
        environment={
            "FIXED": {"source": "static", "value": "constant"},
        },
    )
    inp = Input(s)
    assert inp.get_env_variables({}) == {"FIXED": "constant"}


def test_mixed_environment_variables():
    s = InputSchema(
        environment={
            "FROM_REQ": {"source": "field", "fieldname": "req_field"},
            "STATIC": {"source": "static", "value": "val"},
        },
    )
    inp = Input(s)
    result = inp.get_env_variables({"req_field": "dynamic"})
    assert result == {"FROM_REQ": "dynamic", "STATIC": "val"}


def test_validate_passes():
    s = InputSchema(
        environment={
            "VAR": {"source": "field", "fieldname": "name"},
        },
    )
    inp = Input(s)
    request = MagicMock()
    request.json = {"name": "alice"}
    assert inp.validate(request) is None


def test_validate_missing_field():
    s = InputSchema(
        environment={
            "VAR": {"source": "field", "fieldname": "name"},
        },
    )
    inp = Input(s)
    request = MagicMock()
    request.json = {}
    result = inp.validate(request)
    assert result is not None
    assert "name" in result


def test_validate_missing_file_field():
    s = InputSchema(
        files=[
            {"fieldname": "cert_data", "destination": "cert.pem"},
        ],
    )
    inp = Input(s)
    request = MagicMock()
    request.json = {}
    result = inp.validate(request)
    assert result is not None
    assert "cert_data" in result


def test_validate_file_field_present():
    s = InputSchema(
        files=[
            {"fieldname": "cert_data", "destination": "cert.pem"},
        ],
    )
    inp = Input(s)
    request = MagicMock()
    request.json = {"cert_data": "contents"}
    assert inp.validate(request) is None


def test_create_variable_files(tmp_path):
    s = InputSchema(
        files=[
            {"fieldname": "config", "destination": "app.conf"},
        ],
    )
    inp = Input(s)
    inp.create_variable_files(tmp_path, {"config": "key=value"})
    # Find the written file (host filename is hashed)
    written = list(tmp_path.iterdir())
    assert len(written) == 1
    assert written[0].read_text() == "key=value"


def test_invalid_env_source():
    with pytest.raises(ValidationError):
        InputSchema(
            environment={
                "BAD": {"source": "magic", "fieldname": "x"},
            },
        )
