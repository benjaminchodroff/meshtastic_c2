import logging
from typing import Dict

from meshtastic.mesh_interface import MeshInterface
from pubsub import pub

from commands.base import Command

logger = logging.getLogger(__name__)

commands: Dict[str, Command] = {}

def register_command(cmd: Command):
    commands[cmd.name.lower()] = cmd
    for alias in cmd.aliases:
        commands[alias.lower()] = cmd
    logger.debug(f"Registered: {cmd.name}")

def register_all_commands():
    from commands.cmd import ShellCommand
    from commands.test import TestCommand

    register_command(ShellCommand())
    register_command(TestCommand())

def dispatch(packet: dict, interface: MeshInterface):
    try:
        channel_idx = packet.get("channel")
        decoded = packet.get("decoded", {})
        text_bytes = decoded.get("payload", b"")
        text = text_bytes.decode("utf-8", errors="replace").strip()

        if not text.startswith("!"):
            return

        parts = text.split(maxsplit=1)
        cmd_name = parts[0].lower()
        args = parts[1] if len(parts) > 1 else ""

        disabled_set = {c.strip().lower() for c in config.disabled_commands.split(',') if c.strip()}  # Pass config to dispatch or make global
        if cmd_name in disabled_set:
            logger.warning(f"Rejected disabled command: {cmd_name}")
            return
        
        cmd = commands.get(cmd_name)
        if not cmd:
            return

        if cmd.channel is not None and channel_idx != cmd.channel:
            return

        logger.info(f"Dispatching {cmd_name} on channel {channel_idx}")
        cmd.execute(packet, interface, args)

    except Exception as e:
        logger.error(f"Dispatch failed: {e}", exc_info=True)
