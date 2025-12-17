#!/usr/bin/env python3
"""
AI Handler - Manages conversational AI interactions
"""

import asyncio
import random
from typing import Dict, Optional, Any, cast
from app.utils.logger import get_logger
from app.utils.memory_manager import MemoryManager
from datetime import datetime
import json

logger = get_logger("ai_handler")

class AIHandler:
    """Handle AI-powered conversations and responses."""
    
    def __init__(self, memory_manager: MemoryManager, ai_client=None, ai_model=None, ai_enabled=False):
        self.memory = memory_manager
        self.ai_client = ai_client
        self.ai_model = ai_model
        self.ai_enabled = ai_enabled
        
        # Enhanced Nigerian responses with new categories
        self.nigerian_responses = {
            "success": ["Correct! ✅", "E don enter! 🎉", "Sharp sharp! 💪", "Na so! ✅", "Perfect! 👌"],
            "error": ["Wahala dey o! 😅", "Something go wrong! 😅", "No vex, try again! 😊", "Abeg check am again! 🙏"],
            "waiting": ["Small small... ⏳", "Dey wait small... ⏳", "E dey process... ⏳", "Just hold on... ⏳"],
            "balance_low": ["Your money small o! 😅", "You need more money for this transfer o!", "Account balance no reach!"],
            "balance_good": ["Your money dey kampe! 💰", "Money dey for your account! 💪", "You get money o! 💰"],
            "casual": ["No wahala! 😊", "You welcome! 🤗", "Anytime! I dey here for you.", "Sharp! Wetin next?", "Correct! 👍"],
            "thanks": ["No wahala! 😊", "You welcome! 🤗", "Anytime! I dey here for you.", "Na my job be that! 💪"],
            "denial_response": ["No wahala! Let me know if you need anything else.", "Alright! I dey here if you change your mind.", "Cool! Just holler when you ready."],
            "correction_response": ["I hear you! Let me get that right for you.", "My bad! Let me fix that.", "You right! Let me correct that."],
            "complaint_response": ["I understand your frustration! Let me help.", "Sorry about that! How can I fix this?", "I hear you loud and clear! Let me sort this out."],
            "conversational_response": ["I dey fine o! Thanks for asking.", "All good here! What's on your mind?", "I'm doing well! How can I help?"],
            "repetition_complaint": ["You right! Sorry about that repetition.", "My bad! I wasn't tracking properly.", "True! I don't want to repeat myself."]
        }
    
    async def _send_follow_up_message(self, user_id: str, message: str):
        """Send a follow-up WhatsApp message to user."""
        try:
            from app.services.whatsapp_service import WhatsAppService
            
            whatsapp_service = WhatsAppService()
            
            # Format user_id for WhatsApp (ensure it has proper format)
            whatsapp_number = user_id if user_id.startswith('whatsapp:') else f"whatsapp:{user_id}"
            
            result = await whatsapp_service.send_message(whatsapp_number, message)
            
            if result.get('success'):
                logger.info(f"📱 Follow-up message sent successfully to {user_id}")
            else:
                logger.error(f"❌ Failed to send follow-up message to {user_id}: {result.get('error')}")
                
        except Exception as e:
            logger.error(f"Failed to send follow-up message: {e}")
    
    def _is_simple_social_interaction(self, message: str) -> bool:
        """Detect if this is a simple social interaction that doesn't need thinking delays."""
        message_lower = message.lower().strip()
        
        # Simple greetings
        simple_greetings = [
            "hi", "hello", "hey", "yo", "yoo", "good morning", "good afternoon", "good evening",
            "how are you", "how you doing", "how's it going", "what's up", "wassup", "sup"
        ]
        
        # Simple thanks
        simple_thanks = [
            "thanks", "thank you", "appreciate it", "thanks a lot", "thank you very much"
        ]
        
        # Simple responses
        simple_responses = [
            "good", "fine", "great", "awesome", "cool", "nice", "ok", "okay", "alright",
            "nothing much", "not much", "all good", "i'm good", "doing good", "doing great"
        ]
        
        # Simple confirmations/denials
        simple_confirmations = [
            "yes", "yeah", "yep", "sure", "ok", "okay", "alright", "no", "nope", "nah"
        ]
        
        # Check for exact matches or very simple patterns
        all_simple_patterns = simple_greetings + simple_thanks + simple_responses + simple_confirmations
        
        # Exact match check
        if message_lower in all_simple_patterns:
            return True
        
        # Pattern match for slightly longer but still simple messages
        if len(message_lower.split()) <= 3:
            for pattern in all_simple_patterns:
                if pattern in message_lower:
                    return True
        
        return False

    async def handle_ai_conversation(self, user_id: str, message: str, context: str) -> str:
        """Handle AI-powered conversations with smart delay detection."""
        try:
            # Check if this is a simple social interaction
            if self._is_simple_social_interaction(message):
                # Provide instant response without thinking delay
                return await self._handle_ai_conversation_traditional(user_id, message, context)
            
            # For complex queries, use thinking delay + background processing
            responses = [
                "Lemme think about that real quick... 🤔",
                "Give me a sec to process that... 💭",
                "Hold on, let me figure that out for you... ⏳",
                "One moment while I think about this... 🧠",
                "Processing your request... Just a sec! 💭"
            ]
            import random
            immediate_response = random.choice(responses)
            
            # Start background processing task (don't await it)
            asyncio.create_task(self._process_ai_conversation_background(user_id, message, context))
            
            # Return immediate response to user
            return immediate_response
            
        except Exception as e:
            logger.error(f"Failed to start AI conversation: {e}")
            # Fallback to traditional method if background processing fails
            return await self._handle_ai_conversation_traditional(user_id, message, context)
    
    async def handle_ai_conversation_with_callback(self, user_id: str, message: str, send_follow_up_callback) -> str:
        """Handle AI-powered conversations with callback, smart delay detection."""
        try:
            # Check if this is a simple social interaction
            if self._is_simple_social_interaction(message):
                # Provide instant response without thinking delay or callback
                return await self.handle_general_conversation(user_id, message)
            
            # For complex queries, use thinking delay + background processing
            responses = [
                "Lemme think about that real quick... 🤔",
                "Give me a sec to process that... 💭", 
                "Hold on, let me figure that out for you... ⏳",
                "One moment while I think about this... 🧠",
                "Processing your request... Just a sec! 💭"
            ]
            import random
            immediate_response = random.choice(responses)
            
            # Start background processing task with callback
            asyncio.create_task(self._process_ai_conversation_with_callback_background(user_id, message, send_follow_up_callback))
            
            # Return immediate response to user
            return immediate_response
            
        except Exception as e:
            logger.error(f"Failed to start AI conversation with callback: {e}")
            # Fallback to traditional method
            return await self.handle_conversation_request(user_id, message)
    
    async def _process_ai_conversation_with_callback_background(self, user_id: str, message: str, send_follow_up_callback):
        """Process AI conversation in background and send follow-up via callback."""
        try:
            logger.info(f"🔄 Starting background AI conversation with callback for user {user_id}")
            
            # Process the AI conversation using the general conversation handler
            result = await self.handle_conversation_request(user_id, message)
            
            # Send the detailed response via callback
            await send_follow_up_callback(user_id, result)
            logger.info(f"✅ Background AI conversation with callback completed for user {user_id}")
            
        except Exception as e:
            logger.error(f"Background AI conversation with callback failed: {e}")
            await send_follow_up_callback(user_id, "Sorry, I'm having trouble processing that right now. Could you try again?")

    async def _process_ai_conversation_background(self, user_id: str, message: str, context: str):
        """Process AI conversation in background and send second response."""
        try:
            logger.info(f"🔄 Starting background AI conversation for user {user_id}")
            
            # Process the AI conversation
            result = await self._handle_ai_conversation_traditional(user_id, message, context)
            
            # Send the detailed response as second message
            await self._send_follow_up_message(user_id, result)
            logger.info(f"✅ Background AI conversation completed for user {user_id}")
            
        except Exception as e:
            logger.error(f"Background AI conversation failed: {e}")
            await self._send_follow_up_message(user_id, "Sorry, I'm having trouble processing that right now. Could you try again?")
    
    def _build_tizbot_system_prompt(self, context: Dict = None) -> str:
        """Build comprehensive TizBot persona system prompt for ChatGPT-like behavior."""
        
        return """You are TizBot, a smart and conversational Nigerian banking assistant with ChatGPT-like intelligence.

🤖 **CORE IDENTITY:**
- Name: TizBot (sometimes called TizLion AI)
- Personality: Friendly, smart, conversational, relatable, occasionally funny
- Origin: Nigerian AI assistant specializing in banking but capable of general conversation
- Behavior: Like ChatGPT but with Nigerian flair and banking expertise

💬 **CONVERSATIONAL STYLE:**
- Always respond naturally and conversationally
- Use Nigerian expressions and Pidgin English when appropriate
- Never give robotic or template responses
- Can discuss anything - banking, life, current events, casual topics
- Remember and reference previous conversations
- Be genuinely helpful and engaging
- Match the user's energy and tone

🧠 **MEMORY & CONTEXT:**
- You have perfect memory of all previous conversations with each user
- Reference past interactions, amounts, names, and topics naturally
- Build on previous conversations without repeating information
- Maintain conversational flow across multiple messages
- Remember user preferences and patterns

🏦 **BANKING EXPERTISE:**
- You can check balances, send money, view transaction history
- You work with Paystack API and Nigerian banks
- You can save beneficiaries and manage contacts
- You handle transfers, account resolution, and financial queries
- Always prioritize security and user verification

✨ **BEHAVIORAL RULES:**
- NEVER say "I don't understand" or "I'm not sure"
- ALWAYS generate something thoughtful and helpful
- For unclear requests, ask clarifying questions conversationally
- Mix casual chat with banking assistance naturally
- Use humor appropriately but stay helpful
- Be patient with confused users

🎯 **RESPONSE GUIDELINES:**
- Keep responses concise (1-3 sentences for simple topics)
- Use natural language, not bullet points or excessive formatting
- Ask follow-up questions to keep conversations flowing
- Offer help proactively when sensing user needs
- Be encouraging and positive
- Sound like talking to a smart friend, not a chatbot

📝 **EXAMPLES OF GOOD RESPONSES:**
- "Hey! What's up? Need help with anything or just checking in?"
- "I remember you sent money to Temmy last week. Need to send more?"
- "Your balance is ₦7,480 - not bad! Planning any transfers today?"
- "I can help with that! Let me check your recent transactions."
- "That's interesting! I can help with banking stuff too if you need."

🚫 **NEVER SAY:**
- "I'm not sure how to help with that"
- "I don't understand what you mean"
- "Here's what I can do: • Item 1 • Item 2"
- "I'm here to help! 😊 What can I do for you?"
- "Sorry, I can't process that request"

🔄 **CONVERSATION FLOW:**
- Acknowledge what the user said
- Provide helpful response or ask clarifying questions
- Offer additional assistance naturally
- Keep the conversation going when appropriate
- Remember context for future messages

Remember: You're not just a banking bot - you're a conversational AI that happens to be great at banking. Be naturally helpful, genuinely engaging, and always ready to chat about anything while offering banking assistance when needed."""

    async def _handle_ai_conversation_traditional(self, user_id: str, message: str, context: str) -> str:
        """Traditional AI conversation handler with enhanced TizBot persona."""
        try:
            if not self.ai_enabled or not self.ai_client:
                return await self._handle_intelligent_fallback(user_id, message)
            
            # Get conversation history for better context
            conversation_history = await self.memory.get_conversation_history(user_id, limit=7)
            
            # Build enhanced TizBot system prompt
            system_prompt = self._build_tizbot_system_prompt()
            
            # Prepare conversation context
            context_messages = []
            if conversation_history:
                for msg in conversation_history[-5:]:  # Last 5 messages for better context
                    role = "user" if msg.get("role") == "user" else "assistant"
                    content = msg.get("message", "")
                    if content and not content.startswith("["):  # Skip system messages
                        context_messages.append({"role": role, "content": content})
            
            # Add current message
            context_messages.append({"role": "user", "content": message})
            
            # Generate AI response
            if not self.ai_model:
                return "I'm having trouble with my AI right now. Try asking me about your balance or transfers?"
            
            completion = await self.ai_client.chat.completions.create(
                model=self.ai_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    *context_messages
                ],
                max_tokens=200,  # Allow for more comprehensive responses
                temperature=0.8  # More creative and conversational
            )
            
            # Handle potential None content
            raw_content = completion.choices[0].message.content
            ai_response = raw_content.strip() if raw_content else "I couldn't generate a response right now."
            
            # Ensure response isn't too long
            if len(ai_response) > 400:
                ai_response = ai_response[:397] + "..."
                
            return ai_response
            
        except Exception as e:
            logger.error(f"AI conversation failed: {e}")
            return "I'm having trouble right now. Try asking me about your balance or sending money?"
    
    async def _handle_intelligent_fallback(self, user_id: str, message: str) -> str:
        """Intelligent fallback when AI is not available - TizBot persona maintained."""
        
        message_lower = message.lower()
        
        # Handle banking-related queries with TizBot personality
        if any(word in message_lower for word in ["balance", "money", "account", "send", "transfer"]):
            responses = [
                "I can help you with that! My AI is having a moment, but I can still check your balance or help with transfers.",
                "No worries! Even without my full AI, I can help you send money or check your account balance.",
                "I'm still here to help! I can check your balance, send money, or view your transaction history right now.",
                "My AI is taking a break, but I can still handle your banking needs! What do you need?"
            ]
            import random
            return random.choice(responses)
        
        # Handle greetings with personality
        if any(word in message_lower for word in ["hi", "hello", "hey", "good morning", "good afternoon", "good evening"]):
            responses = [
                "Hey there! My AI is having a moment, but I'm still here to help with your banking needs.",
                "Hello! I'm still around to help you with balance checks, transfers, and more.",
                "Hi! Even without my full AI, I can still help you with banking stuff. What's up?",
                "Good day! I'm still here to help with your money matters. What can I do for you?"
            ]
            import random
            return random.choice(responses)
        
        # Handle casual conversation
        if any(word in message_lower for word in ["how are you", "how you doing", "what's up", "wassup"]):
            responses = [
                "I'm doing well! My AI is taking a quick break, but I'm still here to help with your banking.",
                "All good here! I can still help you with balance checks, transfers, and transaction history.",
                "I'm fine! My AI is having a moment, but I can still handle your banking needs.",
                "Doing great! Even without my full AI, I can help you with money stuff. What do you need?"
            ]
            import random
            return random.choice(responses)
        
        # Handle thanks and appreciation
        if any(word in message_lower for word in ["thanks", "thank you", "appreciate"]):
            responses = [
                "You're welcome! I'm always here to help with your banking needs.",
                "No problem! Feel free to ask me about your balance or transfers anytime.",
                "Happy to help! I can check your account or help with money transfers whenever you need.",
                "Anytime! I'm here for all your banking questions."
            ]
            import random
            return random.choice(responses)
        
        # Handle questions about capabilities
        if any(word in message_lower for word in ["what can you do", "help", "what", "how"]):
            return """I can help you with several things right now:

💰 Check your account balance
💸 Send money to any Nigerian bank
📊 View your transaction history
👥 Show your saved beneficiaries
🏦 List available banks

What would you like to do? Just ask me naturally!"""
        
        # Handle confusion or negative responses
        if any(word in message_lower for word in ["confused", "don't understand", "not sure", "unclear"]):
            responses = [
                "No worries! I'm here to help. Try asking me about your balance or sending money to someone.",
                "That's okay! I can help with banking stuff - checking your balance, sending money, or viewing your history.",
                "Let me help you out! I can check your account balance, send transfers, or show your transaction history.",
                "Don't worry! I'm here to make banking easy. What do you need help with?"
            ]
            import random
            return random.choice(responses)
        
        # Default intelligent response with TizBot personality
        responses = [
            "I'm here to help! You can ask me about your balance, send money, or check your transaction history. What's on your mind?",
            "What can I help you with today? I can check your balance, send money, or show your recent transactions.",
            "I'm ready to help! Whether it's checking your account balance, sending money, or reviewing transactions.",
            "How can I assist you? I can help with balance checks, money transfers, transaction history, and more!"
        ]
        
        import random
        return random.choice(responses)
    
    async def handle_greeting_question(self, user_id: str) -> str:
        """Handle greeting questions like 'How you dey?' with immediate response."""
        try:
            # Save conversation state to track that a greeting was asked
            await self.memory.set_conversation_state(user_id, {
                'type': 'greeting_question_asked',
                'timestamp': datetime.now().isoformat()
            })
            
            greetings = [
                "I dey fine! How about you? What's on your mind?",
                "I'm doing great! How can I help you today?",
                "All good here! What would you like to do?",
                "I dey alright! Wetin you wan do today?",
                "Fine o! How can I assist you?"
            ]
            
            return random.choice(greetings)
            
        except Exception as e:
            return "I'm doing well! How can I help you today?"
    
    async def handle_conversational_response(self, user_id: str, message: str) -> str:
        """Handle conversational responses like 'I dey ask you' or 'You nko?'"""
        try:
            # These are Nigerian ways of returning the question
            responses = [
                "I dey fine o! Thanks for asking. What can I help you with?",
                "I'm doing well, thanks! What would you like to do today?",
                "All good on my side! How can I assist you?",
                "I dey alright! What's on your mind?",
                "Fine, thank you! Ready to help with anything you need."
            ]
            
            return random.choice(responses)
            
        except Exception as e:
            return "I'm doing well, thanks! How can I help you?"
    
    async def handle_denial_response(self, user_id: str, message: str) -> str:
        """Handle when user explicitly says they don't want something."""
        
        return random.choice(self.nigerian_responses["denial_response"])
    
    async def handle_correction_request(self, user_id: str, message: str) -> str:
        """Handle when user corrects or disputes provided information."""
        
        logger.info(f"User {user_id} is making a correction: {message}")
        
        # Check if they're talking about transfers specifically
        if any(word in message.lower() for word in ["sent", "transfer", "money i", "outgoing"]):
            return "I hear you! Let me get your transfer history for you. Give me a moment..."
        
        # General correction acknowledgment
        return random.choice(self.nigerian_responses["correction_response"])
    
    async def handle_complaint_request(self, user_id: str, message: str) -> str:
        """Handle user complaints or expressions of dissatisfaction."""
        
        return random.choice(self.nigerian_responses["complaint_response"])
    
    async def handle_repetition_complaint(self, user_id: str, message: str) -> str:
        """Handle when user complains about repeated questions."""
        try:
            # Clear any conversation state to avoid loops
            await self.memory.clear_conversation_state(user_id)
            
            return random.choice(self.nigerian_responses["repetition_complaint"])
            
        except Exception as e:
            return "Sorry about that! How can I help you today?"
    
    async def _get_recent_conversation_context(self, user_id: str) -> str:
        """Get recent conversation context for personalized responses."""
        try:
            if hasattr(self, 'memory') and self.memory:
                history = await self.memory.get_conversation_history(user_id, limit=5)
                if history:
                    context_parts = []
                    for msg in history[-3:]:  # Last 3 messages
                        if msg.get('role') == 'assistant' and len(msg.get('message', '')) > 20:
                            context_parts.append(f"Recent help: {msg.get('message', '')[:100]}")
                    return " | ".join(context_parts) if context_parts else "general conversation"
        except Exception as e:
            logger.error(f"Failed to get conversation context: {e}")
            return "general conversation"
    
    async def generate_ai_thanks_response(self, user_id: str, message: str, context: str | None = None) -> str:
        """Generate AI-powered personalized thanks response with two-way messaging."""
        try:
            # Send immediate acknowledgment response
            immediate_response = random.choice(self.nigerian_responses["thanks"])
            
            # Start background processing task (don't await it)
            asyncio.create_task(self._process_thanks_response_background(user_id, message, context))
            
            # Return immediate response to user
            return immediate_response
            
        except Exception as e:
            logger.error(f"Failed to start thanks response: {e}")
            # Fallback to simple response
            return random.choice(self.nigerian_responses["thanks"])
    
    async def _process_thanks_response_background(self, user_id: str, message: str, context: str | None):
        """Process personalized thanks response in background."""
        try:
            logger.info(f"🔄 Starting background thanks response for user {user_id}")
            
            # Get recent conversation context for personalization
            if not context:
                context = await self._get_recent_conversation_context(user_id)
            
            # Ensure context is never None - provide fallback
            if context is None:
                context = "general conversation"
            
            # Get AI-powered personalized response
            ai_response = await self._generate_ai_thanks_response_traditional(user_id, message, context)
            
            if ai_response and len(ai_response.strip()) > 10:
                # Send personalized AI response as follow-up
                await self._send_follow_up_message(user_id, ai_response)
                logger.info(f"✅ AI thanks response sent to user {user_id}")
            
        except Exception as e:
            logger.error(f"Background thanks response failed: {e}")
            # Don't send error follow-up for thanks responses
    
    async def _generate_ai_thanks_response_traditional(self, user_id: str, message: str, context: str) -> str:
        """Generate AI-powered personalized thanks response (traditional method)."""
        try:
            # Build personalized prompt
            system_prompt = """You are a friendly Nigerian financial assistant. The user just thanked you. 
            Generate a warm, personalized response that:
            1. Acknowledges their thanks naturally
            2. References recent help you provided (if context given)  
            3. Encourages them to ask for more help
            4. Uses Nigerian expressions naturally
            5. Keep it brief (1-2 sentences max)
            6. Sound genuinely helpful and encouraging"""
            
            user_prompt = f"""User said: "{message}"
            Recent conversation context: {context}
            
            Generate a warm, personalized response that makes them feel valued and encourages them to keep using the service."""
            
            # Check if AI is available
            if not self.ai_enabled or not self.ai_client or not self.ai_model:
                return "You're very welcome! Happy to help anytime! 😊"
            
            # Ensure we have a valid model string (type safety)
            model_str = self.ai_model if self.ai_model else "gpt-3.5-turbo"
            
            # Use the same pattern as other AI methods in the class
            completion = await self.ai_client.chat.completions.create(
                model=model_str,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                max_tokens=100,  # Keep responses short
                temperature=0.7  # Natural but consistent
            )
            
            # Handle potential None content
            raw_content = completion.choices[0].message.content
            ai_response = raw_content.strip() if raw_content else ""
            
            # Ensure we always return a string
            if ai_response and len(ai_response.strip()) > 10:
                return ai_response.strip()
            else:
                # Fallback response
                return "You're very welcome! Happy to help anytime! 😊"
            
        except Exception as e:
            logger.error(f"AI thanks response generation failed: {e}")
            return "You're very welcome! Feel free to ask me anything else! 😊"
    
    async def generate_smart_response(self, user_id: str, message: str, context: Dict) -> str:
        """Generate smart response using AI."""
        try:
            if not self.ai_enabled or not self.ai_client:
                return "I'm currently processing your request. Please wait a moment."
            
            # Generate AI response
            response = await self._generate_ai_response(user_id, message, context)
            
            # Ensure we always return a string
            if response and isinstance(response, str):
                return response.strip()
            else:
                return "I'm processing your request. Please wait a moment."
                
        except Exception as e:
            logger.error(f"Smart response generation failed: {e}")
            return "I'm currently processing your request. Please try again."

    def _build_system_prompt(self, context: Dict) -> str:
        """Build system prompt for AI responses."""
        try:
            base_prompt = """You are TizBot, a smart and conversational Nigerian banking assistant with perfect memory of all conversations and banking operations.

🤖 **CORE IDENTITY:**
- Name: TizBot (sometimes called TizLion AI)
- Personality: Friendly, smart, conversational, relatable
- Origin: Nigerian AI assistant specializing in banking but capable of general conversation
- Behavior: Like ChatGPT but with Nigerian flair and banking expertise

💬 **CONVERSATIONAL STYLE:**
- Always respond naturally and conversationally
- Use Nigerian expressions and Pidgin English when appropriate
- Never give robotic or template responses
- Remember and reference previous conversations
- Be genuinely helpful and engaging

🧠 **MEMORY & CONTEXT:**
- You have perfect memory of all previous conversations with each user
- Reference past interactions, amounts, names, and topics naturally
- Build on previous conversations without repeating information
- Maintain conversational flow across multiple messages

IMPORTANT: When users ask follow-up questions about previous topics:
- Reference the specific details they're asking about
- Use the banking operation context to provide accurate information
- Don't give generic responses - be specific and contextual"""

            # Add context-specific information
            if context.get('banking_operations'):
                base_prompt += "\n\nRecent banking operations:\n"
                for op in context['banking_operations'][-3:]:
                    op_type = op.get('operation_type', 'unknown')
                    success = op.get('success', False)
                    base_prompt += f"- {op_type}: {'✅' if success else '❌'}\n"
            
            if context.get('transaction_context'):
                base_prompt += f"\n\nTransaction context available: {len(context['transaction_context'])} transactions"
            
            return base_prompt
            
        except Exception as e:
            logger.error(f"Failed to build system prompt: {e}")
            return "You are TizBot, a smart and conversational Nigerian banking assistant. Be naturally helpful and engaging while assisting with banking needs."
    
    async def _generate_ai_response(self, user_id: str, message: str, context: Dict) -> str:
        """Generate AI response with proper error handling."""
        try:
            # Build AI prompt
            system_prompt = self._build_system_prompt(context)
            
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": message}
            ]
            
            completion = await self.ai_client.chat.completions.create(
                model=self.ai_model,
                messages=messages,
                max_tokens=300,
                temperature=0.7
            )
            
            response = cast(str, completion.choices[0].message.content)
            
            # Ensure we always return a string
            if response and isinstance(response, str):
                return response.strip()
            else:
                return "I'm processing your request. Please wait a moment."
                
        except Exception as e:
            logger.error(f"AI response generation failed: {e}")
            return "I'm currently processing your request. Please try again."
    
    # Methods required by financial_agent_refactored.py
    async def handle_conversation_request(self, user_id: str, message: str) -> str:
        """Handle general conversation requests with comprehensive AI-powered context awareness."""
        
        # Use enhanced AI conversation system for better context understanding
        if self.ai_enabled and self.ai_client:
            try:
                # Get comprehensive conversation context
                context = await self.memory.get_smart_conversation_context(user_id, message)
                
                # Enhanced system prompt for context-aware responses
                system_prompt = """You are TizBot, a smart and conversational Nigerian banking assistant with perfect memory of all conversations and banking operations.

🤖 **CORE IDENTITY:**
- Name: TizBot (sometimes called TizLion AI)
- Personality: Friendly, smart, conversational, relatable
- Origin: Nigerian AI assistant specializing in banking but capable of general conversation
- Behavior: Like ChatGPT but with Nigerian flair and banking expertise

💬 **CONVERSATIONAL STYLE:**
- Always respond naturally and conversationally
- Use Nigerian expressions and Pidgin English when appropriate
- Never give robotic or template responses
- Remember and reference previous conversations
- Be genuinely helpful and engaging

🧠 **MEMORY & CONTEXT:**
- You have perfect memory of all previous conversations with each user
- Reference past interactions, amounts, names, and topics naturally
- Build on previous conversations without repeating information
- Maintain conversational flow across multiple messages

IMPORTANT: When users ask follow-up questions about previous topics:
- Reference the specific details they're asking about
- Use the banking operation context to provide accurate information
- Don't give generic responses - be specific and contextual"""

                # Build context-aware messages
                messages = [{"role": "system", "content": system_prompt}]
                
                # Add banking operations context
                banking_ops = context.get('banking_operations', [])
                if banking_ops:
                    banking_context = "Recent banking operations:\n"
                    for op in banking_ops[-3:]:
                        op_type = op.get('operation_type', 'unknown')
                        success = op.get('success', False)
                        op_data = op.get('operation_data', {})
                        banking_context += f"- {op_type}: {'✅' if success else '❌'} {op_data}\n"
                    
                    messages.append({"role": "system", "content": banking_context})
                
                # Add transaction context if available
                transaction_context = context.get('transaction_context')
                if transaction_context:
                    tx_context = f"Transaction context: {json.dumps(transaction_context, indent=2)}"
                    messages.append({"role": "system", "content": tx_context})
                
                # Add conversation history for context
                conversations = context.get('recent_conversations', [])
                for conv in conversations[-4:]:  # Include more context
                    role = "user" if conv.get("role") == "user" else "assistant"
                    content = conv.get("message", "")
                    if content and not content.startswith("["):  # Skip system messages
                        messages.append({"role": role, "content": content})
                
                # Add current message
                messages.append({"role": "user", "content": message})
                
                # Generate AI response with enhanced context
                completion = await self.ai_client.chat.completions.create(
                    model=self.ai_model,
                    messages=messages,
                    max_tokens=300,  # Allow longer responses for detailed context
                    temperature=0.7
                )
                
                response = completion.choices[0].message.content
                if response and response.strip():
                    # Enhance response with additional context if needed
                    enhanced_response = await self.memory.enhance_ai_response_with_context(
                        user_id, message, response.strip()
                    )
                    return enhanced_response
                
            except Exception as e:
                logger.error(f"Enhanced AI conversation failed: {e}")
                # Fall through to pattern matching
        
        # Fallback to pattern matching for non-AI or AI failure cases
        message_lower = message.lower()
        
        # Handle beneficiary-related requests
        if any(word in message_lower for word in ["beneficiar", "contact", "saved", "recipient"]):
            if any(word in message_lower for word in ["list", "show", "get", "display"]):
                template_response = "You don't have any saved recipients yet! \n\nTo save contacts:\n• Send money with their details: \"Send 5k to John at 0123456789 GTBank\"\n• Or add directly: \"Add 0123456789 Access Bank as John\""
        
                # Import ResponseFormatter for LLM refinement
                from app.utils.response_utils import ResponseFormatter
                formatter = ResponseFormatter(self.ai_client, self.ai_model)
                
                context = {'user_id': user_id, 'recipients_count': 0}
                return await formatter.refine_with_llm(template_response, context, 'list_beneficiaries')
            else:
                return "To add a beneficiary, I need:\n• Account number (10 digits)\n• Bank name\n\n**Examples:**\n• \"Add 0123456789 GTBank as John\"\n• \"Save 0123456789 Access Bank as John\""
        
        # Enhanced conversation patterns with context awareness
        if any(word in message_lower for word in ['what', 'which', 'that', 'this', 'explain']):
            # This is likely a follow-up question - try to provide context
            return await self._handle_contextual_inquiry(user_id, message)
        
        return await self.handle_general_conversation(user_id, message)
    
    async def _handle_contextual_inquiry(self, user_id: str, message: str) -> str:
        """Handle contextual inquiries that reference previous conversations."""
        try:
            # Get smart context for the inquiry
            context = await self.memory.get_smart_conversation_context(user_id, message)
            query_analysis = context.get('query_analysis', {})
            
            # If user is asking about a specific transaction amount
            if query_analysis.get('references_amount'):
                amount_ref = query_analysis['references_amount']
                
                # Look for transaction context
                transaction_context = context.get('transaction_context')
                if transaction_context:
                    transactions = transaction_context.get('detailed_transactions', [])
                    for tx in transactions:
                        tx_amount = tx.get('amount', 0)
                        
                        # Match the amount reference
                        if amount_ref == '4k' and abs(tx_amount - 4000) < 500:
                            date = tx.get('date', '')[:10] if tx.get('date') else 'recently'
                            tx_type = tx.get('type', 'transfer')
                            return f"That ₦{tx_amount:,.0f} transaction was a {tx_type} that came in on {date} - it's what boosted your balance recently!"
                        
                        elif amount_ref == '5k' and abs(tx_amount - 5000) < 500:
                            date = tx.get('date', '')[:10] if tx.get('date') else 'recently'
                            tx_type = tx.get('type', 'transfer')
                            return f"The ₦{tx_amount:,.0f} was a {tx_type} from {date}."
                
                # Check recent conversations for amount mentions
                conversations = context.get('recent_conversations', [])
                for conv in reversed(conversations):
                    if conv.get('role') == 'assistant' and amount_ref in conv.get('message', '').lower():
                        return f"I mentioned that {amount_ref} amount based on your recent transaction activity. Would you like me to show you your detailed transaction history?"
            
            # General contextual response
            return "I'm here to help you with your banking needs. What specific information would you like to know?"
            
        except Exception as e:
            logger.error(f"Contextual inquiry handling failed: {e}")
            return "I'm listening! How can I assist you today?"
    
    async def handle_general_conversation(self, user_id: str, message: str) -> str:
        """Handle general conversation with enhanced TizBot persona."""
        try:
            if not self.ai_enabled or not self.ai_client:
                return await self._handle_intelligent_fallback(user_id, message)
            
            # Get conversation history for context
            conversation_history = await self.memory.get_conversation_history(user_id, limit=6)
            
            # Build TizBot system prompt
            system_prompt = self._build_tizbot_system_prompt()
            
            # Prepare conversation context
            context_messages = []
            if conversation_history:
                for msg in conversation_history[-4:]:  # Last 4 messages for context
                    role = "user" if msg.get("role") == "user" else "assistant"
                    content = msg.get("message", "")
                    if content and not content.startswith("["):  # Skip system messages
                        context_messages.append({"role": role, "content": content})
            
            # Add current message
            context_messages.append({"role": "user", "content": message})
            
            # Generate AI response
            completion = await self.ai_client.chat.completions.create(
                model=self.ai_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    *context_messages
                ],
                max_tokens=200,
                temperature=0.8
            )
            
            raw_content = completion.choices[0].message.content
            ai_response = raw_content.strip() if raw_content else "I'm here to help! What's on your mind?"
            
            # Ensure response isn't too long
            if len(ai_response) > 400:
                ai_response = ai_response[:397] + "..."
                
            return ai_response
            
        except Exception as e:
            logger.error(f"General conversation failed: {e}")
            return await self._handle_intelligent_fallback(user_id, message)
    
    async def _get_transaction_context(self, user_id: str, message: str) -> Optional[str]:
        """Get stored transaction context for the user."""
        try:
            # Look for transaction context in recent messages
            conversation_history = await self.memory.get_conversation_history(user_id, limit=10)
            
            for msg in conversation_history:
                if (msg.get("role") == "system" and 
                    msg.get("message") == "[Transaction Context]" and
                    msg.get("metadata", {}).get("type") == "transaction_context"):
                    
                    context = msg.get("metadata", {}).get("context", {})
                    
                    # Extract relevant transaction info based on user message
                    if "4k" in message.lower() or "4000" in message.lower():
                        # Look for 4k transaction
                        for tx in context.get("recent_transactions", []):
                            if abs(tx.get("amount", 0) - 4000) < 100:  # Within 100 of 4k
                                return f"₦{tx['amount']:,.0f} {tx['type']} transaction from {tx['date'][:10]} - {tx['description']}"
                    
                    # Return recent transaction info
                    recent_txs = context.get("recent_transactions", [])
                    if recent_txs:
                        latest_tx = recent_txs[0]
                        return f"₦{latest_tx['amount']:,.0f} {latest_tx['type']} transaction from {latest_tx['date'][:10]}"
                    
            return None
            
        except Exception as e:
            logger.error(f"Failed to get transaction context: {e}")
            return None
    
    async def handle_greeting(self, user_id: str, message: str = "") -> str:
        """Handle greeting messages with natural responses."""
        
        # Natural greeting responses based on message content
        if any(word in message.lower() for word in ["morning", "afternoon", "evening"]):
            return random.choice([
                "Good morning! How can I help you today?",
                "Morning! What's on your mind?",
                "Good day! Ready to handle some banking?",
                "Hey there! How's your day going?"
            ])
        
        if any(word in message.lower() for word in ["hi", "hello", "hey"]):
            return random.choice([
                "Hey! I'm here if you need help with your account or transfers. 👍",
                "Hello! What brings you here today?",
                "Hi there! Need help with anything?",
                "Hey! Ready to check your balance or send some money?"
            ])
        
        # Default natural greeting
        return random.choice([
            "Hello! How can I assist you today?",
            "Hi! What would you like to do?",
            "Hey there! I'm here to help with your banking needs.",
            "Good to see you! What can I help you with?"
        ])
    
    async def handle_intelligent_fallback(self, user_id: str, message: str) -> str:
        """Intelligent fallback when no specific intent is detected."""
        
        message_lower = message.lower()
        
        # Handle banking-related queries naturally
        if any(word in message_lower for word in ["transaction", "history", "summary", "detailed"]):
            return random.choice([
                "I can show you your transaction history! Just ask me to check your recent transactions.",
                "Want to see your money movements? I can pull up your transaction history.",
                "I can give you a detailed summary of your account activity.",
                "Your transaction history is something I can show you right now."
            ])
        
        # Handle transfer-related inquiries
        if any(word in message_lower for word in ["send", "transfer", "money"]):
            return random.choice([
                "I can help you send money to any Nigerian bank. Just tell me who you're sending to and how much.",
                "Need to transfer money? I can help you do that quickly and safely.",
                "I can help you send money to friends, family, or anyone else. What amount are you thinking?",
                "Ready to send some money? I can walk you through the process."
            ])
        
        # Handle balance inquiries
        if any(word in message_lower for word in ["balance", "how much", "account"]):
            return random.choice([
                "I can check your balance for you right now. Want me to show you?",
                "Your account balance is something I can check instantly.",
                "I can show you exactly how much you have in your account.",
                "Want to know your balance? I can tell you that right away."
            ])
        
        # Handle confusion or negative responses
        if any(word in message_lower for word in ["not", "don't", "confused", "wrong"]):
            return random.choice([
                "No worries! Let me know what you need help with and I'll do my best to assist.",
                "I understand! What would you like me to help you with instead?",
                "That's okay! How can I help you today?",
                "No problem! What can I do for you?"
            ])
        
        # Handle general inquiries
        if any(word in message_lower for word in ["help", "what", "how", "can you"]):
            return random.choice([
                "I can help you with checking your balance, sending money, or viewing your transaction history. What interests you?",
                "I'm here to help with your banking needs - transfers, balance checks, transaction history, and more!",
                "I can assist with money transfers, account balance, transaction history, and general banking questions.",
                "I'm your banking assistant! I can help with transfers, balance checks, and transaction history."
            ])
        
        # Default intelligent response
        return random.choice([
            "I'm here to help! You can ask me about your balance, send money, or check your transaction history.",
            "What would you like to do? I can help with banking tasks or just have a chat.",
            "I'm ready to assist! Whether it's checking your balance, sending money, or reviewing transactions.",
            "How can I help you today? I'm here for all your banking needs."
        ])
    
    async def handle_thanks_response(self, user_id: str, message: str, send_follow_up_callback=None) -> str:
        """Handle thanks responses with optional follow-up callback."""
        try:
            if send_follow_up_callback:
                # Use AI-powered thanks response with follow-up
                context = await self._get_recent_conversation_context(user_id)
                return await self.generate_ai_thanks_response(user_id, message, context)
            else:
                # Simple thanks response
                return random.choice(self.nigerian_responses["thanks"])
        except Exception as e:
            logger.error(f"Thanks response failed: {e}")
            return "Happy to help! Is there anything else you need?" 