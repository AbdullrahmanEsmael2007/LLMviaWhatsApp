import os
from dotenv import load_dotenv

load_dotenv(dotenv_path='.env.local')

OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
TWILIO_ACCOUNT_SID = os.getenv('TWILIO_ACCOUNT_SID')
TWILIO_AUTH_TOKEN = os.getenv('TWILIO_AUTH_TOKEN')
PORT = int(os.getenv('PORT', 5050))

# WhatsApp Configuration
WHATSAPP_SYSTEM_MESSAGE = (
    "You are a helpful and concise WhatsApp assistant made by RMG for Saudi Business Center. Talk in Arabic at the start, but if the user is talking in another language, switch to that language."
    "ROUTING RULES: "
    "1. General Chat (Greetings, 'how are you', etc.): Answer directly. "
    "2. Specific Questions (About the company, files, rules, data, requirements, etc.): You DO NOT know these answers. "
    "You MUST use the `query_knowledge_base` tool for ANY question that requires internal or specific knowledge using the arabic language but then retranslate it to the users language. Follow this process: "
    "1. Use the `query_knowledge_base` tool to get the answer in arabic even if the user is not in arabic. "
    "2. Translate the answer to the users language. "
    "3. Answer the user in the users language. "
    "When you answer, do not use markdown except for singular star (*) for bold and singular underscore (_) for italic."
    "If you are not sure, always use the query_knowledge_base tool to get the answer. You can overuse it with no penalty."
    "It is favourable that you use it as much as possible."
)

# Voice Configuration
VOICE_SYSTEM_MESSAGE = (
    "You are a helpful and concise voice assistant. You are made by RMG for Saudi Business Center. Talk in arabic only"
)
VOICE = 'ash'
LOG_EVENT_TYPES = [
    'response.content.done', 'rate_limits.updated', 'response.done',
    'input_audio_buffer.committed', 'input_audio_buffer.speech_stopped',
    'input_audio_buffer.speech_started', 'session.created'
]

if not OPENAI_API_KEY:
    raise ValueError('Missing the OPENAI_API_KEY environment variable.')

# RAG API Configuration
RAG_API_BASE_URL = os.getenv('RAG_API_BASE_URL', 'https://40-79-241-100.sslip.io/api/v1')
RAG_EMAIL = os.getenv('RAG_EMAIL', 'admin@rmg-sa.com')
RAG_PASSWORD = os.getenv('RAG_PASSWORD', 'Admin@123456')
RAG_SESSION_ID = os.getenv('RAG_SESSION_ID', '54e7d7fa-4496-43c0-88f5-9ceea5bf4eb5')

# Audio Configuration
# Base64 string for "Let me check that..." + Typing sounds. 
# Leave empty to disable filler audio.
FILLER_AUDIO = os.getenv('FILLER_AUDIO', '')
