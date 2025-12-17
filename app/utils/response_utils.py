"""
Response utilities for handling JSON serialization and LLM-refined responses.
"""

import json
from datetime import datetime
from typing import Dict, List, Any, Optional, Union
from app.utils.logger import logger
from app.schemas.core import LLMRefinedResponse, TransactionSummary
from openai import AsyncOpenAI


class ResponseFormatter:
    """Unified response formatter with LLM refinement capabilities."""
    
    def __init__(self, ai_client: Optional[AsyncOpenAI] = None, ai_model: str = "gpt-4o-mini"):
        self.ai_client = ai_client
        self.ai_model = ai_model
        self.ai_enabled = ai_client is not None
    
    def to_json_safe_dict(self, data: Any) -> Any:
        """Convert data to JSON-safe format, handling datetime objects."""
        if isinstance(data, datetime):
            return data.isoformat()
        elif isinstance(data, dict):
            return {key: self.to_json_safe_dict(value) for key, value in data.items()}
        elif isinstance(data, list):
            return [self.to_json_safe_dict(item) for item in data]
        else:
            return data
    
    def safe_json_dumps(self, data: Any, **kwargs) -> str:
        """Safe JSON serialization with datetime handling."""
        try:
            safe_data = self.to_json_safe_dict(data)
            return json.dumps(safe_data, **kwargs)
        except Exception as e:
            logger.error(f"JSON serialization failed: {e}")
            return "{}"
    
    async def refine_with_llm(self, template_response: str, context: Dict, intent: str) -> str:
        """Refine a template response using LLM."""
        if not self.ai_enabled or not self.ai_client:
            return template_response
            
        try:
            system_prompt = f"""You are TizBot, a smart and conversational Nigerian banking assistant. Improve the given template response to be more conversational and natural.

🤖 **YOUR PERSONALITY:**
- Name: TizBot - friendly, smart, conversational
- Use Nigerian expressions naturally
- Be helpful and engaging
- Sound like a smart friend, not a robot

Context: {self.safe_json_dumps(context)}
Intent: {intent}

Guidelines:
- Keep the same factual information
- Make it more conversational and friendly
- Use appropriate emojis
- Keep response concise (under 200 words)
- Maintain Nigerian banking context
"""
            
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Improve this response: {template_response}"}
            ]
            
            completion = await self.ai_client.chat.completions.create(
                model=self.ai_model,
                messages=messages,  # type: ignore
                max_tokens=250,
                temperature=0.7
            )
            
            refined_response = completion.choices[0].message.content
            if refined_response and refined_response.strip():
                return refined_response.strip()
                
        except Exception as e:
            logger.error(f"LLM response refinement failed: {e}")
        
        return template_response
    
    def format_money(self, amount: Union[int, float]) -> str:
        """Format money amount in Nigerian Naira."""
        try:
            # Convert from kobo to naira if needed
            if isinstance(amount, int) and amount > 10000:
                amount = float(amount) / 100
            return f"₦{amount:,.2f}"
        except Exception:
            return f"₦{amount}"
    
    def format_transaction_summary(self, transactions: List[Dict]) -> TransactionSummary:
        """Format transaction summary with proper datetime handling."""
        try:
            total_amount = 0
            transaction_items = []
            
            for tx in transactions:
                amount = tx.get('amount', 0)
                if isinstance(amount, (int, float)):
                    total_amount += amount
                
                # Handle datetime serialization
                created_at = tx.get('created_at')
                if isinstance(created_at, str):
                    date_display = created_at[:10]
                elif isinstance(created_at, datetime):
                    date_display = created_at.strftime('%Y-%m-%d')
                else:
                    date_display = 'N/A'
                
                transaction_items.append({
                    'amount': self.format_money(amount),
                    'status': tx.get('status', 'unknown'),
                    'date': date_display,
                    'channel': tx.get('channel', 'unknown'),
                    'reference': tx.get('reference', '')
                })
            
            return TransactionSummary(
                total_transactions=len(transactions),
                total_amount=self.format_money(total_amount),
                transactions=transaction_items,
                period="recent"
            )
            
        except Exception as e:
            logger.error(f"Transaction summary formatting failed: {e}")
            return TransactionSummary(
                total_transactions=0,
                total_amount=self.format_money(0),
                transactions=[],
                period="recent"
            )
    
    def format_recipients_list(self, local_recipients: List[Dict], paystack_recipients: List[Dict]) -> str:
        """Format recipients list with proper structure."""
        try:
            total_count = len(local_recipients) + len(paystack_recipients)
            
            if total_count == 0:
                return """You don't have any saved recipients yet! 

To save contacts:
• Send money with their details: "Send 5k to 0123456789 access bank"  
• I'll ask if you want to save them as a contact
• Or give me their details: "Send to John at 1234567890 kuda"

Next time just say: "Send money to John" 💰"""
            
            response = f"📋 **Your Recipients & Contacts** ({total_count} total):\n\n"
            
            # Show local recipients
            if local_recipients:
                response += f"💾 **App Saved Contacts** ({len(local_recipients)}):\n"
                for i, recipient in enumerate(local_recipients[:8], 1):
                    usage = recipient.get('use_count', 0)
                    usage_text = f" (used {usage}x)" if usage > 0 else ""
                    nickname = recipient.get('nickname') or recipient.get('name', 'Unknown')
                    
                    response += f"{i}. **{nickname}**{usage_text}\n"
                    response += f"   👤 {recipient.get('name', 'Unknown')}\n"
                    response += f"   🏦 {recipient.get('bank_name', 'Unknown Bank')} - {recipient.get('account_number', '')}\n\n"
                
                if len(local_recipients) > 8:
                    response += f"... and {len(local_recipients) - 8} more app contacts\n\n"
            
            # Show Paystack recipients
            if paystack_recipients:
                response += f"🏦 **Paystack Recipients** ({len(paystack_recipients)}):\n"
                for i, recipient in enumerate(paystack_recipients[:5], 1):
                    name = recipient.get('name', 'Unknown')
                    details = recipient.get('details', {})
                    account_number = details.get('account_number', '')
                    bank_name = details.get('bank_name', 'Unknown Bank')
                    
                    response += f"{i}. **{name}**\n"
                    response += f"   🏦 {bank_name} - {account_number}\n\n"
                
                if len(paystack_recipients) > 5:
                    response += f"... and {len(paystack_recipients) - 5} more Paystack recipients\n\n"
            
            response += "💡 **To send money**: \"Send 5k to [name]\""
            
            return response
            
        except Exception as e:
            logger.error(f"Recipients list formatting failed: {e}")
            return "I found your recipients but had trouble formatting them. Please try again." 