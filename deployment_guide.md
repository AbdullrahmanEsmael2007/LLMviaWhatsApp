# Deployment & Maintenance Guide (Azure/Linux)

This guide explains how to set up `uvicorn` (the app) and `ngrok` (the tunnel) as background services so they start automatically and stay running.

## Prerequisites

*   **Server Path**: Assumed to be `/opt/llm-voice`. Adjust if different.
*   **User**: Assumed to be the current user (e.g., `azureuser` or `ubuntu`).
*   **Virtual Environment**: Located at `/opt/llm-voice/venv`.

---

## 1. Setting up the App Service (`llm-voice`)

We will use `systemd` to keep the Python server running.

### 1.1 Create the Service File
Run: `sudo nano /etc/systemd/system/llm-voice.service`

Paste this content (adjusting User/Group/Paths as needed):

```ini
[Unit]
Description=LLM Voice Assistant (Uvicorn)
After=network.target

[Service]
# CHANGE THESE TO YOUR USERNAME/GROUP
User=azureuser
Group=azureuser

# The directory where your code lives
WorkingDirectory=/opt/llm-voice

# Environment variables (or use EnvironmentFile=/opt/llm-voice/.env)
EnvironmentFile=/opt/llm-voice/.env
Environment="PATH=/opt/llm-voice/venv/bin"

# The command to start the server
ExecStart=/opt/llm-voice/venv/bin/uvicorn main:app --host 0.0.0.0 --port 5050

# Auto-restart if it crashes
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
```

### 1.2 Enable and Start
```bash
sudo systemctl daemon-reload
sudo systemctl enable llm-voice
sudo systemctl start llm-voice
```

### 1.3 Check Status
```bash
sudo systemctl status llm-voice
```

---

## 2. Setting up Ngrok Service (`ngrok`)

Running ngrok as a service ensures the tunnel stays open.

> **Important**: If you are on the **Free Tier**, your URL changes every time ngrok restarts. You must update the Twilio Console manually each time. We highly recommend a paid plan or a static domain if possible.

### 2.1 Create the Service File
Run: `sudo nano /etc/systemd/system/ngrok.service`

```ini
[Unit]
Description=Ngrok Tunnel
After=network.target

[Service]
User=azureuser
Group=azureuser
WorkingDirectory=/opt/llm-voice

# Command to start ngrok on port 5050
# If you have a config file, add: --config=/opt/llm-voice/ngrok.yml
# If you have a static domain, add: --domain=your-domain.ngrok-free.app
ExecStart=/usr/local/bin/ngrok http 5050 --log=stdout

Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
```

### 2.2 Enable and Start
```bash
sudo systemctl daemon-reload
sudo systemctl enable ngrok
sudo systemctl start ngrok
```

### 2.3 Get the Public URL
To see the URL assigned by ngrok:
```bash
curl http://localhost:4040/api/tunnels | python3 -c "import sys, json; print(json.load(sys.stdin)['tunnels'][0]['public_url'])"
```
*Copy this URL to your Twilio Console.*

---

## 3. Maintenance Cheat Sheet

### Restarting the App (After code changes)
Whenever you `git pull` new code, you must restart the app:
```bash
# 1. Pull changes
cd /opt/llm-voice
git pull

# 2. Update dependencies (Optional, if requirements.txt changed)
source venv/bin/activate
pip install -r requirements.txt

# 3. Restart Service
sudo systemctl restart llm-voice
```

### Restarting Ngrok
```bash
sudo systemctl restart ngrok
# Remember to check the new URL if you don't have a static domain!
```

### Viewing Logs (Debugging)
If something isn't working, check the logs:

**App Logs:**
```bash
sudo journalctl -u llm-voice -f
```

**Ngrok Logs:**
```bash
sudo journalctl -u ngrok -f
```
