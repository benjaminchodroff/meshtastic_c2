import shlex
import subprocess
import logging

from meshtastic.mesh_interface import MeshInterface
from .base import Command

logger = logging.getLogger(__name__)

class ShellCommand(Command):
    name = "!cmd"
    channel = None  # can be set to config.channel_cmd later if desired

    def execute(self, packet: dict, interface: MeshInterface, args: str):
        channel_idx = packet.get("channel")
        from_id = packet.get("from") or packet.get("fromId")

        if not args:
            interface.sendText("Usage: !cmd <shell command>", channelIndex=channel_idx, destinationId=from_id)
            return

        try:
            cmd_list = shlex.split(args)
            result = subprocess.run(
                cmd_list,
                capture_output=True,
                text=True,
                timeout=45,
            )

            response = f"Exit: {result.returncode}"
            if result.stdout.strip():
                response += f"\nOut:\n{result.stdout.strip()}"
            if result.stderr.strip():
                response += f"\nErr:\n{result.stderr.strip()}"

            interface.sendText(response, channelIndex=channel_idx, destinationId=from_id)
        except subprocess.TimeoutExpired:
            interface.sendText("Command timed out (45s)", channelIndex=channel_idx, destinationId=from_id)
        except Exception as e:
            interface.sendText(f"Error: {str(e)}", channelIndex=channel_idx, destinationId=from_id)
            logger.error(f"Shell exec failed: {e}")
