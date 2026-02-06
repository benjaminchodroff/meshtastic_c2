import pytest
import subprocess
from unittest.mock import MagicMock, patch
from commands.cmd import ShellCommand


@pytest.fixture
def mock_config():
    config = MagicMock()
    config.allowed_shell_commands = ""
    return config


@pytest.fixture
def mock_interface():
    interface = MagicMock()
    interface.sendText = MagicMock()
    return interface


@pytest.fixture
def mock_packet():
    return {
        "from": 1234567890,
        "fromId": "!abcd1234",
        "channel": 1,
    }


def test_cmd_no_args(mock_interface, mock_packet, mock_config):
    cmd = ShellCommand()
    cmd.execute(mock_packet, mock_interface, "", mock_config)
    mock_interface.sendText.assert_called_once_with(
        "Usage: !cmd <command>",
        channelIndex=1,
        destinationId=1234567890
    )


def test_cmd_empty_after_split(mock_interface, mock_packet, mock_config):
    cmd = ShellCommand()
    cmd.execute(mock_packet, mock_interface, "   ", mock_config)
    mock_interface.sendText.assert_called_once_with(
        "Empty command",
        channelIndex=1,
        destinationId=1234567890
    )


def test_cmd_disabled_no_allowed_commands(mock_interface, mock_packet, mock_config):
    cmd = ShellCommand()
    cmd.execute(mock_packet, mock_interface, "uptime", mock_config)

    mock_interface.sendText.assert_called_once_with(
        "!cmd is disabled (no allowed commands configured)",
        channelIndex=1,
        destinationId=1234567890
    )


def test_cmd_not_in_whitelist(mock_interface, mock_packet, mock_config):
    mock_config.allowed_shell_commands = "uptime,df -h"

    cmd = ShellCommand()
    cmd.execute(mock_packet, mock_interface, "rm -rf dangerous", mock_config)

    mock_interface.sendText.assert_called_once_with(
        "Command 'rm' is not allowed",
        channelIndex=1,
        destinationId=1234567890
    )


def test_cmd_allowed_successful_execution(mock_interface, mock_packet, mock_config):
    mock_config.allowed_shell_commands = "uptime,whoami"

    with patch("subprocess.run") as mock_run:
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "up 2 days\n"
        mock_result.stderr = ""
        mock_run.return_value = mock_result

        cmd = ShellCommand()
        cmd.execute(mock_packet, mock_interface, "uptime", mock_config)

        mock_interface.sendText.assert_called_once()
        sent_text = mock_interface.sendText.call_args[0][0]
        assert "Exit: 0" in sent_text
        assert "up 2 days" in sent_text


def test_cmd_allowed_nonzero_exit(mock_interface, mock_packet, mock_config):
    mock_config.allowed_shell_commands = "ls"

    with patch("subprocess.run") as mock_run:
        mock_result = MagicMock()
        mock_result.returncode = 2
        mock_result.stdout = ""
        mock_result.stderr = "ls: cannot access 'nonexistent': No such file or directory\n"
        mock_run.return_value = mock_result

        cmd = ShellCommand()
        cmd.execute(mock_packet, mock_interface, "ls nonexistent", mock_config)

        mock_interface.sendText.assert_called_once()
        sent_text = mock_interface.sendText.call_args[0][0]
        assert "Exit: 2" in sent_text
        assert "Err:" in sent_text


def test_cmd_timeout(mock_interface, mock_packet, mock_config):
    mock_config.allowed_shell_commands = "sleep"

    with patch("subprocess.run") as mock_run:
        mock_run.side_effect = subprocess.TimeoutExpired("sleep 60", 30)

        cmd = ShellCommand()
        cmd.execute(mock_packet, mock_interface, "sleep 60", mock_config)

        mock_interface.sendText.assert_called_once_with(
            "Command timed out after 30 seconds",
            channelIndex=1,
            destinationId=1234567890
        )


def test_cmd_invalid_shlex_syntax(mock_interface, mock_packet, mock_config):
    mock_config.allowed_shell_commands = "echo"

    cmd = ShellCommand()
    cmd.execute(mock_packet, mock_interface, 'echo "unmatched quote', mock_config)

    mock_interface.sendText.assert_called_once()
    sent_text = mock_interface.sendText.call_args[0][0]
    assert "Invalid command syntax" in sent_text
