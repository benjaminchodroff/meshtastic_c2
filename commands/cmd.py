import shlex
import subprocess
import logging

from meshtastic.mesh_interface import MeshInterface
from .base import Command

logger = logging.getLogger(__name__)

class ShellCommand(Command):
    name = "!cmd"
    channel = None

    def execute(self, packet: dict, interface: MeshInterface, args: str, config):
        channel_idx = packet.get("channel")
        from_id = packet.get("from") or packet.get("fromId")

        if not args:
            interface.sendText(
                "Usage: !cmd <command>",
                channelIndex=channel_idx,
                destinationId=from_id
            )
            return

        try:
            parts = shlex.split(args)
            if not parts:
                interface.sendText("Empty command", channelIndex=channel_idx, destinationId=from_id)
                return
            cmd_base = parts[0]
        except ValueError as e:
            interface.sendText(f"Invalid command syntax: {str(e)}", channelIndex=channel_idx, destinationId=from_id)
            return

        allowed_raw = config.allowed_shell_commands
        allowed_set = {c.strip() for c in allowed_raw.split(',') if c.strip()}

        if not allowed_set:
            interface.sendText(
                "!cmd is disabled (no allowed commands configured)",
                channelIndex=channel_idx,
                destinationId=from_id
            )
            logger.warning(f"!cmd attempted but disabled in config: {args} from {from_id}")
            return

        if cmd_base not in allowed_set:
            interface.sendText(
                f"Command '{cmd_base}' is not allowed",
                channelIndex=channel_idx,
                destinationId=from_id
            )
            logger.warning(f"Rejected disallowed !cmd: {args} from {from_id}")
            return

        try:
            result = subprocess.run(
                parts,
                capture_output=True,
                text=True,
                timeout=30,
                check=False,
            )

            response = f"Exit: {result.returncode}"
            if result.stdout.strip():
                response += f"\nOut:\n{result.stdout.strip()}"
            if result.stderr.strip():
                response += f"\nErr:\n{result.stderr.strip()}"

            interface.sendText(response, channelIndex=channel_idx, destinationId=from_id)
            logger.info(f"Allowed !cmd executed: {args} from {from_id}")

        except subprocess.TimeoutExpired:
            interface.sendText("Command timed out after 30 seconds", channelIndex=channel_idx, destinationId=from_id)
            logger.warning(f"!cmd timeout: {args} from {from_id}")

        except Exception as e:
            interface.sendText(f"Execution error: {str(e)}", channelIndex=channel_idx, destinationId=from_id)
            logger.error(f"Shell command failed: {args} → {e}")
