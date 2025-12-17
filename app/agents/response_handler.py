"""Response handler for different types of responses and formatting."""

import random
from typing import Dict, List, Any, Optional
from app.utils.logger import get_logger
from app.utils.bank_resolver import BankResolver
from datetime import datetime

logger = get_logger(__name__)

class ResponseHandler:
    """Handler for different types of responses and formatting."""
    
    def __init__(self, ai_client=None, ai_model=None, ai_enabled=False):
        # Add AI capabilities to response handler
        self.ai_client = ai_client
        self.ai_model = ai_model
        self.ai_enabled = ai_enabled
        
        # Nigerian expressions for different contexts
        self.nigerian_responses = {
            "success": ["Correct! ✅", "E don enter! 🎉", "Sharp sharp! 💪", "Na so! ✅", "Perfect! 👌"],
            "error": ["Wahala dey o! 😅", "Something go wrong! 😅", "No vex, try again! 😊", "Abeg check am again! 🙏"],
            "waiting": ["Small small... ⏳", "Dey wait small... ⏳", "E dey process... ⏳", "Just hold on... ⏳"],
            "balance_low": ["Your money small o! 😅", "You need more money for this transfer o!", "Account balance no reach!"],
            "balance_good": ["Your money dey kampe! 💰", "Money dey for your account! 💪", "You get money o! 💰"],
            "casual": ["No wahala! 😊", "You welcome! 🤗", "Anytime! I dey here for you.", "Sharp! Wetin next?", "Correct! 👍"],
            "thanks": ["No wahala! 😊", "You welcome! 🤗", "Anytime! I dey here for you.", "Na my job be that! 💪"],
            "greeting": ["Hey! How you dey? 👋", "Hello! Wetin I fit do for you?", "Good day! How far? 😊", "Hey there! How you dey?"],
            "help": ["I fit help you with:\n• Check balance\n• Send money\n• View transaction history\n• Manage beneficiaries\n• Chat normally! 😊", 
                    "Wetin you need help with? I dey here for you! 💪"],
            "network": [
                "Wahala with internet! Check your connection try again.",
                "Network issue dey o! Try again in a moment.",
                "Connection problem. Give it another shot!"
            ],
            "balance": [
                "Your account balance no reach for this transfer!",
                "Money small for your account o!",
                "You need more money to complete this transfer."
            ],
            "account": [
                "Abeg check the account details again!",
                "Something wrong with the account details o!",
                "The account number or bank might be wrong."
            ],
            "general": [
                "Something go wrong! Try again.",
                "Wahala dey somewhere! Try again.",
                "Error happened, but no vex - try again!"
            ]
        }
        
        # Bank mappings now use BankResolver utility (no local storage needed)
        
        # Bank code to name mapping (for backward compatibility, but uses BankResolver)
        # Note: This is kept for methods that reference self.bank_code_to_name
        # but should be migrated to use BankResolver.get_bank_name() directly
        self.bank_code_to_name = BankResolver.get_all_bank_names()
        
        # Add additional mappings for common bank codes (if any missing)
        self.bank_code_to_name.update({
            "058": "GTBank",
            "044": "Access Bank",
            "011": "First Bank",
            "057": "Zenith Bank",
            "033": "UBA",
            "070": "Fidelity Bank",
            "232": "Sterling Bank",
            "032": "Union Bank",
            "035": "Wema Bank",
            "214": "FCMB",
            "50211": "Kuda Bank",
            "999992": "OPay",
            "999991": "PalmPay",
            "50515": "Moniepoint",
            "565": "Carbon",
            "101": "Providus Bank",
            "082": "Keystone Bank",
            "076": "Polaris Bank"
        })
        
    def get_random_response(self, category: str) -> str:
        """Get a random response from a category."""
        if category in self.nigerian_responses:
            return random.choice(self.nigerian_responses[category])
        return "No wahala! 😊"
    
    def format_currency(self, amount: float) -> str:
        """Format currency amount in Nigerian Naira."""
        return f"₦{amount:,.2f}"
    
    def format_transaction_status(self, status: str) -> str:
        """Format transaction status with appropriate emojis."""
        status_map = {
            "success": "✅ Success",
            "pending": "🕐 Pending",
            "failed": "❌ Failed",
            "abandoned": "⏸️ Abandoned",
            "reversed": "🔄 Reversed"
        }
        return status_map.get(status.lower(), status)
    
    def format_bank_name(self, bank_code: str) -> str:
        """Format bank name from bank code."""
        return self.bank_code_to_name.get(bank_code, f"Bank {bank_code}")
    
    def format_account_display(self, account_number: str, account_name: str, bank_name: str) -> str:
        """Format account display for user-friendly output."""
        return f"{account_name} - {account_number} ({bank_name})"
    
    def format_transaction_summary(self, transaction: Dict) -> str:
        """Format a single transaction for display."""
        amount = self.format_currency(transaction.get('amount', 0))
        status = self.format_transaction_status(transaction.get('status', 'unknown'))
        reference = transaction.get('reference', 'N/A')
        created_at = transaction.get('created_at', 'N/A')
        
        return f"• {amount} - {status}\n  Ref: {reference}\n  Date: {created_at}"
    
    def format_transfer_summary(self, transfer: Dict) -> str:
        """Format a single transfer for display."""
        amount = self.format_currency(transfer.get('amount', 0))
        status = self.format_transaction_status(transfer.get('status', 'unknown'))
        reference = transfer.get('reference', 'N/A')
        recipient = transfer.get('recipient', {})
        recipient_name = recipient.get('name', 'Unknown')
        created_at = transfer.get('created_at', 'N/A')
        
        return f"• {amount} to {recipient_name}\n  Status: {status}\n  Ref: {reference}\n  Date: {created_at}"
    
    def format_balance_response(self, balance_data: Dict) -> str:
        """Format balance response."""
        balance = self.format_currency(balance_data.get('balance', 0))
        return f"Your balance: {balance} {self.get_random_response('balance_good')}"
    
    def format_recipient_list(self, recipients: List[Dict]) -> str:
        """Format list of recipients."""
        if not recipients:
            return "You no get any saved beneficiaries yet. Add some to make transfers faster! 😊"
        
        formatted = "Your saved beneficiaries:\n\n"
        for i, recipient in enumerate(recipients, 1):
            name = recipient.get('name', 'Unknown')
            account_number = recipient.get('account_number', 'N/A')
            bank_name = self.format_bank_name(recipient.get('bank_code', ''))
            formatted += f"{i}. {name}\n   {account_number} ({bank_name})\n\n"
        
        return formatted.strip()
    
    def format_error_response(self, error_type: str, details: str = "") -> str:
        """Format error response with Nigerian expressions."""
        base_response = self.get_random_response("error")
        
        if error_type == "insufficient_balance":
            return f"{base_response} You no get enough money for this transfer."
        elif error_type == "invalid_account":
            return f"{base_response} The account details you give me no correct."
        elif error_type == "network_error":
            return f"{base_response} Network wahala dey. Try again small."
        elif error_type == "invalid_amount":
            return f"{base_response} The amount you enter no correct."
        elif error_type == "beneficiary_not_found":
            return f"{base_response} I no fit find that beneficiary."
        else:
            return f"{base_response} {details}" if details else base_response
    
    def format_waiting_response(self, action: str) -> str:
        """Format waiting response for long operations."""
        base_response = self.get_random_response("waiting")
        return f"{base_response} I dey {action} for you..."
    
    def format_success_response(self, action: str, details: str = "") -> str:
        """Format success response."""
        base_response = self.get_random_response("success")
        return f"{base_response} {action} successful! {details}".strip()
    
    async def format_help_response(self) -> str:
        """Format help response using LLM or fallback to static response."""
        if self.ai_enabled and self.ai_client:
            try:
                system_prompt = """You are TizBot, a friendly Nigerian banking assistant. Generate a natural, helpful response when someone asks for help.

Guidelines:
- Be conversational and friendly
- Mention key banking features naturally
- Use Nigerian expressions when appropriate
- Keep it short and easy to understand
- Sound like a helpful friend, not a manual
- Don't use excessive bullet points or formatting

Examples:
- "I can help you with checking your balance, sending money, or viewing your transaction history. What do you need?"
- "I'm here to help! I can check your balance, send money to any Nigerian bank, or show your transaction history. What's up?"
- "Need help? I can check your account balance, send money transfers, or show your recent transactions. What can I do for you?"
"""
                
                completion = await self.ai_client.chat.completions.create(
                    model=self.ai_model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": "The user is asking for help with what I can do"}
                    ],
                    max_tokens=100,
                    temperature=0.8
                )
                
                ai_response = completion.choices[0].message.content
                if ai_response and ai_response.strip():
                    return ai_response.strip()
                
            except Exception as e:
                logger.error(f"LLM help response generation failed: {e}")
        
        # Fallback to static response
        return self.get_random_response("help")
    
    async def format_greeting_response(self, user_message: str = "") -> str:
        """Format greeting response using LLM or fallback to static response."""
        if self.ai_enabled and self.ai_client:
            try:
                system_prompt = """You are TizBot, a friendly Nigerian banking assistant. Generate a short, natural greeting response.

Guidelines:
- Be warm but brief (1 sentence only)
- Match the user's energy level
- Use simple Nigerian expressions when appropriate
- Don't ask questions or offer help in greetings
- Just acknowledge and greet back

Examples:
- "Hey! How you dey? 👋"
- "Hello there! 😊"
- "Good day! 🙂"
- "Hi! Hope you dey alright!"
"""
                
                completion = await self.ai_client.chat.completions.create(
                    model=self.ai_model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": f"Generate a greeting response to: {user_message or 'a general greeting'}"}
                    ],
                    max_tokens=40,
                    temperature=0.7
                )
                
                ai_response = completion.choices[0].message.content
                if ai_response and ai_response.strip():
                    return ai_response.strip()
                
            except Exception as e:
                logger.error(f"LLM greeting response generation failed: {e}")
        
        # Fallback to static response
        return self.get_random_response("greeting")
    
    async def format_thanks_response(self, user_message: str = "") -> str:
        """Format thanks response using LLM or fallback to static response."""
        if self.ai_enabled and self.ai_client:
            try:
                system_prompt = """You are TizBot, a friendly Nigerian banking assistant. Generate a natural, warm response to someone thanking you.

Guidelines:
- Be warm and friendly
- Keep it short (1-2 sentences)
- Sound natural and conversational
- Use Nigerian expressions when appropriate
- Don't be overly formal

Examples:
- "You're welcome! 😊"
- "No problem! Happy to help!"
- "Anytime! That's what I'm here for."
- "You're very welcome! Let me know if you need anything else."
"""
                
                completion = await self.ai_client.chat.completions.create(
                    model=self.ai_model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": f"Generate a thanks response to: {user_message or 'someone thanking me'}"}
                    ],
                    max_tokens=60,
                    temperature=0.8
                )
                
                ai_response = completion.choices[0].message.content
                if ai_response and ai_response.strip():
                    return ai_response.strip()
                
            except Exception as e:
                logger.error(f"LLM thanks response generation failed: {e}")
        
        # Fallback to static response
        return self.get_random_response("thanks")
    
    async def format_casual_response(self, user_message: str = "") -> str:
        """Format casual response using LLM or fallback to static response."""
        if self.ai_enabled and self.ai_client:
            try:
                system_prompt = """You are TizBot, a friendly Nigerian banking assistant. Generate a natural, casual response to everyday conversation.

Guidelines:
- Be conversational and friendly
- Match the user's tone
- Use Nigerian expressions naturally
- Keep it short and natural
- Sound like a helpful friend
- Can transition to offering help if appropriate

Examples:
- "Cool! What's up?"
- "Nice! How can I help you?"
- "That's good! Anything I can do for you?"
- "Alright! What do you need?"
"""
                
                completion = await self.ai_client.chat.completions.create(
                    model=self.ai_model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": f"Generate a casual response to: {user_message or 'casual conversation'}"}
                    ],
                    max_tokens=60,
                    temperature=0.8
                )
                
                ai_response = completion.choices[0].message.content
                if ai_response and ai_response.strip():
                    return ai_response.strip()
                
            except Exception as e:
                logger.error(f"LLM casual response generation failed: {e}")
        
        # Fallback to static response
        return self.get_random_response("casual")
    
    def format_confirmation_request(self, action: str, details: str) -> str:
        """Format confirmation request."""
        return f"Confirm {action}:\n\n{details}\n\nType 'yes' to continue or 'no' to cancel."
    
    def format_transfer_confirmation(self, amount: float, account_name: str, account_number: str, bank_name: str) -> str:
        """Format transfer confirmation message with natural Nigerian style."""
        formatted_amount = f"₦{amount:,.2f}"
        
        return f"""💰 *Transfer Confirmation*

You want to send:
• Amount: {formatted_amount}
• To: {account_name}
• Account: {account_number}
• Bank: {bank_name}

Is this correct? Type **"yes"** to proceed or **"no"** to cancel."""

    def format_transfer_success(self, amount: float, account_name: str, account_number: str, bank_name: str) -> str:
        """Format transfer success message with natural Nigerian style."""
        formatted_amount = f"₦{amount:,.2f}"
        
        return f"""✅ *Transfer Successful*

*Transfer Details:*
• Amount: {formatted_amount}
• To: {account_name}
• Account: {account_number}
• Bank: {bank_name}

Your transfer has been processed successfully!

💾 *{account_name}* has been saved for future transfers."""

    def format_account_found(self, account_name: str, account_number: str, bank_name: str) -> str:
        """Format account found message with natural Nigerian style."""
        return f"""✅ *Account Found*

*Account Details:*
• Name: {account_name}
• Account: {account_number}
• Bank: {bank_name}

How much would you like to send?"""

    def format_account_found_with_amount(self, account_name: str, account_number: str, bank_name: str, amount: float) -> str:
        """Format account found with amount already specified."""
        formatted_amount = f"₦{amount:,.2f}"
        
        return f"""✅ I found the account: *{account_name}*

Do you want me to send {formatted_amount} to:

• Account: {account_number}
• Bank: {bank_name}

Reply with **"yes"** to confirm or **"no"** to cancel."""
    
    def format_time_filter_response(self, time_desc: str, data: Dict) -> str:
        """Format time filter response."""
        formatted_amount = self.format_currency(data.get('total_amount', 0))
        count = data.get('count', 0)
        
        return f"For {time_desc.lower()}: {formatted_amount} from {count} transactions"
    
    def create_conversation_context(self, user_message: str, intent: str, entities: Dict) -> Dict:
        """Create conversation context for AI processing."""
        return {
            "user_message": user_message,
            "detected_intent": intent,
            "entities": entities,
            "timestamp": str(datetime.now()) if 'datetime' in globals() else "now"
        }
    
    def should_use_ai_response(self, intent: str, ai_enabled: bool) -> bool:
        """Determine if AI should be used for response generation."""
        ai_suitable_intents = [
            "conversation", "help", "thanks", "greeting", "casual_response",
            "history", "balance", "transfer", "beneficiary_mention"
        ]
        
        return ai_enabled and intent in ai_suitable_intents
    
    async def enhance_error_messages(self, error_type: str) -> str:
        """Generate natural, helpful error messages using LLM or fallback to static responses."""
        
        # Try LLM-based error message generation first
        if self.ai_enabled and self.ai_client:
            try:
                system_prompt = """You are TizBot, a friendly Nigerian banking assistant. Generate a natural, helpful error message for the user.

Guidelines:
- Use natural, conversational language
- Include some Nigerian expressions when appropriate
- Be helpful and encouraging
- Keep it short (1-2 sentences)
- Don't use bullet points or excessive formatting
- Sound like a helpful friend

Examples:
- For network errors: "Looks like there's a network issue! Check your connection and try again."
- For balance errors: "Your account balance isn't enough for this transfer. You might need to fund your account first."
- For account errors: "Something's off with those account details. Double-check the account number and bank name."
"""
                
                error_context = {
                    "network": "There's a network or connection problem",
                    "balance": "The user's account balance is insufficient",
                    "account": "There's an issue with account details provided",
                    "general": "A general error occurred"
                }
                
                user_message = f"Generate a friendly error message for: {error_context.get(error_type, 'a general error')}"
                
                completion = await self.ai_client.chat.completions.create(
                    model=self.ai_model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_message}
                    ],
                    max_tokens=100,
                    temperature=0.8
                )
                
                ai_response = completion.choices[0].message.content
                if ai_response and ai_response.strip():
                    return ai_response.strip()
                
            except Exception as e:
                logger.error(f"LLM error message generation failed: {e}")
        
        # Fallback to static responses
        error_messages = {
            "network": [
                "Wahala with internet! Check your connection try again.",
                "Network issue dey o! Try again in a moment.",
                "Connection problem. Give it another shot!"
            ],
            "balance": [
                "Your account balance no reach for this transfer!",
                "Money small for your account o!",
                "You need more money to complete this transfer."
            ],
            "account": [
                "Abeg check the account details again!",
                "Something wrong with the account details o!",
                "The account number or bank might be wrong."
            ],
            "general": [
                "Something go wrong! Try again.",
                "Wahala dey somewhere! Try again.",
                "Error happened, but no vex - try again!"
            ]
        }
        
        return random.choice(error_messages.get(error_type, error_messages["general"]))
    
    async def format_fallback_response(self, user_message: str, context: Dict = None) -> str:
        """Generate intelligent fallback responses using LLM instead of static templates."""
        
        # Try LLM-based response generation first
        if self.ai_enabled and self.ai_client:
            try:
                system_prompt = """You are TizBot, a smart and conversational Nigerian banking assistant. The user said something you didn't fully understand, but you should respond naturally and helpfully.

Your personality:
- Friendly and conversational like ChatGPT
- Uses Nigerian expressions naturally
- Never says "I don't understand" or gives robotic responses
- Always tries to be helpful while staying natural
- Can chat casually but also offers banking help

Guidelines:
- Respond conversationally to whatever they said
- If it seems banking-related, offer to help with banking
- If it's casual chat, engage naturally
- Keep responses short (1-3 sentences)
- Use emojis sparingly and naturally
- Sound like a helpful Nigerian friend, not a template

Examples:
- If they say something unclear: "I'm not sure what you mean, but I'm here to help! Are you trying to send money or check your balance?"
- If they seem confused: "Let me help you out! I can check your balance, send money, or just chat - what's up?"
- If they ask about features: "I can help you with all kinds of banking stuff - transfers, balance checks, transaction history. What interests you?"
"""
                
                completion = await self.ai_client.chat.completions.create(
                    model=self.ai_model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_message}
                    ],
                    max_tokens=150,
                    temperature=0.8
                )
                
                ai_response = completion.choices[0].message.content
                if ai_response and ai_response.strip():
                    return ai_response.strip()
                
            except Exception as e:
                logger.error(f"LLM fallback response generation failed: {e}")
        
        # Fallback to intelligent static response
        return """I'm here to help! 😊

I can assist you with:
• 💰 Check your balance
• 💸 Send money transfers  
• 📊 View transaction history
• 👥 Manage beneficiaries
• 💬 Just chat normally!

What would you like to do?"""
    
    def format_comprehensive_recipients_response(self, data: Dict) -> str:
        """Format comprehensive recipients response with both local and Paystack recipients."""
        try:
            local_recipients = data.get('local_recipients', [])
            paystack_recipients = data.get('paystack_recipients', [])
            total_count = data.get('total_count', 0)
            
            if total_count == 0:
                template_response = """You don't have any saved recipients yet!

To save contacts:
• Send money with their details: "Send 5k to 0123456789 access bank"  
• I'll ask if you want to save them as a contact
• Or give me their details: "Send to John at 1234567890 kuda"

Next time just say: "Send money to John" 💰"""
                return template_response
            
            response = f"📋 **Your Recipients & Contacts** ({total_count} total):\n\n"
            
            # Show local recipients (our app saved beneficiaries)
            if local_recipients:
                response += f"💾 **App Saved Contacts** ({len(local_recipients)}):\n"
                for i, recipient in enumerate(local_recipients[:8], 1):  # Show max 8
                    usage = recipient.get('use_count', 0)
                    usage_text = f" (used {usage}x)" if usage > 0 else ""
                    nickname = recipient.get('nickname') or recipient.get('account_name', 'Unknown')
                    
                    response += f"{i}. **{nickname}**{usage_text}\n"
                    response += f"   👤 {recipient.get('account_name', 'Unknown')}\n"
                    response += f"   🏦 {recipient.get('bank_name', 'Unknown Bank')} - {recipient.get('account_number', '')}\n\n"
                
                if len(local_recipients) > 8:
                    response += f"... and {len(local_recipients) - 8} more app contacts\n\n"
            
            # Show Paystack recipients (API recipients)
            if paystack_recipients:
                response += f"🏦 **Paystack Recipients** ({len(paystack_recipients)}):\n"
                for i, recipient in enumerate(paystack_recipients[:5], 1):  # Show max 5
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
            logger.error(f"Failed to format recipients response: {e}")
            return "I found your recipients but had trouble formatting them. Please try again."
    
    def format_duplicate_recipient_response(self, duplicate_check: Dict) -> str:
        """Format response for duplicate recipient detection."""
        if duplicate_check['is_duplicate']:
            recipient = duplicate_check['recipient']
            source = duplicate_check['source']
            
            if source == 'local':
                account_name = recipient.get('account_name', 'Unknown')
                account_number = recipient.get('account_number', '')
                bank_name = recipient.get('bank_name', 'Unknown Bank')
            else:  # paystack
                account_name = recipient.get('name', 'Unknown')
                details = recipient.get('details', {})
                account_number = details.get('account_number', '')
                bank_name = details.get('bank_name', 'Unknown Bank')
            
            return f"""✅ **Already Saved!**

The account **{account_number}** ({bank_name}) is already in your contacts:

👤 **{account_name}**
🏦 {bank_name} - {account_number}
💾 Saved in: {"App contacts" if source == 'local' else "Paystack recipients"}

You can send money right away: "Send 5k to {account_name.split()[0]}"
Or check all contacts: "Show my recipients" """
        
        elif duplicate_check.get('has_similar'):
            similar = duplicate_check['similar_accounts'][0]  # Show first similar
            existing_account = similar['existing']
            
            return f"""⚠️ **Similar Account Found**

You want to add: **{duplicate_check.get('new_account', 'Unknown')}**
But you already have: **{existing_account}**

Did you mean the existing account? If this is a different account, please confirm by saying:
"Yes, add the new account {duplicate_check.get('new_account', 'Unknown')}"

Or check your existing contacts: "Show my recipients" """
        
        return "Account checked for duplicates."
    
    def format_successful_recipient_save_response(self, recipient_data: Dict, local_save_result: Dict) -> str:
        """Format response for successful recipient save."""
        account_name = recipient_data['account_name']
        account_number = recipient_data['account_number']
        bank_name = recipient_data['bank_name']
        
        response = f"""✅ **Contact Saved Successfully!**

👤 **{account_name}**
🏦 {bank_name} - {account_number}
💾 Saved to: Paystack API"""
        
        if local_save_result.get('saved_locally'):
            response += " + App contacts"
        
        response += f"""

🚀 **Now you can send money easily:**
• "Send 5k to {account_name.split()[0]}"
• "Transfer ₦2000 to {account_name.split()[0]}"

💡 Use "Show my recipients" to see all saved contacts!"""
        
        return response
    
    def format_beneficiary_transfer_confirmation(self, amount: float, recipient_name: str, account_name: str, bank_name: str, balance_after: float) -> str:
        """Format beneficiary transfer confirmation."""
        formatted_amount = self.format_currency(amount)
        formatted_balance = self.format_currency(balance_after)
        
        return f"""Sharp! You wan send {formatted_amount} to {recipient_name}! 💰

**Transfer Details:**
• Amount: {formatted_amount}
• To: **{recipient_name}** ({account_name})
• Bank: {bank_name.title()}

**After Transfer**: {formatted_balance}

Say "yes" to send it or "no" to cancel! """
    
    def format_named_transfer_confirmation(self, amount: float, recipient_name: str, account_name: str, 
                                         account_number: str, bank_name: str, balance_after: float, is_new: bool = False) -> str:
        """Format named transfer confirmation."""
        formatted_amount = self.format_currency(amount)
        formatted_balance = self.format_currency(balance_after)
        new_text = " (New contact - I've saved them for you!)" if is_new else ""
        
        return f"""✅ **Account Resolved!** {new_text}

**Transfer Details:**
• Amount: {formatted_amount}
• To: **{recipient_name}** ({account_name})
• Account: {account_number}
• Bank: {bank_name}

**After Transfer**: {formatted_balance}

Say "yes" to send it or "no" to cancel! 💰"""
    
    def format_insufficient_balance_response(self, requested_amount: float, current_balance: float, recipient_name: str = "") -> str:
        """Format insufficient balance response."""
        formatted_requested = self.format_currency(requested_amount)
        formatted_balance = self.format_currency(current_balance)
        
        if recipient_name:
            return f"❌ **Insufficient Balance**\n\nYou want to send {formatted_requested} to {recipient_name} but your balance is {formatted_balance}."
        else:
            return f"❌ **Insufficient Balance**\n\nYou're trying to send {formatted_requested} but your balance is {formatted_balance}."
    
    def create_comprehensive_fallback_response(self, data: Dict) -> str:
        """Create a natural fallback response when AI fails, using Nigerian conversational style."""
        try:
            # Create natural response based on data
            balance_text = self.format_currency(data.get('current_balance', 0))
            
            if data.get('transfer_count', 0) > 0 and data.get('transaction_count', 0) > 0:
                # Both incoming and outgoing activity
                received = self.format_currency(data.get('total_received', 0))
                sent = self.format_currency(data.get('total_sent', 0))
                return f"You've been active! Received {received} from {data['transaction_count']} transactions and sent {sent} from {data['transfer_count']} transfers. Your balance is {balance_text}."
            
            elif data.get('transaction_count', 0) > 0:
                # Only incoming activity
                received = self.format_currency(data.get('total_received', 0))
                if data['transaction_count'] == 1:
                    return f"You received {received} from 1 transaction. Your balance is {balance_text}."
                else:
                    return f"You received {received} from {data['transaction_count']} transactions. Your balance is {balance_text}."
            
            elif data.get('transfer_count', 0) > 0:
                # Only outgoing activity
                sent = self.format_currency(data.get('total_sent', 0))
                if data['transfer_count'] == 1:
                    return f"You sent {sent} from 1 transfer. Your balance is {balance_text}."
                else:
                    return f"You sent {sent} from {data['transfer_count']} transfers. Your balance is {balance_text}."
            
            else:
                # No activity
                return f"No recent activity found for {data.get('period', 'the period')}. Your current balance is {balance_text}."
                
        except Exception as e:
            logger.error(f"Failed to create fallback response: {e}")
            return f"Your current balance is {self.format_currency(data.get('current_balance', 0))}." 
    
    async def generate_ai_transfer_success_response(self, user_id: str, transfer_data: Dict, context: Dict = None) -> str:
        """Generate AI-powered conversational transfer success response."""
        if not (self.ai_enabled and self.ai_client):
            return self._fallback_transfer_success_response(transfer_data)
        
        try:
            # Extract transfer details
            amount = transfer_data.get('amount', 0)
            recipient_name = transfer_data.get('recipient', 'Unknown')
            account_number = transfer_data.get('account_number', 'N/A')
            bank_name = transfer_data.get('bank_name', 'Unknown Bank')
            reference = transfer_data.get('reference', 'N/A')
            is_new_recipient = transfer_data.get('is_new_recipient', False)
            
            # Format amount for display
            formatted_amount = f"₦{amount:,.2f}"
            
            # Initialize variables with defaults
            repeat_recipient = False
            time_context = "general"
            context_info = ""
            
            # Get additional context for more personalized responses
            try:
                # Get user's recent transfer history for context
                from app.utils.memory_manager import MemoryManager
                memory = MemoryManager()
                recent_transfers = await memory.get_transfer_history(user_id, limit=5)
                
                # Calculate some interesting stats
                total_transfers_count = len(recent_transfers)
                total_amount_sent = sum(t.get('amount', 0) for t in recent_transfers)
                
                # Check if this is a repeat recipient
                if recent_transfers:
                    for transfer in recent_transfers[:-1]:  # Exclude current transfer
                        if transfer.get('recipient') == recipient_name:
                            repeat_recipient = True
                            break
                
                # Time-based patterns
                import datetime
                current_hour = datetime.datetime.now().hour
                if current_hour < 12:
                    time_context = "morning"
                elif current_hour < 17:
                    time_context = "afternoon"
                else:
                    time_context = "evening"
                
                # Build contextual information
                context_info = f"\n\nUser context:"
                context_info += f"\n- Recent transfers: {total_transfers_count}"
                context_info += f"\n- Total amount sent recently: ₦{total_amount_sent:,.2f}"
                context_info += f"\n- Repeat recipient: {repeat_recipient}"
                context_info += f"\n- Time of day: {time_context}"
                context_info += f"\n- Amount size: {'large' if amount > 10000 else 'medium' if amount > 1000 else 'small'}"
                
                # Special occasions/patterns
                if repeat_recipient:
                    context_info += "\n- This is a repeat recipient (user has sent money to them before)"
                
                if amount > 50000:
                    context_info += "\n- This is a large transfer (> ₦50,000)"
                elif amount < 500:
                    context_info += "\n- This is a small transfer (< ₦500)"
                
                # Add to existing context if provided
                if context:
                    balance_info = context.get('balance_after', 0)
                    if balance_info > 0:
                        context_info += f"\n- Balance after transfer: ₦{balance_info:,.2f}"
                
            except Exception as context_error:
                logger.warning(f"Could not fetch context for AI response: {context_error}")
                context_info = ""
            
            # Determine transfer type for context
            transfer_type = "beneficiary" if not is_new_recipient else "new_account"
            
            # Select AI personality based on context
            personality_style = self._select_ai_personality(amount, repeat_recipient, time_context, is_new_recipient)
            
            # Enhanced AI prompt with contextual awareness
            system_prompt = f"""You are TizBot, a friendly Nigerian AI banking assistant. Generate a natural, conversational response for a successful money transfer.

{personality_style}

Guidelines:
- Be warm, friendly, and conversational
- Use Nigerian expressions naturally (like "don reach", "sharp sharp", "no wahala", "correct", "e don enter")
- Sound excited about successful transfers
- Keep it brief (2-3 sentences max)
- Use appropriate emojis sparingly
- Include key transfer details naturally
- Sound like a helpful friend, not a robot
- Vary your responses based on context
- Make references to patterns when relevant (e.g., "Another successful transfer to Mary!" if repeat recipient)
- Acknowledge large/small amounts appropriately
- Be encouraging and positive

Response styles based on context:
- New recipient: Welcome them, mention saving for future
- Repeat recipient: Acknowledge familiarity ("Another transfer to John!")
- Large amounts: Show appropriate excitement
- Small amounts: Be encouraging but not overly dramatic
- Morning/afternoon/evening: Use appropriate time-based expressions

Examples:
- "Sharp! Your ₦5,000 don reach John at GTBank! 🎉 E don enter successfully."
- "Perfect! Another ₦2,000 to Mary - she must be happy! ✅ Money transferred successfully."
- "Wow! ₦50,000 to David - that's a big one! 💰 Transfer complete, ref: ABC123."
- "Nice! ₦500 sent to Sarah at Kuda Bank. Small but mighty! ✅"
"""
            
            user_prompt = f"""Generate a conversational success response for this transfer:

Amount: {formatted_amount}
Recipient: {recipient_name}
Bank: {bank_name}
Reference: {reference}
Transfer type: {transfer_type}
New recipient: {is_new_recipient}{context_info}

Make it sound natural, contextual, and friendly!"""
            
            # Generate AI response
            completion = await self.ai_client.chat.completions.create(
                model=self.ai_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                max_tokens=150,
                temperature=0.8
            )
            
            ai_response = completion.choices[0].message.content
            if ai_response and ai_response.strip():
                # Add recipient save notification if it's a new recipient
                response = ai_response.strip()
                if is_new_recipient:
                    save_messages = [
                        f"💾 I've saved **{recipient_name}** for easy future transfers!",
                        f"💾 **{recipient_name}** is now in your contacts!",
                        f"💾 Added **{recipient_name}** to your saved recipients!",
                        f"💾 **{recipient_name}** saved for next time!"
                    ]
                    import random
                    response += f"\n\n{random.choice(save_messages)}"
                
                # Follow-up suggestions disabled - user wants simple transfer completion
                # follow_up = await self._generate_ai_follow_up_suggestions(
                #     user_id, transfer_data, context_info
                # )
                # if follow_up:
                #     response += f"\n\n{follow_up}"
                
                return response
            
        except Exception as e:
            logger.error(f"AI transfer success response generation failed: {e}")
        
        # Fallback to enhanced template
        return self._fallback_transfer_success_response(transfer_data)
    
    def _fallback_transfer_success_response(self, transfer_data: Dict) -> str:
        """Fallback transfer success response when AI is unavailable."""
        amount = transfer_data.get('amount', 0)
        recipient_name = transfer_data.get('recipient', 'Unknown')
        bank_name = transfer_data.get('bank_name', 'Unknown Bank')
        reference = transfer_data.get('reference', 'N/A')
        is_new_recipient = transfer_data.get('is_new_recipient', False)
        
        formatted_amount = f"₦{amount:,.2f}"
        
        # Nigerian-style responses
        responses = [
            f"Sharp! Your {formatted_amount} don reach {recipient_name} at {bank_name}! 🎉 Ref: {reference}",
            f"Perfect! {formatted_amount} sent to {recipient_name} successfully! ✅ Reference: {reference}",
            f"Money don enter! {formatted_amount} transferred to {recipient_name} ({bank_name}) 💰 Ref: {reference}",
            f"✅ Transfer complete! {formatted_amount} successfully sent to {recipient_name} at {bank_name}.",
            f"E don enter! Your {formatted_amount} transfer to {recipient_name} was successful! 🎉 Ref: {reference}"
        ]
        
        import random
        response = random.choice(responses)
        
        if is_new_recipient:
            response += f"\n\n💾 I've saved **{recipient_name}** as a contact for easy future transfers!"
        
        return response 
    
    async def _generate_ai_follow_up_suggestions(self, user_id: str, transfer_data: Dict, context_info: str) -> str:
        """Generate AI-powered follow-up suggestions based on transfer context."""
        if not (self.ai_enabled and self.ai_client):
            return self._fallback_follow_up_suggestions(transfer_data)
        
        try:
            # Extract relevant info for suggestions
            amount = transfer_data.get('amount', 0)
            recipient_name = transfer_data.get('recipient', 'Unknown')
            bank_name = transfer_data.get('bank_name', 'Unknown Bank')
            is_new_recipient = transfer_data.get('is_new_recipient', False)
            
            # Create contextual prompt for follow-up suggestions
            system_prompt = """You are TizBot, a helpful Nigerian AI banking assistant. Generate natural, contextual follow-up suggestions after a successful money transfer.

Guidelines:
- Suggest 1-2 relevant next actions based on the context
- Keep suggestions brief and actionable
- Use Nigerian expressions naturally
- Be helpful without being pushy
- Vary suggestions based on:
  * Transfer amount (large/small)
  * New vs repeat recipient
  * Time patterns
  * User history

Good suggestion types:
- Check balance after large transfers
- Send receipts to recipients
- Set up regular transfers for repeat recipients
- Check transaction history
- Transfer to other saved contacts
- Ask if they need help with anything else

Examples:
- "Want me to check your balance after that big transfer?"
- "Should I help you send money to anyone else?"
- "Need your transaction history or receipt?"
- "Want to set up regular transfers to {recipient}?"

Keep it conversational and optional - don't be demanding!"""
            
            user_prompt = f"""Generate 1-2 brief follow-up suggestions for this transfer:

Amount: ₦{amount:,.2f}
Recipient: {recipient_name}
Bank: {bank_name}
New recipient: {is_new_recipient}{context_info}

Make suggestions feel natural and helpful!"""
            
            # Generate AI suggestions
            completion = await self.ai_client.chat.completions.create(
                model=self.ai_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                max_tokens=100,
                temperature=0.7
            )
            
            ai_suggestions = completion.choices[0].message.content
            if ai_suggestions and ai_suggestions.strip():
                return ai_suggestions.strip()
            
        except Exception as e:
            logger.error(f"AI follow-up suggestions generation failed: {e}")
        
        # Fallback to static suggestions
        return self._fallback_follow_up_suggestions(transfer_data)
    
    def _fallback_follow_up_suggestions(self, transfer_data: Dict) -> str:
        """Fallback follow-up suggestions when AI is unavailable."""
        amount = transfer_data.get('amount', 0)
        recipient_name = transfer_data.get('recipient', 'Unknown')
        is_new_recipient = transfer_data.get('is_new_recipient', False)
        
        suggestions = []
        
        # Context-based suggestions
        if amount > 10000:
            suggestions.extend([
                "Want me to check your balance after that big transfer?",
                "Need your transaction history or receipt?",
                "Should I help you send money to anyone else?"
            ])
        elif amount > 1000:
            suggestions.extend([
                "Should I help you send money to anyone else?",
                "Want to check your balance or transaction history?",
                "Need help with anything else?"
            ])
        else:
            suggestions.extend([
                "Want to send money to anyone else?",
                "Need help with anything else?",
                "Should I check your balance?"
            ])
        
        # New recipient suggestions
        if is_new_recipient:
            suggestions.extend([
                f"Want to set up regular transfers to {recipient_name}?",
                "Should I help you add more contacts?"
            ])
        else:
            suggestions.extend([
                f"Want to send more money to {recipient_name}?",
                "Should I help you send to other contacts?"
            ])
        
        # Random selection
        import random
        selected_suggestions = random.sample(suggestions, min(2, len(suggestions)))
        
        if len(selected_suggestions) == 1:
            return selected_suggestions[0]
        else:
            return f"{selected_suggestions[0]} Or {selected_suggestions[1].lower()}" 

    def _select_ai_personality(self, amount: float, repeat_recipient: bool, time_context: str, is_new_recipient: bool) -> str:
        """Selects an AI personality based on transfer context."""
        if amount > 50000:
            return """You are TizBot, a friendly Nigerian AI banking assistant. You are excited and enthusiastic about large transfers.
- Be warm, friendly, and conversational
- Use Nigerian expressions naturally (like "don reach", "sharp sharp", "no wahala", "correct", "e don enter")
- Sound excited about successful transfers
- Keep it brief (2-3 sentences max)
- Use appropriate emojis sparingly
- Include key transfer details naturally
- Sound like a helpful friend, not a robot
- Vary your responses based on context
- Make references to patterns when relevant (e.g., "Another successful transfer to Mary!" if repeat recipient)
- Acknowledge large/small amounts appropriately
- Be encouraging and positive

Response styles based on context:
- New recipient: Welcome them, mention saving for future
- Repeat recipient: Acknowledge familiarity ("Another transfer to John!")
- Large amounts: Show appropriate excitement
- Small amounts: Be encouraging but not overly dramatic
- Morning/afternoon/evening: Use appropriate time-based expressions

Examples:
- "Sharp! Your ₦50,000 to David - that's a big one! 💰 Transfer complete, ref: ABC123."
- "Wow! ₦50,000 to David - that's a big one! 💰 Transfer complete, ref: ABC123."
"""
        elif amount < 500:
            return """You are TizBot, a friendly Nigerian AI banking assistant. You are encouraging and positive about small transfers.
- Be warm, friendly, and conversational
- Use Nigerian expressions naturally (like "don reach", "sharp sharp", "no wahala", "correct", "e don enter")
- Sound excited about successful transfers
- Keep it brief (2-3 sentences max)
- Use appropriate emojis sparingly
- Include key transfer details naturally
- Sound like a helpful friend, not a robot
- Vary your responses based on context
- Make references to patterns when relevant (e.g., "Another successful transfer to Mary!" if repeat recipient)
- Acknowledge large/small amounts appropriately
- Be encouraging and positive

Response styles based on context:
- New recipient: Welcome them, mention saving for future
- Repeat recipient: Acknowledge familiarity ("Another transfer to John!")
- Large amounts: Show appropriate excitement
- Small amounts: Be encouraging but not overly dramatic
- Morning/afternoon/evening: Use appropriate time-based expressions

Examples:
- "Nice! ₦500 sent to Sarah at Kuda Bank. Small but mighty! ✅"
- "Nice! ₦500 sent to Sarah at Kuda Bank. Small but mighty! ✅"
"""
        elif repeat_recipient:
            return """You are TizBot, a friendly Nigerian AI banking assistant. You are familiar with repeat transfers.
- Be warm, friendly, and conversational
- Use Nigerian expressions naturally (like "don reach", "sharp sharp", "no wahala", "correct", "e don enter")
- Sound excited about successful transfers
- Keep it brief (2-3 sentences max)
- Use appropriate emojis sparingly
- Include key transfer details naturally
- Sound like a helpful friend, not a robot
- Vary your responses based on context
- Make references to patterns when relevant (e.g., "Another successful transfer to Mary!" if repeat recipient)
- Acknowledge large/small amounts appropriately
- Be encouraging and positive

Response styles based on context:
- New recipient: Welcome them, mention saving for future
- Repeat recipient: Acknowledge familiarity ("Another transfer to John!")
- Large amounts: Show appropriate excitement
- Small amounts: Be encouraging but not overly dramatic
- Morning/afternoon/evening: Use appropriate time-based expressions

Examples:
- "Perfect! Another ₦2,000 to Mary - she must be happy! ✅ Money transferred successfully."
- "Perfect! Another ₦2,000 to Mary - she must be happy! ✅ Money transferred successfully."
"""
        else:
            return """You are TizBot, a friendly Nigerian AI banking assistant. You are warm and welcoming.
- Be friendly and conversational
- Match the user's energy level
- Use Nigerian expressions naturally when appropriate
- Keep it short (1-2 sentences)
- Sound like a helpful friend
- Offer help naturally

Examples:
- "Hey there! How can I help you today?"
- "Hello! What can I do for you?"
- "Hi! Need help with any banking stuff?"
- "Good day! How far? What do you need?"
""" 