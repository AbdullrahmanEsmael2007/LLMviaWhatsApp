from fastapi import APIRouter, WebSocket, Request, Response
from fastapi.responses import HTMLResponse
from twilio.twiml.voice_response import VoiceResponse, Connect
from app.voice_handler import VoiceEventHandler

router = APIRouter()

@router.get("/", response_class=HTMLResponse)
async def index_page():
    return "<h1>Twilio Media Stream Server is Running</h1>"

@router.post("/twiml")
async def twiml_response(request: Request):
    """
    Twilio hits this endpoint when a call comes in.
    We respond with TwiML to connect the call to a Media Stream (WebSocket).
    """
    host = request.headers.get("host") or "localhost"
    
    response = VoiceResponse()
    response.say("Connected to Chatbot.")
    connect = Connect()
    connect.stream(url=f"wss://{host}/websocket")
    response.append(connect)
    
    return Response(content=str(response), media_type="application/xml")

@router.websocket("/websocket")
async def websocket_endpoint(websocket: WebSocket):
    """
    Handle the Twilio Media Stream WebSocket.
    DELEGATES logic to VoiceEventHandler.
    """
    await websocket.accept()
    print("Twilio Media Stream Connected")
    
    handler = VoiceEventHandler(websocket)
    await handler.start()
    
    print("Twilio Connection Closed")
