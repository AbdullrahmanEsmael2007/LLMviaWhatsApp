import os
import httpx
import json

from app.config import RAG_API_BASE_URL, RAG_EMAIL, RAG_PASSWORD, RAG_SESSION_ID

class RagClient:
    def __init__(self):
        self.base_url = RAG_API_BASE_URL
        self.token = None

    async def login(self):
        """Authenticate and get a JWT token."""
        url = f"{self.base_url}/auth/login"
        payload = {
            "email": RAG_EMAIL,
            "password": RAG_PASSWORD
        }
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(url, json=payload)
                response.raise_for_status()
                data = response.json()
                # Access token might be directly in data like "token" or "access_token"
                # Looking at standard implementations, let's assume "data"->"token" or just "token"
                # We will debug this if it fails, but standard is usually data['data']['token'] or data['token']
                # Let's start with a safe check
                if "data" in data and "token" in data["data"]:
                     self.token = data["data"]["token"]
                elif "token" in data:
                     self.token = data["token"]
                elif "access_token" in data:
                     self.token = data["access_token"]
                else:
                     print(f"Login Response unexpected format: {data}")
            except Exception as e:
                print(f"RAG Login Failed: {e}")

    async def query(self, message: str) -> str:
        """Send a message to the RAG chat API."""
        if not self.token:
            await self.login()
        
        # CORRECT ENDPOINT: Use text chat endpoint, not voice
        url = f"{self.base_url}/chat-messages" 
        
        # Schema requires multipart/form-data for 'message' and 'session_id'
        # based on ChatMessageCreateModel schema in OpenAPI
        data = {
            "session_id": RAG_SESSION_ID,
            "message": message,
            "styled_answer": "false" # Optional, purely text preference
        }
        
        headers = {}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"

        async with httpx.AsyncClient() as client:
            try:
                # httpx handles multipart/form-data when using 'data' param (not json)
                response = await client.post(url, data=data, headers=headers)
                
                if response.status_code == 401:
                    print("Token expired, refreshing...")
                    await self.login()
                    headers["Authorization"] = f"Bearer {self.token}"
                    response = await client.post(url, data=data, headers=headers)

                if response.status_code == 422:
                    print(f"Validation Error: {response.text}")
                    return "I found some info but the system rejected the format."

                # The API appears to return newline-delimited JSON (NDJSON) or a stream.
                # 'Extra data' error means multiple JSON objects are in the response.
                # We will handle this by splitting lines and looking for the answer.
                response_text = response.text
                print(f"RAG Raw Response: {response_text[:200]}...") # Log start of response for debug
                
                final_answer = ""
                
                # Try to parse each line as a separate JSON object
                for line in response_text.strip().split('\n'):
                    if not line.strip():
                        continue
                    try:
                        data = json.loads(line)
                        # Accumulate answer if it's streamed, or pick the final one
                        # Common patterns: 'answer', 'message', 'delta'
                        if "answer" in data:
                            final_answer = data["answer"]
                        elif "data" in data: 
                            final_answer = data["data"]
                            
                    except json.JSONDecodeError:
                        continue
                
                if final_answer:
                    return final_answer
                
                # Fallback: if single JSON parsing failed above (unlikely if loop worked), try whole body
                try:
                    return response.json().get("answer")
                except:
                    return f"Received info but couldn't parse: {response_text[:100]}"
                
            except Exception as e:
                print(f"RAG Query Error: {e}")
                return "Sorry, I couldn't access the knowledge base at this moment."
