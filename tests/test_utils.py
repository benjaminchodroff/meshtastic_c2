# tests/test_utils.py
import pytest
from core.utils import get_short_name

# Fixtures are already defined in conftest.py
# We're using mock_interface and mock_packet from there


def test_get_short_name_success(mock_interface, mock_packet):
    """
    Test that shortName is correctly returned when node info is present.
    Uses consistent sender value so hex normalization matches the mock key.
    """
    # Use a value whose hex representation matches the key we set
    sender_int = 0xabcd1234  # 2882402356 in decimal
    sender_str = "!abcd1234"

    # Update packet with consistent values
    mock_packet["from"] = sender_int
    mock_packet["fromId"] = sender_str

    # Set up the node info in the mock
    mock_interface.nodes[sender_str] = {
        "user": {
            "shortName": "BEN1",
            "longName": "Benjamin's Node"  # optional, for realism
        }
    }

    result = get_short_name(mock_packet, mock_interface)
    assert result == "BEN1"


def test_get_short_name_failure_no_node(mock_interface, mock_packet):
    """Test returns None when node is not found in interface.nodes"""
    # No node info set in mock_interface.nodes
    result = get_short_name(mock_packet, mock_interface)
    assert result is None


def test_get_short_name_failure_no_shortname(mock_interface, mock_packet):
    """Test returns None when shortName is missing or empty"""
    sender_str = "!12345678"
    mock_packet["from"] = 0x12345678
    mock_packet["fromId"] = sender_str

    # Node exists, but shortName is empty
    mock_interface.nodes[sender_str] = {
        "user": {
            "shortName": "",
            "longName": "Some Node"
        }
    }

    result = get_short_name(mock_packet, mock_interface)
    assert result is None


def test_get_short_name_failure_no_sender(mock_interface, mock_packet):
    """Test returns None when packet has neither 'from' nor 'fromId'"""
    # Remove sender fields
    mock_packet.pop("from", None)
    mock_packet.pop("fromId", None)

    result = get_short_name(mock_packet, mock_interface)
    assert result is None


def test_get_short_name_handles_string_without_exclamation(mock_interface, mock_packet):
    """Test normalizes string sender without leading '!'"""
    sender_str = "abcd1234"  # no '!'
    mock_packet["fromId"] = sender_str
    mock_packet["from"] = None

    mock_interface.nodes["!abcd1234"] = {
        "user": {"shortName": "TEST1"}
    }

    result = get_short_name(mock_packet, mock_interface)
    assert result == "TEST1"
