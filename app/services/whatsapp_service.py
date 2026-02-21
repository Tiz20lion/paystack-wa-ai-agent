"""
WhatsApp service integration using Twilio API.
Handles incoming messages and sends responses for the financial agent.
"""

import asyncio
import httpx
from io import BytesIO
from typing import Dict, Optional, Any
from twilio.rest import Client
from twilio.twiml.messaging_response import MessagingResponse
from twilio.request_validator import RequestValidator
from fastapi import HTTPException
from app.utils.logger import get_logger
from app.utils.config import settings

logger = get_logger("whatsapp_service")


class WhatsAppService:
    """WhatsApp service using Twilio API."""
    
    def __init__(self):
        self.client = None
        self.webhook_url = getattr(settings, 'webhook_url', 'https://your-domain.com/webhook')
        self.validator = None
        self.initialize_client()
        self.initialize_validator()
    
    def initialize_client(self):
        """Initialize Twilio client."""
        try:
            account_sid = getattr(settings, 'twilio_account_sid', None)
            auth_token = getattr(settings, 'twilio_auth_token', None)
            
            if not account_sid or not auth_token:
                logger.warning("Twilio credentials not configured")
                return
            
            self.client = Client(account_sid, auth_token)
            logger.info("Twilio client initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize Twilio client: {e}")
    
    def initialize_validator(self):
        """Initialize Twilio request validator for signature verification."""
        try:
            auth_token = getattr(settings, 'twilio_auth_token', None)
            if auth_token:
                self.validator = RequestValidator(auth_token)
                logger.info("Twilio request validator initialized")
            else:
                logger.warning("Twilio auth token not configured - webhook signature verification disabled")
        except Exception as e:
            logger.error(f"Failed to initialize Twilio validator: {e}")
    
    async def send_message(self, to: str, message: str) -> Dict[str, Any]:
        """Send a WhatsApp message."""
        if not self.client:
            logger.error("Twilio client not initialized")
            return {"success": False, "error": "Twilio client not initialized"}
        
        try:
            # Ensure number is in WhatsApp format
            if not to.startswith('whatsapp:'):
                to = f"whatsapp:{to}"
            
            # Get the from number
            from_number = getattr(settings, 'twilio_whatsapp_number', None)
            if not from_number:
                logger.error("Twilio WhatsApp number not configured")
                return {"success": False, "error": "WhatsApp number not configured"}
            
            if from_number and not from_number.startswith('whatsapp:'):
                from_number = f"whatsapp:{from_number}"
            
            # Send message
            message_instance = self.client.messages.create(
                body=message,
                from_=from_number,
                to=to
            )
            
            logger.info(f"Message sent to {to}: {message_instance.sid}")
            
            return {
                "success": True,
                "message_sid": message_instance.status,
                "status": message_instance.status
            }
            
        except Exception as e:
            logger.error(f"Failed to send WhatsApp message: {e}")
            return {"success": False, "error": str(e)}
    
    async def send_message_with_image(self, to: str, message: str, image_url: str) -> Dict[str, Any]:
        """Send a WhatsApp message with an image."""
        if not self.client:
            logger.error("Twilio client not initialized")
            return {"success": False, "error": "Twilio client not initialized"}
        
        try:
            # Ensure number is in WhatsApp format
            if not to.startswith('whatsapp:'):
                to = f"whatsapp:{to}"
            
            # Get the from number
            from_number = getattr(settings, 'twilio_whatsapp_number', None)
            if from_number and not from_number.startswith('whatsapp:'):
                from_number = f"whatsapp:{from_number}"
            
            # Send message with image
            message_instance = self.client.messages.create(
                body=message,
                media_url=image_url,
                from_=from_number,
                to=to
            )
            
            logger.info(f"Message with image sent to {to}: {message_instance.sid}")
            
            return {
                "success": True,
                "message_sid": message_instance.status,
                "status": message_instance.status
            }
            
        except Exception as e:
            logger.error(f"Failed to send WhatsApp message with image: {e}")
            return {"success": False, "error": str(e)}
    
    async def send_receipt_image(self, to: str, image_path: str, caption: str = "✅ Transfer successful! Here's your receipt.") -> Dict[str, Any]:
        """Send a receipt image via WhatsApp."""
        if not self.client:
            logger.error("Twilio client not initialized")
            return {"success": False, "error": "Twilio client not initialized"}
        
        try:
            import os
            
            # Check if image file exists
            if not os.path.exists(image_path):
                logger.error(f"Receipt image not found: {image_path}")
                return {"success": False, "error": "Receipt image not found"}
            
            # For local files, we need to upload to a publicly accessible URL
            # In production, you'd upload to AWS S3, Cloudinary, or similar
            # For now, we'll use a fallback text message
            
            # Try to create a temporary public URL or use local file serving
            public_url = await self._make_image_publicly_accessible(image_path)
            
            if public_url:
                return await self.send_message_with_image(to, caption, public_url)
            else:
                # Fallback to text message if image hosting fails
                fallback_message = f"{caption}\n\n📄 Receipt details saved and can be accessed in your transaction history."
                return await self.send_message(to, fallback_message)
            
        except Exception as e:
            logger.error(f"Failed to send receipt image: {e}")
            # Fallback to text message
            fallback_message = f"{caption}\n\n📄 Receipt generated but could not be sent as image. Details saved in your transaction history."
            return await self.send_message(to, fallback_message)
    
    async def _make_image_publicly_accessible(self, image_path: str) -> Optional[str]:
        """Make a local image file publicly accessible via a URL."""
        try:
            import os
            import asyncio
            from pathlib import Path
            
            # Check if image file exists and has content
            if not os.path.exists(image_path):
                logger.error(f"Receipt image not found: {image_path}")
                return None
                
            # Wait a moment to ensure file is fully written
            await asyncio.sleep(0.1)
            
            # Verify file has content
            file_size = os.path.getsize(image_path)
            if file_size == 0:
                logger.error(f"Receipt image file is empty: {image_path}")
                return None
            
            # Get the base URL of your API server
            base_url = getattr(settings, 'api_base_url', 'http://127.0.0.1:8000')
            
            # Ensure base_url doesn't end with slash
            base_url = base_url.rstrip('/')
            
            # The image should already be in the receipts/output directory
            # Just construct the public URL using the /receipts endpoint
            filename = os.path.basename(image_path)
            
            # Return the public URL using the /receipts endpoint we set up
            public_url = f"{base_url}/receipts/{filename}"
            
            logger.info(f"Receipt image accessible at: {public_url}")
            logger.debug(f"Receipt file size: {file_size} bytes")
            
            return public_url
            
        except Exception as e:
            logger.error(f"Failed to make image publicly accessible: {e}")
            return None
    
    async def download_media(self, media_url: str) -> Optional[bytes]:
        """Download media from WhatsApp message."""
        if not self.client:
            logger.error("Twilio client not initialized")
            return None
        
        try:
            # NOTE: Twilio WhatsApp API media access needs proper handling
            # media_instance = self.client.media.get(media_url.split('/')[-1])
            
            # Download the media content directly with proper authentication
            async with httpx.AsyncClient() as client:
                # Get credentials safely
                username = getattr(settings, 'twilio_account_sid', None) 
                password = getattr(settings, 'twilio_auth_token', None)
                
                if not username or not password:
                    logger.error("Missing Twilio credentials for media download")
                    return None
                
                response = await client.get(
                    media_url, 
                    auth=(username, password)
                )
                
                if response.status_code == 200:
                    return response.content
                else:
                    logger.error(f"Failed to download media: {response.status_code}")
                    return None
                    
        except Exception as e:
            logger.error(f"Failed to download media: {e}")
            return None
    
    def create_webhook_response(self, message: str) -> str:
        """Create TwiML response for webhook."""
        response = MessagingResponse()
        response.message(message)
        return str(response)
    
    def validate_webhook_request(
        self,
        request_data: Dict[str, Any],
        request_url: str = None,
        signature: str = None,
        validation_url: str = None,
    ) -> bool:
        """Validate incoming webhook request with Twilio signature verification."""
        if 'From' not in request_data or 'MessageSid' not in request_data:
            logger.warning("Missing required field: From or MessageSid")
            return False
        has_body = 'Body' in request_data
        has_media = int(request_data.get('NumMedia', 0)) > 0
        if not has_body and not has_media:
            return True

        if not self.validator or not signature:
            return True
        urls_to_try = []
        if validation_url:
            urls_to_try.append(validation_url.strip())
        if request_url and request_url not in urls_to_try:
            urls_to_try.append(request_url)
        if not urls_to_try:
            return True
        params = {}
        for k, v in request_data.items():
            if hasattr(v, "read"):
                continue
            params[k] = v[0] if isinstance(v, (list, tuple)) else v
        params = {k: str(v) for k, v in params.items()}
        for url in urls_to_try:
            try:
                if self.validator.validate(url, params, signature):
                    logger.debug("Twilio webhook signature verified successfully")
                    return True
            except Exception as e:
                logger.debug(f"Signature validation with URL failed: {e}")
        logger.warning(f"Invalid Twilio webhook signature from {request_data.get('From', 'Unknown')}")
        return False

    def extract_user_info(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract user information from webhook request."""
        phone_number = request_data.get('From', '').replace('whatsapp:', '')
        
        return {
            'user_id': phone_number,
            'phone_number': phone_number,
            'message_sid': request_data.get('MessageSid'),
            'profile_name': request_data.get('ProfileName', ''),
            'timestamp': request_data.get('timestamp', '')
        }
    
    def extract_message_content(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract message content from webhook request."""
        return {
            'text': request_data.get('Body', ''),
            'media_url': request_data.get('MediaUrl0', ''),
            'media_type': request_data.get('MediaContentType0', ''),
            'num_media': int(request_data.get('NumMedia', 0))
        }
    
    def is_spam_message(self, message_text: str, from_number: str) -> bool:
        """Detect spam/system messages that should be ignored."""
        if not message_text:
            return True
        
        message_lower = message_text.lower()
        
        # System/marketing message patterns
        spam_patterns = [
            # WhatsApp business verification spam
            "business verification",
            "verify your business",
            "solution provider",
            "facebook.com/business/help",
            "whatsapp benefits",
            "register up to",
            "authenticate your business",
            "display name in chats",
            
            # Other marketing/system messages
            "this is an automated message",
            "do not reply",
            "unsubscribe",
            "promotional",
            "marketing message",
            "advertisement",
            "*open more doors to growth*",
            
            # Generic system notifications
            "system notification",
            "account notification",
            "service update"
        ]
        
        # Check for spam patterns
        for pattern in spam_patterns:
            if pattern in message_lower:
                logger.info(f"Spam message detected from {from_number}: {pattern}")
                return True
        
        # Check for suspicious phone numbers (like system numbers)
        system_numbers = [
            "+16465894168",  # Known WhatsApp system number
            "+19999999999",  # Common test numbers
            "+12345678900"
        ]
        
        if from_number.replace('whatsapp:', '') in system_numbers:
            logger.info(f"System number detected: {from_number}")
            return True
        
        # Check message length - extremely long messages are often spam
        if len(message_text) > 1000:
            logger.info(f"Very long message detected (likely spam): {len(message_text)} chars")
            return True
        
        return False

    async def handle_webhook(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle incoming webhook request with spam filtering."""
        try:
            # Validate request
            if not self.validate_webhook_request(request_data):
                raise HTTPException(status_code=400, detail="Invalid webhook request")
            
            # Extract user and message info
            user_info = self.extract_user_info(request_data)
            message_content = self.extract_message_content(request_data)
            
            # Check for spam messages and ignore them
            if self.is_spam_message(message_content['text'], user_info['phone_number']):
                logger.info(f"Ignoring spam message from {user_info['user_id']}")
                return {
                    'user_info': user_info,
                    'message_content': message_content,
                    'raw_request': request_data,
                    'is_spam': True,
                    'ignored': True
                }
            
            logger.info(f"Received message from {user_info['user_id']}: {message_content['text']}")
            
            return {
                'user_info': user_info,
                'message_content': message_content,
                'raw_request': request_data,
                'is_spam': False,
                'ignored': False
            }
            
        except Exception as e:
            logger.error(f"Error handling webhook: {e}")
            raise HTTPException(status_code=500, detail="Internal server error")
    
    async def send_typing_indicator(self, to: str):
        """Send typing indicator (not directly supported by Twilio WhatsApp)."""
        # Note: Twilio WhatsApp API doesn't support typing indicators
        # This is a placeholder for future implementation
        pass
    
    async def send_status_update(self, to: str, status: str):
        """Send status update to user."""
        status_messages = {
            'processing': '🔄 Processing your request...',
            'checking_balance': '💰 Checking your balance...',
            'resolving_account': '🔍 Resolving account details...',
            'preparing_transfer': '📤 Preparing transfer...',
            'awaiting_confirmation': '⏳ Awaiting confirmation...',
            'processing_transfer': '💸 Processing transfer...',
            'completed': '✅ Process completed!',
            'error': '❌ Something went wrong. Please try again.'
        }
        
        message = status_messages.get(status, f"Status: {status}")
        await self.send_message(to, message)
    
    async def send_receipt(self, to: str, transfer_details: Dict[str, Any]):
        """Send transfer receipt to user."""
        receipt = f"""
📧 **Transfer Receipt**

Amount: ₦{transfer_details.get('amount', 0) / 100:,.2f}
To: {transfer_details.get('recipient_name', 'Unknown')}
Bank: {transfer_details.get('bank_name', 'Unknown')}
Reference: {transfer_details.get('reference', 'N/A')}
Date: {transfer_details.get('date', 'N/A')}
Status: {transfer_details.get('status', 'Unknown')}

Thank you for using our service! 🙏
"""
        await self.send_message(to, receipt)
    
    async def send_balance_summary(self, to: str, balance: int):
        """Send balance summary to user."""
        message = f"""
💰 **Account Balance**

Available: ₦{balance / 100:,.2f}

Use this balance to send money to anyone with just their account number and bank name!
"""
        await self.send_message(to, message)
    
    async def send_help_message(self, to: str):
        """Send help message to user."""
        help_text = """
🤖 **How to use your Financial Assistant**

💰 **Check Balance:**
• "balance" or "check balance"

🏦 **Resolve Account:**
• "0123456789 Access Bank"

💸 **Send Money:**
• "send 5000 to John"
• "transfer 2k to mom"

📊 **View History:**
• "history" or "my transactions"

🔄 **During Transfer:**
• Confirm with "yes" or "confirm"
• Cancel with "no" or "cancel"

Just chat naturally! I understand Nigerian banking terminology.
"""
        await self.send_message(to, help_text)
    
    async def send_error_message(self, to: str, error: str):
        """Send error message to user."""
        message = f"""
❌ **Error**

{error}

Need help? Send "help" for instructions.
"""
        await self.send_message(to, message)


# Global instance
whatsapp_service = WhatsAppService() 