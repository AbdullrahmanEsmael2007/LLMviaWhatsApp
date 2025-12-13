import os
from dotenv import load_dotenv

load_dotenv(dotenv_path='.env.local')

OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
TWILIO_ACCOUNT_SID = os.getenv('TWILIO_ACCOUNT_SID')
TWILIO_AUTH_TOKEN = os.getenv('TWILIO_AUTH_TOKEN')
PORT = int(os.getenv('PORT', 5050))

# WhatsApp Configuration
WHATSAPP_SYSTEM_MESSAGE = (
    "You are a helpful and concise WhatsApp assistant. You are made by RMG, a saudi company focused on digitalization and automation."
)

# Voice Configuration
VOICE_SYSTEM_MESSAGE = (
    "You are Antigravity, an AI agentic coding assistant. You are helpful, concise, and professional."
)
VOICE = 'alloy'
LOG_EVENT_TYPES = [
    'response.content.done', 'rate_limits.updated', 'response.done',
    'input_audio_buffer.committed', 'input_audio_buffer.speech_stopped',
    'input_audio_buffer.speech_started', 'session.created'
]

if not OPENAI_API_KEY:
    raise ValueError('Missing the OPENAI_API_KEY environment variable.')
