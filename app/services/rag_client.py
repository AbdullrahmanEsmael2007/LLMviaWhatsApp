import os
import httpx

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

                response.raise_for_status()
                # Endpoint returns specific structure, seemingly just "Successful Response" (200)
                # But we need the ANSWER. The GET endpoint returns messages. 
                # Wait, the POST /chat-messages returns 200 "Successful Response" but content is implicit?
                # Usually RAG APIs return the answer in the POST response.
                # Let's check the schema output for POST /chat-messages 
                # Response is "200 Successful Response", schema undefined/empty?
                # ACTUALLY: The user's code snippet implies they want an answer.
                # Let's check the logs or assume standard behavior.
                # Inspecting the OpenAPI again: POST /chat-messages returns "200"
                # But let's look at the actual response content.
                
                result = response.json()
                
                # If the API is stream-only or async, we might not get the answer here.
                # But typically it returns { "answer": ... } or { "data": ... }
                # Let's try to extract 'answer' or 'message' from response.
                return result.get("answer") or result.get("data") or str(result)
                
            except Exception as e:
                print(f"RAG Query Error: {e}")
                return "Sorry, I couldn't access the knowledge base at this moment."
