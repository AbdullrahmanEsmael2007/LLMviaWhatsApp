# Download the helper library from https://www.twilio.com/docs/python/install
import os
from twilio.rest import Client

# Find your Account SID and Auth Token at twilio.com/console
# and set the environment variables. See http://twil.io/secure
from dotenv import load_dotenv
load_dotenv(dotenv_path='.env.local')

auth_token = os.getenv("TWILIO_AUTH_TOKEN")
account_sid = os.getenv("TWILIO_ACCOUNT_SID")
from_number = os.getenv("TWILIO_PHONE_NUMBER")
to_number = os.getenv("MY_PHONE_NUMBER")
client = Client(account_sid, auth_token)
other_number = "+966541389019"

# Fetch the server URL (e.g. ngrok) from env or use a placeholder
# You must have "SERVER_URL" in your .env.local, e.g. SERVER_URL=https://xxxx.ngrok.io
server_url = os.getenv("SERVER_URL")

if not server_url:
    print("Error: SERVER_URL is missing in .env.local. Please set it to your public ngrok URL.")
    exit(1)

call = client.calls.create(
    url=f"{server_url}/twiml",
    to=to_number,
    from_=from_number,
)

print(call.sid)