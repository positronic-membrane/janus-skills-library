import logging
from mock_sdk import make_mock_sdk
from skill import run


def test_echo_message_returns_message():
    sdk = make_mock_sdk()
    sdk["logger"] = logging.getLogger("test")
    result = run(sdk, {"message": "hello"})
    assert result["result"] == "hello"


def test_echo_message_empty_args():
    sdk = make_mock_sdk()
    sdk["logger"] = logging.getLogger("test")
    result = run(sdk, {})
    assert result["result"] == ""
