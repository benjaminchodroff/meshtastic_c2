import logging
import os
from logging.handlers import TimedRotatingFileHandler
from typing import Optional

from meshtastic.mesh_interface import MeshInterface

from .config import Config

logger = logging.getLogger(__name__)

def setup_logging(config: Config):
    os.makedirs(config.log_file_dir, exist_ok=True)

    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, config.log_file_level, logging.INFO))

    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    # Console
    ch = logging.StreamHandler()
    ch.setLevel(getattr(logging, config.console_log_level, logging.INFO))
    ch.setFormatter(formatter)
    root_logger.addHandler(ch)

    # Rotating file
    log_path = os.path.join(config.log_file_dir, config.log_file)
    fh = TimedRotatingFileHandler(log_path, when='midnight', interval=1, backupCount=7)
    fh.setLevel(getattr(logging, config.log_file_level, logging.INFO))
    fh.setFormatter(formatter)
    root_logger.addHandler(fh)

    logging.info("Logging initialized")

def get_short_name(packet: dict, interface: MeshInterface) -> Optional[str]:
    sender = packet.get("from") or packet.get("fromId")
    if sender is None:
        logger.debug("No sender in packet")
        return None

    if isinstance(sender, int):
        node_key = f"!{sender:08x}"
    elif isinstance(sender, str):
        node_key = sender if sender.startswith("!") else f"!{sender}"
    else:
        return None

    node = interface.nodes.get(node_key)
    if not node:
        logger.debug(f"Node {node_key} not found in NodeDB")
        return None

    short = node.get("user", {}).get("shortName", "").strip()
    return short.upper() if short else None
