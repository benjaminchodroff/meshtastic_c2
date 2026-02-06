#!/usr/bin/env python3
import logging
from core.config import load_config
from core.utils import setup_logging
from core.dispatcher import register_all_commands
from core.interface_manager import connect_and_run

def main():
    config = load_config()
    setup_logging(config)

    logger = logging.getLogger(__name__)
    logger.info("Meshtastic C2 starting...")

    register_all_commands()

    connect_and_run(config)

if __name__ == "__main__":
    main()
