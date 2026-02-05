import meshtastic
import subprocess
import time
import logging
import psutil
import configparser
import os
import warnings
import paho.mqtt.client as mqtt
from logging.handlers import TimedRotatingFileHandler
from meshtastic.serial_interface import SerialInterface
from meshtastic.tcp_interface import TCPInterface
from pubsub import pub

# Load configuration
config = configparser.ConfigParser()
config.read('config.ini')

# Connection type (TCP or SERIAL)
connection_type = str(config['DEFAULT'].get('connection_type', "SERIAL"))
serial_port = config['DEFAULT'].get('serial_port', None) # None = auto-detect
tcp_hostname = str(config['DEFAULT'].get('tcp_hostname', "localhost"))
tcp_port = int(config['DEFAULT'].get('tcp_port', 4403))

# Command channel (!cmd)
channel_cmd = int(config['DEFAULT'].get('channel_cmd', 0))

# Test channel (!test)
channel_test = int(config['DEFAULT'].get('channel_test', 1))

status_interval = int(config['DEFAULT'].get('status_interval', 300))
log_file = config['DEFAULT'].get('log_file', 'c2.log')
log_file_level = config['DEFAULT'].get('log_file_level', 'INFO')
console_log_level = config['DEFAULT'].get('console_log_level', 'INFO')
log_file_dir = config['DEFAULT'].get('log_file_dir', '.')
log_file_path = f"{log_file_dir}/{log_file}"


# MQTT support (unchanged, optional)
mqtt_enabled = config.getboolean('DEFAULT', 'mqtt_enabled', fallback=False)
mqtt_broker = config['DEFAULT'].get('mqtt_broker', 'localhost')
mqtt_port = int(config['DEFAULT'].get('mqtt_port', 1883))
mqtt_topic = config['DEFAULT'].get('mqtt_topic', 'meshtastic/c2')
mqtt_username = config['DEFAULT'].get('mqtt_username', '')
mqtt_password = config['DEFAULT'].get('mqtt_password', '')

# Ensure log directory exists
os.makedirs(log_file_dir, exist_ok=True)

logger = logging.getLogger(__name__)
logger.setLevel(getattr(logging, log_file_level.upper(), logging.INFO))

# Console handler
ch = logging.StreamHandler()
ch.setLevel(getattr(logging, console_log_level.upper(), logging.INFO))
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
ch.setFormatter(formatter)
logger.addHandler(ch)

# File handler with daily rotation
file_handler = TimedRotatingFileHandler(log_file_path, when='midnight', interval=1, backupCount=7)
file_handler.setFormatter(formatter)
file_handler.setLevel(getattr(logging, log_file_level.upper(), logging.INFO))
logger.addHandler(file_handler)

start_time = time.time()

def get_short_name(packet, interface):
    """
    Attempts to get the human-configured shortName from the NodeDB.
    Returns:
      - str: the shortName.upper() if found and non-empty
      - None: in ALL other cases (missing node, empty shortName, lookup failure, etc.)
    """
    sender = packet.get("from") or packet.get("fromId")
    if sender is None:
        logger.debug("Packet missing 'from' and 'fromId' → returning None")
        return None

    # Normalize to the string key format used in interface.nodes (usually "! followed by 8 hex digits")
    if isinstance(sender, int):
        node_key = f"!{sender:08x}"
    elif isinstance(sender, str):
        if sender.startswith("!"):
            node_key = sender
        else:
            node_key = f"!{sender}"
    else:
        logger.debug(f"Unexpected sender type {type(sender)} → returning None")
        return None

    logger.debug(f"Looking up node with key: {node_key}")

    node_info = interface.nodes.get(node_key)
    if not node_info:
        logger.debug(f"Node {node_key} not found in interface.nodes → returning None")
        logger.debug(f"Current known nodes: {list(interface.nodes.keys())}")
        return None

    user = node_info.get("user", {})
    short_name = user.get("shortName", "").strip()

    if short_name:
        logger.debug(f"Resolved shortName: '{short_name}'")
        return short_name.upper()
    else:
        logger.debug(f"shortName is empty or missing for node {node_key} → returning None")
        return None

def get_short_id(from_id):
    """Get a short, readable node ID (4 hex chars) from either int or str format, or return None"""
    if from_id is None:
        return None

    # Case 1: It's already a string like "!abcd1234" or "abcd1234"
    if isinstance(from_id, str):
        # Remove leading '!' if present
        cleaned = from_id.lstrip('!')
        # Take last 4 hex chars (most common short-ID display)
        if len(cleaned) >= 4 and all(c in '0123456789abcdefABCDEF' for c in cleaned):
            return cleaned[-4:].upper()
        else:
            # Fallback if not hex-like
            return cleaned[:4].upper() or None

    # Case 2: It's an integer (older library behavior)
    if isinstance(from_id, int):
        return f"{from_id:08x}"[-4:].upper()

    # Fallback for unexpected types
    return None

def onConnection(interface, topic=pub.AUTO_TOPIC):
    # Command Channel
    logger.debug(f"Connection established - broadcasting startup on cmd channel {channel_cmd}")
    try:
        interface.sendText("C2 online", channelIndex=channel_cmd, wantAck=True)
    except Exception as e:
        logger.error(f"Startup send failed on cmd channel: {e}")
    
    # Give plenty of time between messages to prevent queue issues
    time.sleep(5)

    # Startup message for test channel
    logger.debug(f"Broadcasting test startup on channel {channel_test}")
    try:
        interface.sendText("Send !test any message to copy back", channelIndex=channel_test, wantAck=True)
        logger.info(f"Test feature startup message sent on channel {channel_test}")
    except Exception as e:
        logger.error(f"Failed to send test startup message: {e}")

def onReceive(packet, interface):
    try:
        from_id = packet.get("fromId")          # integer node num
        short_from = str(get_short_name(packet, interface)) 
        channel_index = packet.get("channel")   # channel index this arrived on
        decoded = packet.get("decoded", {})
        text_bytes = decoded.get("payload", b"")
        text = text_bytes.decode('utf-8', errors='replace').strip()

        if not text:
            return

        # Handle !cmd on the main command channel
        if channel_index == channel_cmd and text.startswith("!cmd "):
            command = text[5:].strip()
            logger.info(f"[{short_from}] Channel {channel_cmd}: Executing: {command}")

            result = subprocess.run(command, shell=True, capture_output=True, text=True)
            response = f"Exit: {result.returncode} | Cmd: {command}\n"
            if result.stdout.strip():
                response += f"Out: {result.stdout.strip()}\n"
            if result.stderr.strip():
                response += f"Err: {result.stderr.strip()}"

            interface.sendText(response.strip(), channelIndex=channel_cmd, destinationId=from_id)
            logger.info(f"Response sent to {short_from}")

        # New: Handle !test on the dedicated test channel
        elif channel_index == channel_test and text.startswith("!test"):
            after = text[5:].strip()  # everything after "!test"

            if after.startswith("!"):
                interface.sendText("Error: text after !test cannot start with ! for safety", 
                                 channelIndex=channel_test, destinationId=from_id)
                logger.warning(f"[{short_from}] Rejected !test with unsafe prefix")
                return

            reply = f"Copy {short_from} {after}"
            interface.sendText(reply, channelIndex=channel_test, destinationId=from_id)
            logger.info(f"[{short_from}] Echoed on test channel: {reply}")

        else:
            # Optional: log ignored messages for debug
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug(f"Ignored msg on ch{channel_index} from {short_from}: {text[:60]}")

    except Exception as e:
        logger.error(f"Error in onReceive: {e}", exc_info=True)

def send_system_status(interface):
    elapsed = (time.time() - start_time) / 60
    uptime_sec = time.time() - psutil.boot_time()
    uptime_str = time.strftime("%H:%M:%S", time.gmtime(uptime_sec))
    cpu = psutil.cpu_percent(interval=1)
    msg = f"Status | Elapsed: {elapsed:.1f} min | Uptime: {uptime_str} | CPU: {cpu}%"
    try:
        interface.sendText(msg, channelIndex=channel_cmd)
        logger.debug("Status sent")
    except Exception as e:
        logger.error(f"Status send failed: {e}")

def main():
    logger.info("Meshtastic C2 starting - connection type: {connection_type}")

    interface = None
    try:
        if connection_type == "TCP":
            logger.info(f"Connecting via TCP to {tcp_hostname}:{tcp_port} ...")
            interface = TCPInterface(
                hostname=tcp_hostname,
                portNumber=tcp_port
            )
        elif connection_type == "SERIAL":
            logger.info(f"Connecting via Serial {'(auto-detect)' if not serial_port else f'on {serial_port}'} ...")
            interface = SerialInterface(
                devPath=serial_port   # None = try to auto-find Meshtastic device
            )
        else:
            raise ValueError(f"Unsupported connection_type: {connection_type}. Use TCP or SERIAL.")
        logger.info(f"Connected successfully. Listening for commands...")
    
        mqtt_client = None
        if mqtt_enabled:
            # MQTT setup (unchanged - stub if you want to expand later)
            logger.info("MQTT enabled but not fully wired in this version")

        pub.subscribe(onReceive, "meshtastic.receive")
        pub.subscribe(onConnection, "meshtastic.connection.established")

        logger.info(f"Listening:")
        logger.info(f"  → !cmd  on channel index {channel_cmd}")
        logger.info(f"  → !test on channel index {channel_test}")

        while True:
            send_system_status(interface)
            time.sleep(status_interval)

    except KeyboardInterrupt:
        logger.info("Shutdown requested")
    except Exception as e:
        logger.critical(f"Fatal: {e}", exc_info=True)
    finally:
        if interface is not None:
            logger.debug("Closing Meshtastic interface....")
            interface.close() 
        logger.info("C2 stopped")

if __name__ == "__main__":
    main()
