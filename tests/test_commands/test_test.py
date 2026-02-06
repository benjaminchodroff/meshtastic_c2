from commands.test import TestCommand

def test_test_execute_valid(mock_interface, mock_packet, mocker):
    cmd = TestCommand()
    mocker.patch('commands.test.get_short_name', return_value="BEN1")
    cmd.execute(mock_packet, mock_interface, "hello")
    mock_interface.sendText.assert_called_once_with(
        "Copy BEN1 hello",
        channelIndex=1,
        destinationId=1234567890
    )

def test_test_execute_invalid_prefix(mock_interface, mock_packet):
    cmd = TestCommand()
    cmd.execute(mock_packet, mock_interface, "!bad")
    mock_interface.sendText.assert_called_once_with(
        "Error: message cannot start with !",
        channelIndex=1,
        destinationId=1234567890
    )
