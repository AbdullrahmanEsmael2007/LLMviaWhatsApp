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
        
        # Endpoint provided: POST /chat-messages/voice (with session_id query param likely)
        # Note: 'voice' in URL suggests it might return audio or expect audio? 
        # But for RAG usually it's text. We send text.
        
        url = f"{self.base_url}/chat-messages/voice"
        params = {"session_id": RAG_SESSION_ID}
        
        # We need to structure the body. Usually { "message": "..." } or similar.
        # Without docs, we assume standard: { "content": message } or { "query": message }
        # Let's try { "message": message }
        body = { "message": message } # Generic guess, needs verification if docs unavailable
        
        headers = {}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(url, params=params, json=body, headers=headers)
                
                if response.status_code == 401:
                    # Token expired, retry once
                    print("Token expired, refreshing...")
                    await self.login()
                    headers["Authorization"] = f"Bearer {self.token}"
                    response = await client.post(url, params=params, json=body, headers=headers)

                response.raise_for_status()
                result = response.json()
                
                # Parse result. Usually content is in "answer" or "data"
                # We return the raw text answer.
                return result.get("answer") or result.get("data") or str(result)
                
            except Exception as e:
                print(f"RAG Query Error: {e}")
                return "Sorry, I couldn't access the knowledge base at this moment."
