# meshtastic_c2
Meshtastic Command &amp; Control (C2) example utility

Not recommended for production, no warranty or implied support. 

# Server Setup

```
git clone https://github.com/benjaminchodroff/meshtastic_c2.git
cd meshtastic_c2
virtualenv envs
source envs/bin/activate
pip install -r requirements.txt
cp config.ini.example config.ini
```

# Lora Channel Setup

Create a new private channel for your Command and Control remote channel:

```meshtastic --ch-add REMOTE```

Note the channel index and adjust below accordingly:

```meshtastic --ch-index 1 --ch-set psk random --ch-set uplink_enabled true --ch-set downlink_enabled true --ch-set module_settings.position_precision 32```

Note: If you need to copy this channel to other devices, you can retrieve the random psk using meshtastic --info and converting the Base64 private key listed to Hex 0x123. The index number doesn't matter to be the same across devices, but you must update c2.py to use the channel index to be monitored for commands

# Usage

Modify the channel number in config.ini to reflect your private channel on the connected device

```python c2.py```

# Optional: Run as a Systemd Service (Ubuntu 22.04)

To run this script as a service at system startup, follow these steps:

1. Create a systemd service file:

```bash
sudo nano /etc/systemd/system/meshtastic_c2.service
```

2. Add the following content to the service file, replace `/path/to/meshtastic_c2` with the actual path to your installation directory and adjust the `User` as needed.

```ini
[Unit]
Description=Meshtastic Command & Control Service
After=network.target

[Service]
User=root
WorkingDirectory=/path/to/meshtastic_c2 
ExecStart=/path/to/meshtastic_c2/envs/bin/python /path/to/meshtastic_c2/c2.py
Restart=always

[Install]
WantedBy=multi-user.target
```

3. Reload systemd to recognize the new service:

```bash
sudo systemctl daemon-reload
```

4. Enable the service to start on boot:

```bash
sudo systemctl enable meshtastic_c2.service
```

5. Start the service:

```bash
sudo systemctl start meshtastic_c2.service
```

6. Check the status of the service:

```bash
sudo systemctl status meshtastic_c2.service
```

