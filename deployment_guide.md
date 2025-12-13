# Azure Hosting & Deployment Guide

This guide covers everything from setting up a fresh Azure server to keeping your application running 24/7.

## Phase 1: Initial Server Setup (From Scratch)

This section assumes you have a brand new **Ubuntu** server on Azure and have just logged in via SSH.

### 1. The Golden Rule of Ports
To ensure compatibility with other projects on the same server, **we must pick a unique port**.

1.  **Check used ports**: Run this to see what is already in use.
    ```bash
    sudo ss -tulpn | grep LISTEN
    ```
2.  **Pick your port**: The default is `5050`. If `5050` is taken, pick another (e.g., `5051`, `8000`, `3000`).
3.  **Open Firewall**: You must allow this port in your **Azure Network Security Group (NSG)**.
    *   Go to Azure Portal -> Compute -> Networking -> Add Inbound Rule -> Destination Port Ranges: `5050` (or your choice).

### 2. System Preparation
Update the system and install necessary tools:
```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y python3 python3-pip python3-venv git
```

### 3. Clone & Setup
We install the app in `/opt` (standard for optional software).

```bash
# 1. Navigate to /opt
cd /opt

# 2. Clone the repo
sudo git clone https://github.com/AbdullrahmanEsmael2007/LLMviaCall.git llm-voice

# 3. Give your user ownership (replace 'azureuser' if different)
sudo chown -R azureuser:azureuser llm-voice

# 4. Enter directory
cd llm-voice
```

### 4. Virtual Environment & Dependencies
```bash
# 1. Create venv
python3 -m venv venv

# 2. Activate it
source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt
```

### 5. Configuration (.env)
Create the configuration file:
```bash
nano .env
```
Paste your keys (ensure PORT matches what you picked in Step 1):
```ini
OPENAI_API_KEY=sk-...
TWILIO_ACCOUNT_SID=AC...
TWILIO_AUTH_TOKEN=...
PORT=5050 
```
*(Save: Ctrl+X, Y, Enter)*

---

## Phase 2: Running as a Service (Systemd)

We use `systemd` to keep the app running in the background.

### 1. App Service (`llm-voice`)

**1. Create Service File**: `sudo nano /etc/systemd/system/llm-voice.service`
```ini
[Unit]
Description=LLM Voice Assistant
After=network.target

[Service]
User=azureuser
Group=azureuser
WorkingDirectory=/opt/llm-voice
EnvironmentFile=/opt/llm-voice/.env
Environment="PATH=/opt/llm-voice/venv/bin"
# Port is loaded from .env automatically
ExecStart=/opt/llm-voice/venv/bin/uvicorn main:app --host 0.0.0.0

Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
```

**2. Enable and Start**:
```bash
sudo systemctl daemon-reload
sudo systemctl enable llm-voice
sudo systemctl start llm-voice
```

**3. Check Status**: `sudo systemctl status llm-voice`

### 2. Ngrok Service (Optional)

If you chose NOT to open ports in Azure or want a public HTTPS URL easily.

**1. Create Service File**: `sudo nano /etc/systemd/system/ngrok.service`
```ini
[Unit]
Description=Ngrok Tunnel
After=network.target

[Service]
User=azureuser
Group=azureuser
WorkingDirectory=/opt/llm-voice
# Replace with your actual config file path or token
ExecStart=/usr/local/bin/ngrok http 5050 --log=stdout

Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
```

**2. Enable and Start**:
```bash
sudo systemctl daemon-reload
sudo systemctl enable ngrok
sudo systemctl start ngrok
```

**3. Get Public URL**:
```bash
curl http://localhost:4040/api/tunnels
```

---

## Phase 3: Maintenance & Updates

### Restarting after Code Changes
Whenever you update code (`git pull`), you must restart the service.

```bash
cd /opt/llm-voice
git pull
source venv/bin/activate
pip install -r requirements.txt  # If requirements changed
sudo systemctl restart llm-voice
```

### Debugging Logs
If something is wrong, check the live logs:

*   **App Logs**: `sudo journalctl -u llm-voice -f`
*   **Ngrok Logs**: `sudo journalctl -u ngrok -f`
