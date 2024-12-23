import meshtastic
import subprocess
import time
import logging
import psutil
import configparser
import os
import paho.mqtt.client as mqtt
from logging.handlers import TimedRotatingFileHandler
from meshtastic.serial_interface import SerialInterface
from pubsub import pub

# Load configuration
config = configparser.ConfigParser()
config.read('config.ini')
channel = int(config['DEFAULT']['channel'])
status_interval = int(config['DEFAULT']['status_interval'])
log_file = config['DEFAULT']['log_file']
log_file_level = config['DEFAULT']['log_file_level']
console_log_level = config['DEFAULT']['console_log_level']
log_file_dir = config['DEFAULT']['log_file_dir']
log_file_path = f"{log_file_dir}/{log_file}"

mqtt_enabled = config.getboolean('DEFAULT', 'mqtt_enabled')
mqtt_broker = config['DEFAULT']['mqtt_broker']
mqtt_port = int(config['DEFAULT']['mqtt_port'])
mqtt_topic = config['DEFAULT']['mqtt_topic']
mqtt_username = config['DEFAULT']['mqtt_username']
mqtt_password = config['DEFAULT']['mqtt_password']

# Ensure the log directory exists
try:
    os.makedirs(log_file_dir, exist_ok=True)
except Exception as e:
    logging.critical(f"Failed to create log directory {log_file_dir}: {e}")
    raise SystemExit(f"Failed to create log directory {log_file_dir}: {e}")

logger = logging.getLogger(__name__)
ch = logging.StreamHandler()

start_time = time.time()

def onConnection(interface, topic=pub.AUTO_TOPIC):
    logger.debug(f"Broadcast startup message on channel {channel}")
    startup_message = "Device is online and ready."
    try:
        interface.sendText(startup_message, channelIndex=channel)
        logger.info(f"Startup message broadcasted on channel {channel}: {startup_message}")
    except Exception as e:
        logger.error(f"Failed to send startup message: {e}")

def onReceive(packet, interface):
    logger.debug("Received packet...")
    try:
        # Extract channel index and message text
        channel_index = packet.get("channel")
        text = packet.get("decoded", {}).get("payload", "")
        if channel_index == channel:  # Only process messages from the monitored channel index
            if text.startswith(b'!cmd '):  # Commands start with "!cmd "
                command = text[5:]  # Remove the "!cmd " prefix
                logger.info(f"Channel {channel}: Executing command: {command}")
                
                # Execute the command
                result = subprocess.run(command, shell=True, capture_output=True, text=True)
                command = str(command)
                # Prepare the response
                response = f"Exit Code: {result.returncode} Command: {command}\n"
                if result.stdout:
                    response += f"Output: {result.stdout.strip()}\n"
                if result.stderr:
                    response += f"Error: {result.stderr.strip()}"
                
                logger.info(f"Sending response: {response}")
                # Send the response back to channel 
                interface.sendText(response, channelIndex=channel)
            else:
                logger.debug(f"Message on channel {channel} ignored: {text}")
        else:
            logger.debug(f"Message from other channel ignored (Channel Index: {channel_index})")
    except Exception as e:
        logger.error(f"Error processing message: {e}")

def send_system_status(interface):
    elapsed_time = (time.time() - start_time) / 60  # Time since start in minutes
    uptime_seconds = time.time() - psutil.boot_time()
    uptime_str = time.strftime("%H:%M:%S", time.gmtime(uptime_seconds))
    cpu_load = psutil.cpu_percent(interval=1)
    status_message = f"Elapsed Time: {elapsed_time:.2f} minutes, Uptime: {uptime_str}, CPU Load: {cpu_load}%"
    logger.info(f"Sending system status: {status_message}")
    try:
        interface.sendText(status_message, channelIndex=channel)
    except Exception as e:
        logger.error(f"Failed to send system status: {e}")

def setup_logging():
    logging.basicConfig(level=getattr(logging, log_file_level))
    ch.setLevel(getattr(logging, console_log_level))
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    ch.setFormatter(formatter)
    logger.addHandler(ch)
    
    # Setup TimedRotatingFileHandler for daily log rotation
    file_handler = TimedRotatingFileHandler(log_file_path, when='midnight', interval=1)
    file_handler.setFormatter(formatter)
    file_handler.setLevel(getattr(logging, log_file_level))
    logger.addHandler(file_handler)
    
    logger.info('Started')

def on_mqtt_message(client, userdata, message):
    logger.info(f"Received MQTT message: {message.payload.decode()}")
    try:
        interface.sendText(message.payload.decode(), channelIndex=channel)
    except Exception as e:
        logger.error(f"Failed to send message to mesh network: {e}")

def setup_mqtt():
    client = mqtt.Client()
    client.username_pw_set(mqtt_username, mqtt_password)
    client.on_message = on_mqtt_message
    try:
        client.connect(mqtt_broker, mqtt_port)
        client.subscribe(mqtt_topic)
        client.loop_start()
        logger.info(f"Connected to MQTT broker at {mqtt_broker}:{mqtt_port}, subscribed to topic {mqtt_topic}")
    except Exception as e:
        logger.error(f"Failed to connect to MQTT broker: {e}")
        raise SystemExit(f"Failed to connect to MQTT broker: {e}")
    return client

def connect_and_listen():
    mqtt_client = None
    if mqtt_enabled:
        mqtt_client = setup_mqtt()
    
    while True:
        try:
            logger.info("Connecting to Meshtastic device...")
            with SerialInterface() as interface:
                try:
                    # Perform a sanity check to see if we can obtain the hardware model
                    if interface.nodes:
                        for n in interface.nodes.values():
                            if n["num"] == interface.myInfo.my_node_num:
                                logger.debug(n["user"]["hwModel"])
                    
                    pub.subscribe(onReceive, "meshtastic.receive")
                    pub.subscribe(onConnection, "meshtastic.connection.established")
                    logger.info("Listening for messages. Press Ctrl+C to exit.")
                    
                    # Send system status every configured interval
                    while True:
                        send_system_status(interface)
                        time.sleep(status_interval)  # Sleep for the configured interval
                except Exception as e:
                    logger.error(f"Error during operation: {e}")
                finally:
                    logger.debug("Closing the interface.")
                    interface.close()
        except Exception as e:
            logger.error(f"Connection error: {e}")
            logger.info("Attempting to reconnect to serial device in 5 seconds...")
            time.sleep(5)

def main():
    try:
        setup_logging()
        connect_and_listen()
    except KeyboardInterrupt:
        logger.info('Finished')
    except Exception as e:
        logger.error(f"Error: {e}")

if __name__ == "__main__":
    main()

