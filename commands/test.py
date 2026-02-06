import logging

from meshtastic.mesh_interface import MeshInterface
from .base import Command
from core.utils import get_short_name

logger = logging.getLogger(__name__)

class TestCommand(Command):
    name = "!test"
    channel = None  # will use config.channel_test

    def execute(self, packet: dict, interface: MeshInterface, args: str, config=None):
        channel_idx = packet.get("channel")
        from_id = packet.get("from") or packet.get("fromId")

        if not args:
            interface.sendText("Usage: !test <message>", channelIndex=channel_idx, destinationId=from_id)
            return

        if args.strip().startswith("!"):
            interface.sendText("Error: message cannot start with !", channelIndex=channel_idx, destinationId=from_id)
            return

        short = get_short_name(packet, interface)
        display = short if short else f"({str(from_id)[-8:]})"

        reply = f"Copy {display} {args}"
        interface.sendText(reply, channelIndex=channel_idx, destinationId=from_id)
        logger.info(f"Test reply sent: {reply}")
