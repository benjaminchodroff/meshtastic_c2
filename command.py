import meshtastic
import subprocess
import time
import logging
import psutil
from meshtastic.serial_interface import SerialInterface
from pubsub import pub

channel=1

logger = logging.getLogger(__name__)
ch = logging.StreamHandler()

start_time = time.time()

def onConnection(interface, topic=pub.AUTO_TOPIC):
    logger.debug(f"Broadcast startup message on channel {channel}")
    startup_message = f"Device is online and ready."
    interface.sendText(startup_message, channelIndex=channel)
    logger.info(f"Startup message broadcasted on channel {channel}: {startup_message}")

def onReceive(packet, interface):
    logger.debug(f"Received packet...")
    try:
        # Extract channel index and message text
        channel_index = packet.get("channel")
        text = packet.get("decoded").get("payload", {})
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
    interface.sendText(status_message, channelIndex=channel)

def main():
    try:
        logging.basicConfig(filename='output.log', level=logging.DEBUG)
        ch.setLevel(logging.DEBUG)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        ch.setFormatter(formatter)
        logger.addHandler(ch)
        logger.info('Started')
        
        while True:
            try:
                logger.info("Connecting to Meshtastic device...")
                with SerialInterface() as interface:
                    try:
                        if interface.nodes:
                            for n in interface.nodes.values():
                                if n["num"] == interface.myInfo.my_node_num:
                                    logger.debug(n["user"]["hwModel"])
                       
                        pub.subscribe(onReceive, "meshtastic.receive")
                        pub.subscribe(onConnection, "meshtastic.connection.established")
                        logger.info("Listening for messages. Press Ctrl+C to exit.")
                        
                        # Send system status every 5 minutes
                        while True:
                            send_system_status(interface)
                            time.sleep(300)  # Sleep for 5 minutes
                    except Exception as e:
                        logger.error(f"Error during operation: {e}")
                    finally:
                        logger.debug("Closing the interface.")
                        interface.close()
            except Exception as e:
                logger.error(f"Connection error: {e}")
                logger.info("Attempting to reconnect in 5 seconds...")
                time.sleep(5)
    except KeyboardInterrupt:
        logger.info('Finished')
    except Exception as e:
        logger.error(f"Error: {e}")

if __name__ == "__main__":
    main()

