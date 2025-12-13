from fastapi import APIRouter, Request, Form, Response
from twilio.twiml.messaging_response import MessagingResponse
# Import form the new services location (we will move chat_service.py next)
from app.services.chat_service import get_chat_response

router = APIRouter()

@router.post("/whatsapp")
async def whatsapp_reply(
    Body: str = Form(""), 
    From: str = Form(...),
    NumMedia: int = Form(0),
    MediaUrl0: str = Form(None),
    MediaContentType0: str = Form(None)
):
    """
    Handle incoming WhatsApp messages (Text, Audio, Images).
    """
    # Get response from the Chat Service
    reply_text, media_url = await get_chat_response(
        message_body=Body, 
        sender_number=From,
        media_url=MediaUrl0,
        media_type=MediaContentType0
    )
    
    # Create TwiML Response
    response = MessagingResponse()
    msg = response.message(reply_text)

    if media_url:
        msg.media(media_url)
    
    return Response(content=str(response), media_type="application/xml")
