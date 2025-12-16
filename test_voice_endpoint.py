from fastapi import Request
from app.routers.voice import twiml_response
import asyncio
from unittest.mock import MagicMock

async def test_twiml():
    # Mock Request
    request = MagicMock()
    request.headers.get.return_value = "test.ngrok.io"
    
    print("Testing /twiml endpoint...")
    try:
        response = await twiml_response(request)
        print("Status Code:", response.status_code)
        print("Body:", response.body.decode())
    except Exception as e:
        print("ERROR:", e)

if __name__ == "__main__":
    asyncio.run(test_twiml())
