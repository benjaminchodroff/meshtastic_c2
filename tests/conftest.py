import pytest
from unittest.mock import MagicMock

@pytest.fixture
def mock_interface():
    interface = MagicMock()
    interface.sendText = MagicMock()
    interface.nodes = {}
    return interface

@pytest.fixture
def mock_packet(channel=1, text="!test hello"):
    return {
        "from": 1234567890,
        "fromId": "!abcd1234",
        "channel": channel,
        "decoded": {"payload": text.encode()}
    }
