import logging
import time
import os

from meshtastic.serial_interface import SerialInterface
from meshtastic.tcp_interface import TCPInterface
from meshtastic.mesh_interface import MeshInterface
from pubsub import pub
from functools import partial

from core.config import Config
from core.dispatcher import dispatch

logger = logging.getLogger(__name__)

start_time = time.time()

def on_connection(interface: MeshInterface, topic=pub.AUTO_TOPIC):
    config = interface_manager_config
    try:
        # Determine message for command channel
        allowed_raw = config.allowed_shell_commands
        allowed_set = {c.strip() for c in allowed_raw.split(',') if c.strip()}

        if allowed_set:
            cmd_message = "C2 online – send !cmd <command> (allowed: " + ", ".join(sorted(allowed_set))[:100] + "...)"
        else:
            cmd_message = "C2 online"

        interface.sendText(cmd_message, channelIndex=config.channel_cmd, wantAck=False)
        logger.info(f"Sent command channel startup: {cmd_message[:50]}...")

        time.sleep(3)

        interface.sendText(config.test_startup_message, channelIndex=config.channel_test, wantAck=False)
        logger.info("Sent test startup message")
    except Exception as e:
        logger.error(f"Startup send failed: {e}")

def on_receive(packet: dict, interface: MeshInterface, config):
    dispatch(packet, interface, config)

interface_manager_config: Config = None

def connect_and_run(config: Config):
    global interface_manager_config, start_time
    interface_manager_config = config
    start_time = time.time()

    interface: MeshInterface = None

    try:
        if config.connection_type == "TCP":
            logger.info(f"TCP connect → {config.tcp_hostname}:{config.tcp_port}")
            interface = TCPInterface(hostname=config.tcp_hostname, portNumber=config.tcp_port)
        elif config.connection_type == "SERIAL":
            dev = config.serial_port or None
            logger.info(f"Serial connect → {dev or 'auto-detect'}")
            interface = SerialInterface(devPath=dev)
        else:
            raise ValueError(f"Unsupported connection_type: {config.connection_type}")

        pub.subscribe(partial(on_receive, config=config), "meshtastic.receive")
        pub.subscribe(on_connection, "meshtastic.connection.established")

        logger.info(f"Listening:\n  !cmd  → channel {config.channel_cmd}\n  !test → channel {config.channel_test}")

        while True:
            uptime_sec = time.time() - start_time
            uptime_str = time.strftime("%H:%M:%S", time.gmtime(uptime_sec))
            status = f"C2 status | Uptime: {uptime_str}"
            try:
                interface.sendText(status, channelIndex=config.channel_cmd, wantAck=False)
            except Exception as e:
                logger.warning(f"Status send failed: {e}")
            time.sleep(config.status_interval)

    except KeyboardInterrupt:
        logger.info("Shutdown requested")
    except Exception as e:
        logger.critical(f"Fatal error: {e}", exc_info=True)
    finally:
        if interface is not None:
            try:
                interface.close()
            except:
                pass
        logger.info("Interface closed")
