import os
import openai
import base64
import audioop
import wave
import io
from dotenv import load_dotenv

# Load Env
load_dotenv('.env.local')
client = openai.OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

def generate_filler():
    print("Generating audio from OpenAI TTS...")
    response = client.audio.speech.create(
        model="tts-1",
        voice="shimmer",
        input="Let me check that for you in our knowledge base...",
        response_format="pcm"  # Raw samples (24kHz mono usually)
    )
    
    # OpenAI pcm is 24000Hz, 16-bit mono
    raw_audio = response.content
    
    # 1. Resample 24000 -> 8000
    # audioop.ratecv(fragment, width, nchannels, inrate, outrate, state[, weightA[, weightB]])
    # width=2 (16-bit)
    print("Resampling to 8000Hz...")
    formatted_audio, _ = audioop.ratecv(raw_audio, 2, 1, 24000, 8000, None)
    
    # 2. Convert to u-law
    print("Encoding to u-law...")
    ulaw_audio = audioop.lin2ulaw(formatted_audio, 2)
    
    # 3. Base64 Encode
    b64_string = base64.b64encode(ulaw_audio).decode('utf-8')
    
    print("\nSUCCESS! Here is your FILLER_AUDIO string (copy this to .env):")
    print("-" * 20)
    print(b64_string)
    print("-" * 20)
    
    # Also save to file for verification
    with open("filler.ulaw", "wb") as f:
        f.write(ulaw_audio)
    print("Saved raw u-law to filler.ulaw")

if __name__ == "__main__":
    generate_filler()
