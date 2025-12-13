from fastapi import FastAPI
from app.config import PORT
from app.routers.whatsapp import router as whatsapp_router
from app.routers.voice import router as voice_router

app = FastAPI(title="Unified LLM Server (WhatsApp & Voice)")

# Register Routers
app.include_router(whatsapp_router) # Handles /whatsapp
app.include_router(voice_router)    # Handles /twiml and /websocket

@app.get("/")
async def root():
    return {
        "message": "Unified Server Running",
        "endpoints": {
            "whatsapp": "POST /whatsapp",
            "voice_webhook": "POST /twiml",
            "voice_websocket": "WSS /websocket"
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=PORT)
