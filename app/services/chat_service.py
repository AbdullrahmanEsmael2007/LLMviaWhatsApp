import openai
import httpx
import json
import base64
import io
import asyncio
from app.config import OPENAI_API_KEY, WHATSAPP_SYSTEM_MESSAGE, TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN
from typing import Optional, Tuple
from app.services.rag_client import RagClient

# Initialize Clients
client = openai.AsyncOpenAI(api_key=OPENAI_API_KEY)
rag_client = RagClient()

conversation_history = defaultdict(list)

# Define Tools (Functions) for the Model
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "generate_image",
            "description": "Generate an image based on a text prompt using DALL-E 3.",
            "parameters": {
                "type": "object",
                "properties": {
                    "prompt": {
                        "type": "string",
                        "description": "The detailed description of the image to generate."
                    }
                },
                "required": ["prompt"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "query_knowledge_base",
            "description": "Use this tool to answer specific questions about files, documents, business rules, requirements, fees, or company data. If the user asks for specific values or procedures, ALWAYS use this tool.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The specific question or query to check in the knowledge base."
                    }
                },
                "required": ["query"]
            }
        }
    }
]

async def download_media(media_url: str) -> bytes:
    """Download media from Twilio URL (requires Basic Auth)."""
    async with httpx.AsyncClient() as http_client:
        response = await http_client.get(
             media_url, 
             auth=(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN),
             follow_redirects=True
        )
        return response.content

async def get_chat_response(
    message_body: str, 
    sender_number: str, 
    media_url: Optional[str] = None, 
    media_type: Optional[str] = None
) -> Tuple[str, Optional[str]]:
    """
    Process user message.
    Returns: (text_response, optional_media_url)
    """
    
    # Initialize history if empty
    if not conversation_history[sender_number]:
        conversation_history[sender_number].append({
            "role": "system", 
            "content": WHATSAPP_SYSTEM_MESSAGE
        })
    
    # --- 1. HANDLE INCOMING MEDIA ---
    
    # Audio (Voice Note) -> Whisper
    if media_type and media_type.startswith('audio/'):
        print(f"Processing Audio: {media_type}")
        try:
            audio_bytes = await download_media(media_url)
            ext = media_type.split('/')[-1].replace('x-', '') 
            audio_file = io.BytesIO(audio_bytes)
            audio_file.name = f"voice_note.{ext}" 
            
            transcription = await client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file
            )
            transcribed_text = transcription.text
            print(f"Transcribed: {transcribed_text}")
            
            # Combine with any text body
            if message_body:
                message_body = f"{message_body}\n[Transcribed Voice]: {transcribed_text}"
            else:
                message_body = transcribed_text
        except Exception as e:
            print(f"Audio error: {e}")
            return "I couldn't hear that voice note.", None

    # Construct User Message Content
    user_content = []
    if message_body:
        user_content.append({"type": "text", "text": message_body})
        
    # Image -> Vision
    if media_type and media_type.startswith('image/') and media_url:
        print(f"Processing Image: {media_url}")
        try:
            image_data = await download_media(media_url)
            base64_image = base64.b64encode(image_data).decode('utf-8')
            data_url = f"data:{media_type};base64,{base64_image}"
            
            user_content.append({
                "type": "image_url",
                "image_url": {"url": data_url}
            })
        except Exception as e:
            print(f"Image download error: {e}")
            user_content.append({"type": "text", "text": "[Image Download Failed]"})
        
    if user_content:
        conversation_history[sender_number].append({
            "role": "user",
            "content": user_content
        })
    
    # --- 2. GET AI RESPONSE (LOOP for Tools) ---
    try:
        response = await client.chat.completions.create(
            model="gpt-4o",
            messages=conversation_history[sender_number],
            tools=TOOLS,
            tool_choice="auto"
        )
        
        message = response.choices[0].message
        
        # Check for Tool Calls
        if message.tool_calls:
            conversation_history[sender_number].append(message)
            
            for tool_call in message.tool_calls:
                if tool_call.function.name == "generate_image":
                    args = json.loads(tool_call.function.arguments)
                    prompt = args.get("prompt")
                    print(f"Generating Image (Async): {prompt}")
                    
                    # Launch Background Task
                    asyncio.create_task(generate_and_send_image(sender_number, prompt))
                    
                    # CRITICAL: Append a logical "success" result for the tool so the history is valid
                    conversation_history[sender_number].append({
                        "tool_call_id": tool_call.id,
                        "role": "tool",
                        "name": "generate_image",
                        "content": "Image generation started in background."
                    })
                    
                    return "I am generating that image for you now 🎨... It might take a moment.", None
            
                elif tool_call.function.name == "query_knowledge_base":
                    args = json.loads(tool_call.function.arguments)
                    query = args.get("query")
                    print(f"Querying Knowledge Base: {query}")
                    
                    # Call RAG API
                    rag_answer = await rag_client.query(query)
                    print(f"RAG Answer: {rag_answer}")
                    
                    conversation_history[sender_number].append({
                        "tool_call_id": tool_call.id,
                        "role": "tool",
                        "name": "query_knowledge_base",
                        "content": rag_answer or "No relevant information found."
                    })
                    # Loop continues to get the final answer from GPT based on the tool output
            
            # --- 3. RE-CALL API AFTER TOOL OUTPUTS ---
            try:
                response = await client.chat.completions.create(
                    model="gpt-4o",
                    messages=conversation_history[sender_number],
                    tools=TOOLS,
                )
                message = response.choices[0].message
                
            except Exception as e:
                print(f"Error in second pass: {e}")
                return "I found some info but couldn't process it.", None

        # Normal Text Response
        reply = message.content
        conversation_history[sender_number].append({"role": "assistant", "content": reply})
        return reply, None

    except Exception as e:
        print(f"Error calling OpenAI: {e}")
        return "Sorry, something went wrong.", None

async def generate_and_send_image(to_number: str, prompt: str):
    """
    Generate image and send via Twilio Client (Outbound).
    """
    from twilio.rest import Client
    twilio_client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
    
    try:
        img_response = await client.images.generate(
            model="dall-e-3",
            prompt=prompt,
            size="1024x1024",
            quality="standard",
            n=1
        )
        image_url = img_response.data[0].url
        revised_prompt = img_response.data[0].revised_prompt
        
        # Send message via Twilio API
        twilio_client.messages.create(
            from_='whatsapp:+14155238886', # Sandbox Number
            body=f"Here is your image: {revised_prompt}",
            media_url=[image_url],
            to=to_number
        )
        print("Image sent successfully via Twilio API")
        
    except Exception as e:
        print(f"Async Generation Error: {e}")
        twilio_client.messages.create(
            from_='whatsapp:+14155238886',
            body="Sorry, I failed to generate the image.",
            to=to_number
        )
