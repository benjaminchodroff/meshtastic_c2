import logging
from typing import Dict

from meshtastic.mesh_interface import MeshInterface
from pubsub import pub

from commands.base import Command

logger = logging.getLogger(__name__)

commands: Dict[str, Command] = {}


def register_command(cmd: Command):
    logger.debug(f"register_command starting: {cmd}")
    commands[cmd.name.lower()] = cmd
    for alias in cmd.aliases:
        commands[alias.lower()] = cmd
    logger.debug(f"register_command finished: {cmd.name}")

def register_all_commands(config):
    if config.channel_cmd >=0:
        from commands.cmd import ShellCommand
        command_cmd = ShellCommand()
        command_cmd.channel = config.channel_cmd
        register_command(command_cmd)
    if config.channel_test >=0:
        from commands.test import TestCommand
        command_test = TestCommand()
        command_test.channel = config.channel_test
        register_command(command_test)

def dispatch(packet: dict, interface: MeshInterface, config):
    try:
        logger.debug(f"dispatch is processing")
        channel_idx = packet.get("channel")
        decoded = packet.get("decoded", {})
        text_bytes = decoded.get("payload", b"")
        text = text_bytes.decode("utf-8", errors="replace").strip()

        if not text.startswith("!"):
            logger.debug(f"Not processing text because it did not start with a command")
            return

        parts = text.split(maxsplit=1)
        cmd_name = parts[0].lower()
        args = parts[1] if len(parts) > 1 else ""

        cmd = commands.get(cmd_name)
        if not cmd:
            logger.debug(f"Rejecting command: {cmd_name} because it is not known")
            return
        
        if cmd.channel is None:
            logger.info(f"Rejected command: {cmd_name} in channel {channel_idx} because it is disabled in all channels")
            return

        if cmd.channel is not None and channel_idx != cmd.channel or channel_idx is None:
            logger.debug(f"Rejected command: {cmd_name} in channel {channel_idx} because not in registered channel {cmd.channel}")
            return

        logger.info(f"Dispatch executing {cmd_name} on channel {channel_idx}")
        cmd.execute(packet, interface, args, config)
        logger.debug(f"Dispatch completed")
    except Exception as e:
        logger.error(f"Dispatch failed: {e}", exc_info=True)
