import asyncio
import json
import websockets
from fastapi import WebSocket
from app.config import OPENAI_API_KEY, VOICE_SYSTEM_MESSAGE, VOICE, LOG_EVENT_TYPES

class VoiceEventHandler:
    def __init__(self, websocket: WebSocket):
        self.websocket = websocket
        self.stream_sid = None
        self.openai_ws = None
        self.last_assistant_item_id = None  # Track current response for cancellation

    async def start(self):
        try:
            # Connection to OpenAI Realtime API
            url = "wss://api.openai.com/v1/realtime?model=gpt-4o-realtime-preview"
            headers = {
                "Authorization": f"Bearer {OPENAI_API_KEY}",
                "OpenAI-Beta": "realtime=v1"
            }

            async with websockets.connect(url, additional_headers=headers) as openai_ws:
                self.openai_ws = openai_ws
                await self.initialize_session()
                
                # Create tasks to read from both sockets simultaneously
                twilio_task = asyncio.create_task(self.receive_from_twilio())
                openai_task = asyncio.create_task(self.receive_from_openai())

                await asyncio.gather(twilio_task, openai_task)
                
        except websockets.exceptions.ConnectionClosed:
            print("OpenAI Connection Closed")
        except Exception as e:
            print(f"Error in VoiceEventHandler: {e}")

    async def initialize_session(self):
        """Send initial session update to OpenAI."""
        session_update = {
            "type": "session.update",
            "session": {
                "turn_detection": {"type": "server_vad"},
                "input_audio_format": "g711_ulaw",
                "output_audio_format": "g711_ulaw",
                "voice": VOICE,
                "instructions": VOICE_SYSTEM_MESSAGE,
                "modalities": ["text", "audio"],
                "temperature": 0.8,
            }
        }
        await self.openai_ws.send(json.dumps(session_update))

    async def handle_speech_started_event(self):
        """Handle interruption when user starts speaking."""
        print(f"User interrupted! Cancelling current response... (StreamSid: {self.stream_sid})")
        
        # Clear Twilio's audio buffer to stop playback immediately
        if self.stream_sid:
            clear_event = {
                "event": "clear",
                "streamSid": self.stream_sid
            }
            await self.websocket.send_json(clear_event)
            # print("Sent clear event to Twilio")
        
        # Cancel the current OpenAI response if one is in progress
        if self.last_assistant_item_id:
            cancel_event = {
                "type": "response.cancel"
            }
            await self.openai_ws.send(json.dumps(cancel_event))
            # print("Sent response.cancel to OpenAI")

    async def send_filler_audio(self):
        """
        Send a 'typing sound' or 'filler phrase' to Twilio to mask RAG latency.
        """
        if not self.stream_sid:
            return
            
        from app.config import FILLER_AUDIO
        
        if FILLER_AUDIO:
            # print(">> PLAYING FILLER AUDIO: 'Let me look that up for you...' [Typing Sounds] <<")
            try:
                await self.websocket.send_json({
                    "event": "media",
                    "streamSid": self.stream_sid,
                    "media": {"payload": FILLER_AUDIO}
                })
            except Exception as e:
                print(f"Error sending filler audio: {e}")
        else:
            # print(">> Filler audio requested but FILLER_AUDIO config is empty. Skipping. <<")
            pass

    async def receive_from_twilio(self):
        """Receive audio from Twilio and send to OpenAI."""
        try:
            async for message in self.websocket.iter_text():
                data = json.loads(message)
                event_type = data.get("event")
                
                if event_type == "media":
                    # Twilio sends base64 encoded audio
                    audio_payload = {
                        "type": "input_audio_buffer.append",
                        "audio": data["media"]["payload"]
                    }
                    if self.openai_ws:
                        await self.openai_ws.send(json.dumps(audio_payload))
                    
                elif event_type == "start":
                    self.stream_sid = data['start']['streamSid']
                    print(f"Incoming Stream Started: {self.stream_sid}")
                
                elif event_type == "stop":
                    print("Twilio Stream Stopped")
                    break
                    
        except Exception as e:
            print(f"Error processing Twilio message: {e}")

    async def receive_from_openai(self):
        """Receive audio from OpenAI and send to Twilio."""
        audio_chunks_received = 0
        from app.services.rag_client import RagClient
        rag_client = RagClient()

        try:
            async for message in self.openai_ws:
                data = json.loads(message)
                event_type = data.get("type")
                
                # Log events for debugging (except audio deltas which are too frequent)
                if event_type not in ["response.audio.delta"]:
                    print(f"OpenAI Event: {event_type}")
                
                if event_type == "session.created":
                    print("OpenAI Session Created Successfully")
                
                elif event_type == "session.updated":
                    print("OpenAI Session Updated")
                
                elif event_type == "input_audio_buffer.speech_started":
                    # User started speaking - handle interruption!
                    await self.handle_speech_started_event()
                    
                elif event_type == "response.audio.delta":
                    audio_chunks_received += 1
                    if audio_chunks_received == 1:
                        print(f"Receiving audio from OpenAI... (StreamSid: {self.stream_sid})")
                    
                    if "delta" in data and self.stream_sid:
                        audio_payload = {
                            "event": "media",
                            "streamSid": self.stream_sid,
                            "media": {
                                "payload": data['delta']
                            }
                        }
                        await self.websocket.send_json(audio_payload)

                elif event_type == "response.function_call_arguments.done":
                    # --- VOICE RAG LOGIC ---
                    print(f"Function Call Detected: {data}")
                    call_id = data.get("call_id")
                    args = json.loads(data.get("arguments", "{}"))
                    name = data.get("name") # Usually not in this event, checking implicit or previous
                    
                    # Note: Ideally we check the tool name. 
                    # But if we only have one tool, we can assume or check logic.
                    # The event structure usually implies specific detection.
                    
                    if "query" in args:
                        query = args["query"]
                        
                        # 1. MASK LATENCY
                        await self.send_filler_audio()
                        
                        # 2. QUERY RAG
                        print(f"Voice executing RAG Query: {query}")
                        rag_answer = await rag_client.query(query)
                        print(f"Voice RAG Result: {rag_answer[:50]}...")
                        
                        # 3. SEND OUTPUT BACK
                        await self.openai_ws.send(json.dumps({
                            "type": "conversation.item.create",
                            "item": {
                                "type": "function_call_output",
                                "call_id": call_id,
                                "output": str(rag_answer) # Ensure string
                            }
                        }))
                        
                        # 4. TRIGGER RESPONSE
                        await self.openai_ws.send(json.dumps({
                            "type": "response.create"
                        }))
                
                elif event_type == "conversation.item.created":
                    # Track assistant response items for cancellation
                    item = data.get("item", {})
                    if item.get("role") == "assistant":
                        self.last_assistant_item_id = item.get("id")
                        
                elif event_type == "response.audio.done":
                    audio_chunks_received = 0
                        
                elif event_type == 'error':
                    print(f"OpenAI ERROR: {data}")
                    
                elif event_type == 'response.done':
                    response = data.get('response', {})
                    status = response.get('status')
                    print(f"Response done - status: {status}")
                    
                    if status == 'failed':
                         print(f"FAILED DETAILS: {response.get('status_details')}")
                         
                    # Clear the item ID when response is complete
                    self.last_assistant_item_id = None

        except Exception as e:
            print(f"Error processing OpenAI message: {e}")
            import traceback
            traceback.print_exc()
