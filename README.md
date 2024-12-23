# meshtastic_c2
Meshtastic Command &amp; Control (C2) example utility

Not recommended for production, no warranty or implied support. 

# Server Setup

git clone https://github.com/benjaminchodroff/meshtastic_c2.git
cd meshtastic_c2
virtualenv envs
source envs/bin/activate
pip install -r requirements.txt

# Lora Channel Setup

Create a new private channel for your Command and Control remote channel
meshtastic --ch-add REMOTE
Note the channel index and adjust below accordingly
meshtastic --ch-index 1 --ch-set psk random --ch-set uplink_enabled true --ch-set downlink_enabled true --ch-set module_settings.position_precision 32

Note: If you need to copy this channel to other devices, you can retrieve the random psk using meshtastic --info and converting the Base64 private key listed to Hex 0x123. The index number doesn't matter to be the same across devices, but you must update command.py to use the channel index to be monitored for commands

# Usage
Modify the channel number in command.py to reflect your private channel on the connected device
python command.py

From another device on the same channel (or via MQTT) you can now send messages such as "!cmd touch HelloWorld.txt" to execute remote commands
 
