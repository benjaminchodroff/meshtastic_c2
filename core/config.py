# core/config.py

import configparser
import os
import sys
from typing import Optional

class Config:
    def __init__(self):
        # Connection settings
        self.connection_type: str = "SERIAL"
        self.tcp_hostname: str = "192.168.1.100"
        self.tcp_port: int = 4403
        self.serial_port: Optional[str] = "/dev/ttyUSB0"

        # Channel settings
        self.channel_cmd: int = 1
        self.channel_test: int = 1

        # Logging & status
        self.status_interval: int = 600
        self.log_file: str = "meshtastic_c2.log"
        self.log_file_dir: str = "./log/meshtastic_c2"
        self.log_file_level: str = "INFO"
        self.console_log_level: str = "INFO"

        # MQTT (kept but not actively used in current code)
        self.mqtt_enabled: bool = False
        self.mqtt_broker: str = "mqtt.meshtastic.org"
        self.mqtt_port: int = 1883
        self.mqtt_username: str = "meshdev"
        self.mqtt_password: str = "large4cats"
        self.mqtt_topic: str = "msh/AE"

        # Test command feature
        self.test_startup_message: str = "Send !test any message to copy back"


def load_config(path: str = "config.ini") -> Config:
    """
    Load configuration from config.ini.
    Exits the program with error if the file is missing or cannot be parsed.
    """
    full_path = os.path.abspath(path)

    if not os.path.isfile(full_path):
        print("\n" + "=" * 80)
        print("CRITICAL ERROR: Required configuration file not found")
        print(f"               Expected: {full_path}")
        print("=" * 80)
        print("\nThe application cannot start without config.ini.")
        print("To fix:")
        print("  1. Copy config.ini.example to config.ini in the project root")
        print("  2. Edit the values (especially connection_type, tcp_hostname/serial_port, channels)")
        print("  3. Run the application again\n")
        sys.exit(1)

    parser = configparser.ConfigParser()

    try:
        parsed_files = parser.read(full_path)
        if not parsed_files:
            print(f"CRITICAL ERROR: Could not read or parse config.ini: {full_path}")
            sys.exit(1)
    except configparser.Error as e:
        print(f"CRITICAL ERROR: Failed to parse config.ini: {full_path}")
        print(f"Parse error: {e}")
        sys.exit(1)

    if "DEFAULT" not in parser:
        print(f"CRITICAL ERROR: config.ini is missing required [DEFAULT] section: {full_path}")
        sys.exit(1)

    cfg = Config()
    sec = parser["DEFAULT"]

    # Load values with defaults from class
    cfg.connection_type    = sec.get("connection_type", cfg.connection_type).upper()
    cfg.tcp_hostname       = sec.get("tcp_hostname", cfg.tcp_hostname)
    cfg.tcp_port           = int(sec.get("tcp_port", str(cfg.tcp_port)))
    cfg.serial_port        = sec.get("serial_port", cfg.serial_port) or None

    cfg.channel_cmd        = int(sec.get("channel_cmd", str(cfg.channel_cmd)))
    cfg.channel_test       = int(sec.get("channel_test", str(cfg.channel_test)))

    cfg.status_interval    = int(sec.get("status_interval", str(cfg.status_interval)))
    cfg.log_file           = sec.get("log_file", cfg.log_file)
    cfg.log_file_dir       = sec.get("log_file_dir", cfg.log_file_dir)
    cfg.log_file_level     = sec.get("log_file_level", cfg.log_file_level).upper()
    cfg.console_log_level  = sec.get("console_log_level", cfg.console_log_level).upper()

    cfg.mqtt_enabled       = sec.getboolean("mqtt_enabled", cfg.mqtt_enabled)
    cfg.mqtt_broker        = sec.get("mqtt_broker", cfg.mqtt_broker)
    cfg.mqtt_port          = int(sec.get("mqtt_port", str(cfg.mqtt_port)))
    cfg.mqtt_username      = sec.get("mqtt_username", cfg.mqtt_username)
    cfg.mqtt_password      = sec.get("mqtt_password", cfg.mqtt_password)
    cfg.mqtt_topic         = sec.get("mqtt_topic", cfg.mqtt_topic)

    # Optional test message override
    cfg.test_startup_message = sec.get("test_startup_message", cfg.test_startup_message)

    return cfg
