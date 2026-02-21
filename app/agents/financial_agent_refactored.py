#!/usr/bin/env python3
"""
Refactored Financial Agent
Main coordinator that uses specialized handler modules for different banking operations.
"""

import asyncio
import logging
import random
from typing import Dict, Optional, Any
from app.utils.logger import get_logger
from app.services.paystack_service import PaystackService
from app.utils.memory_manager import MemoryManager
from app.utils.recipient_manager import RecipientManager
from datetime import datetime

# Import specialized handlers
from app.agents.message_processor import MessageProcessor
from app.agents.balance_handler import BalanceHandler
from app.agents.transfer_handler import TransferHandler
from app.agents.history_handler import HistoryHandler
from app.agents.beneficiary_handler import BeneficiaryHandler
from app.agents.ai_handler import AIHandler
from app.agents.response_handler import ResponseHandler
from app.agents.conversation_state import ConversationState
from app.receipts.generator import generate_receipt_image
from app.utils.bank_resolver import BankResolver
from app.utils.amount_converter import AmountConverter

logger = get_logger("financial_agent")


class FinancialAgent:
    """
    Refactored Financial Agent - Main coordinator for banking operations.
    
    This agent delegates specialized tasks to focused handler modules:
    - MessageProcessor: Intent detection and entity extraction
    - BalanceHandler: Balance checks and related operations
    - TransferHandler: Money transfers and confirmations
    - HistoryHandler: Transaction history and reporting
    - BeneficiaryHandler: Contact/recipient management
    - AIHandler: AI conversations and responses
    - ResponseHandler: Response formatting and utilities
    - ConversationState: State management for multi-step flows
    """
    
    def __init__(self, paystack_service: PaystackService, memory_manager: MemoryManager, 
                 recipient_manager: RecipientManager, ai_client=None, ai_model=None, ai_enabled=False):
        
        # Core services
        self.paystack = paystack_service
        self.memory = memory_manager
        self.recipient_manager = recipient_manager
        
        # AI configuration
        self.ai_client = ai_client
        self.ai_model = ai_model
        self.ai_enabled = ai_enabled
        
        # Initialize specialized handlers
        self.message_processor = MessageProcessor()
        self.balance_handler = BalanceHandler(paystack_service, memory_manager, ai_client, ai_model, ai_enabled)
        self.transfer_handler = TransferHandler(paystack_service, memory_manager, ai_client, ai_model, ai_enabled)
        self.history_handler = HistoryHandler(paystack_service, memory_manager, ai_client, ai_model, ai_enabled)
        self.beneficiary_handler = BeneficiaryHandler(paystack_service, recipient_manager, memory_manager)
        self.ai_handler = AIHandler(memory_manager, ai_client, ai_model, ai_enabled)
        self.response_handler = ResponseHandler(ai_client, ai_model, ai_enabled)  # Updated with AI capabilities
        self.conversation_state = ConversationState()
        
        logger.info("✅ Financial Agent initialized with specialized handlers")
    
    async def process_message(
        self,
        user_id: str,
        message: str,
        send_follow_up_callback=None,
        send_receipt_callback=None,
    ) -> str:
        """
        Main message processing method with comprehensive memory and context storage.

        Args:
            user_id: User identifier
            message: User message
            send_follow_up_callback: Optional callback for sending follow-up messages
            send_receipt_callback: Optional callback for sending receipt images (e.g. Telegram)

        Returns:
            str: Response message
        """
        
        try:
            # Save user message to memory with enhanced context
            await self.memory.save_message(user_id, message, "user", {
                'intent_parsing': True,
                'session_active': True,
                'timestamp': datetime.utcnow().isoformat()
            })
            
            # Check for existing conversation state
            state = await self.memory.get_conversation_state(user_id)
            
            # Debug logging to see what's happening with conversation state
            if state:
                logger.info(f"🔍 Found conversation state for user {user_id}: type={state.get('type')}, expired={self.conversation_state.is_state_expired(state)}")
            else:
                logger.info(f"🔍 No conversation state found for user {user_id}")
            
            # If in a conversation state, handle the flow
            if state and not self.conversation_state.is_state_expired(state):
                # SMART STATE HANDLING: Check if this is a greeting/casual message during transaction
                temp_intent, temp_entities = self.message_processor.parse_message(message)
                
                if any(word in message.lower() for word in ['cancel', 'stop', 'abort', 'clear', 'restart', 'start over', 'never mind', 'nevermind']):
                    # User wants to cancel/restart - clear state and give fresh start
                    await self.memory.clear_conversation_state(user_id)
                    logger.info(f"🔄 User requested to cancel/restart - clearing conversation state")
                    
                    cancel_responses = [
                        "No problem! Transaction cancelled. What else can I help you with?",
                        "Got it! I've cancelled that transfer. How can I help you now?",
                        "Sure thing! Starting fresh. What would you like to do?",
                        "Okay! Transaction cleared. What can I do for you?"
                    ]
                    response = random.choice(cancel_responses)
                    
                elif temp_intent in ["greeting", "thanks", "casual_response"]:
                    # User is being friendly/casual while in a transaction - give contextual response
                    logger.info(f"🔄 User sent greeting/casual message during conversation state - providing contextual response")
                    response = await self._handle_greeting_during_transaction(user_id, message, state, temp_intent)
                else:
                    logger.info(f"🔄 Processing message through conversation state handler")
                    response = await self._handle_conversation_state(user_id, message, state, send_follow_up_callback, send_receipt_callback)
            else:
                # Clear expired state if exists
                if state:
                    await self.memory.clear_conversation_state(user_id)
                
                # Parse message for intent and entities
                intent, entities = self.message_processor.parse_message(message)
                logger.info(f"Detected intent: {intent}, entities: {entities}")
                
                # Save intent and entities for context
                await self.memory.save_message(user_id, f"[INTENT_PARSED: {intent}]", "system", {
                    'type': 'intent_parsing',
                    'intent': intent,
                    'entities': entities,
                    'parsed_message': message
                })
                
                # Route to appropriate handler based on intent
                response = await self._route_to_handler(user_id, message, intent, entities, send_follow_up_callback, send_receipt_callback)
            
            # Save assistant response to memory with metadata
            await self.memory.save_message(user_id, response, "assistant", {
                'response_generated': True,
                'response_length': len(response) if response else 0,
                'timestamp': datetime.utcnow().isoformat()
            })
            
            return response or "I'm here to help! What can I do for you?"
            
        except Exception as e:
            logger.error(f"Message processing failed: {e}")
            # Save error context
            await self.memory.save_message(user_id, f"[ERROR: {str(e)}]", "system", {
                'type': 'error',
                'error_message': str(e),
                'failed_message': message
            })
            # Use LLM-based error response instead of static template
            return await self._handle_error_response(user_id, message, str(e))
    
    async def _handle_conversation_state(self, user_id: str, message: str, state: Dict, send_follow_up_callback, send_receipt_callback=None) -> str:
        """Handle conversation states (confirmations, follow-ups, etc.)."""
        try:
            state_type = state.get("type")
            intent, entities = self.message_processor.parse_message(message)

            if self.conversation_state.should_clear_state(state, message):
                await self.memory.clear_conversation_state(user_id)
                return await self._route_to_handler(user_id, message, intent, entities, send_follow_up_callback, send_receipt_callback)

            if state_type in ["transfer_pending_confirmation", "direct_transfer_pending_confirmation", "beneficiary_transfer_pending_confirmation", "account_bank_amount_transfer_pending_confirmation"]:
                return await self._handle_pending_confirmation(user_id, message, state, send_follow_up_callback, send_receipt_callback)
            
            elif state_type == 'beneficiary_transfer_pending_amount':
                # Handle amount input for beneficiary transfer
                amount = self.conversation_state.extract_amount_from_message(message)
                if amount:
                    # Update state with amount and ask for confirmation
                    state['amount'] = amount
                    
                    # Check balance
                    balance_check = await self.balance_handler.check_sufficient_balance(amount)
                    if not balance_check['sufficient']:
                        await self.memory.clear_conversation_state(user_id)
                        return self.response_handler.format_error_response("insufficient_balance", 
                                                                         f"You're trying to send ₦{amount:,.2f} but your balance is {balance_check['formatted_balance']}.")
                    
                    # Set confirmation state
                    state['type'] = 'beneficiary_transfer_pending_confirmation'
                    await self.memory.set_conversation_state(user_id, state)
                    
                    formatted_amount = f"₦{amount:,.2f}"
                    return f"💰 **Transfer Confirmation**\n\nSend {formatted_amount} to **{state['account_name']}**?"
                else:
                    return "Please specify the amount you want to send (e.g., 5k, 5000, ₦5000)."
            
            elif state_type == 'account_resolution_pending_amount':
                # Handle amount input after account resolution
                logger.info(f"🔍 Processing amount input for account resolution: message='{message}'")
                amount = self.conversation_state.extract_amount_from_message(message)
                logger.info(f"🔍 Extracted amount: {amount}")
                if amount:
                    # Check balance
                    balance_check = await self.balance_handler.check_sufficient_balance(amount)
                    if not balance_check['sufficient']:
                        await self.memory.clear_conversation_state(user_id)
                        return self.response_handler.format_error_response("insufficient_balance", 
                                                                         f"You're trying to send ₦{amount:,.2f} but your balance is {balance_check['formatted_balance']}.")
                    
                    # Set confirmation state
                    state['type'] = 'direct_transfer_pending_confirmation'
                    state['amount'] = amount
                    await self.memory.set_conversation_state(user_id, state)
                    
                    formatted_amount = f"₦{amount:,.2f}"
                    return f"""💰 **Transfer Confirmation**

**You want to send:**
• Amount: {formatted_amount}
• To: {state['account_name']}
• Account: {state['account_number']}
• Bank: {state['bank_name'].title()}

Is this correct? Type "yes" to proceed or "no" to cancel."""
                else:
                    return "Please specify the amount you want to send (e.g., 5k, 5000, ₦5000)."
            
            elif state_type == 'account_resolved_pending_amount':
                # Handle amount input after account + bank resolution
                amount = self.conversation_state.extract_amount_from_message(message)
                if amount:
                    # Check balance
                    balance_check = await self.balance_handler.check_sufficient_balance(amount)
                    if not balance_check['sufficient']:
                        await self.memory.clear_conversation_state(user_id)
                        return self.response_handler.format_error_response("insufficient_balance", 
                                                                         f"You're trying to send ₦{amount:,.2f} but your balance is {balance_check['formatted_balance']}.")
                    
                    # Now resolve the account to get account name and proceed with confirmation
                    try:
                        account_info = await self.paystack.resolve_account(state['account_number'], state['bank_code'])
                        account_name = account_info.get('account_name', 'Unknown Account')
                        
                        # Set confirmation state
                        state['type'] = 'account_bank_amount_transfer_pending_confirmation'
                        state['amount'] = amount
                        state['account_name'] = account_name
                        await self.memory.set_conversation_state(user_id, state)
                        
                        formatted_amount = f"₦{amount:,.2f}"
                        confirmation_responses = [
                            f"💰 **Transfer Confirmation**\n\nSend {formatted_amount} to **{account_name}** at {state['bank_name']}?",
                            f"💰 **Transfer Confirmation**\n\nReady to transfer {formatted_amount} to **{account_name}** ({state['bank_name']})?"
                        ]
                        return random.choice(confirmation_responses)
                        
                    except Exception as e:
                        logger.error(f"Account resolution failed: {e}")
                        await self.memory.clear_conversation_state(user_id)
                        return f"I couldn't verify that {state['bank_name']} account {state['account_number']}. Please double-check the details and try again."
                else:
                    return "Please specify the amount you want to send (e.g., 5k, 5000, ₦5000)."
            
            # account_bank_amount_transfer_pending_confirmation is now handled by _handle_pending_confirmation above
            
            else:
                await self.memory.clear_conversation_state(user_id)
                return await self._route_to_handler(user_id, message, intent, entities, send_follow_up_callback, send_receipt_callback)
        except Exception as e:
            logger.error(f"Conversation state handling failed: {e}")
            await self.memory.clear_conversation_state(user_id)
            return await self._handle_error_response(user_id, message, str(e))

    async def _route_to_handler(self, user_id: str, message: str, intent: str, entities: Dict, send_follow_up_callback=None, send_receipt_callback=None) -> str:
        """Enhanced routing with clear separation between banking and conversational intents."""
        
        # Define banking intents that require specific handlers
        banking_intents = [
            "balance", "history", "transfers_sent", "people_sent_money",
            "transfer", "named_transfer_with_account", "beneficiary_transfer",
            "account_resolve", "account_bank_amount_transfer", "banks", "nickname_creation"
        ]
        
        # Define conversational intents that should use AI for ChatGPT-like responses
        conversational_intents = [
            "greeting", "thanks", "conversation", "conversational_response",
            "help", "complaint", "casual", "amount_only", "greeting_question",
            "greeting_response", "repetition_complaint", "denial"
        ]
        
        # Handle confirmation without conversation state separately
        if intent == "confirmation":
            return "I'm not sure what you're confirming right now. Is there anything I can help you with? 😊"
        
        if intent in banking_intents:
            return await self._handle_banking_intent(user_id, message, intent, entities, send_follow_up_callback, send_receipt_callback)

        elif intent in conversational_intents:
            return await self._handle_conversational_intent(user_id, message, intent, entities, send_follow_up_callback)

        elif intent == "conversation" and entities:
            transfer_context = await self._analyze_transfer_context(user_id, message, entities)
            if transfer_context:
                return await self._handle_conversational_transfer(user_id, message, entities, transfer_context, send_follow_up_callback)
            else:
                return await self._handle_conversational_intent(user_id, message, intent, entities, send_follow_up_callback)
        else:
            logger.info(f"Unknown intent '{intent}' - routing to AI handler for intelligent fallback")
            return await self._handle_conversational_intent(user_id, message, intent, entities, send_follow_up_callback)

    async def _handle_banking_intent(self, user_id: str, message: str, intent: str, entities: Dict, send_follow_up_callback=None, send_receipt_callback=None) -> str:
        """Handle banking-specific intents."""
        
        if intent == "balance":
            if send_follow_up_callback:
                return await self.balance_handler.handle_balance_check_with_ai(user_id, message, send_follow_up_callback)
            else:
                return await self.balance_handler.handle_balance_request(user_id, message)
        
        elif intent == "history":
            if send_follow_up_callback:
                return await self.history_handler.handle_history_request_with_ai(user_id, message, send_follow_up_callback)
            else:
                return await self.history_handler.handle_history_request(user_id, message, entities)
        
        elif intent == "transfers_sent":
            if send_follow_up_callback:
                return await self.history_handler.handle_transfers_sent_with_ai(user_id, message, send_follow_up_callback)
            else:
                return await self.history_handler.handle_transfers_sent_request(user_id, message, entities)
        
        elif intent == "people_sent_money":
            if send_follow_up_callback:
                return await self.history_handler.handle_people_sent_money_request(user_id, message, send_follow_up_callback)
            else:
                return await self.history_handler.handle_transfers_sent_request(user_id, message, entities)
        
        elif intent in ["transfer", "named_transfer_with_account"]:
            existing_state = await self.memory.get_conversation_state(user_id)
            if existing_state and existing_state.get("type") == "account_resolution_pending_amount":
                logger.info("Transfer intent detected but found existing account resolution state - using conversation state handler")
                return await self._handle_conversation_state(user_id, message, existing_state, send_follow_up_callback, send_receipt_callback)
            else:
                return await self.transfer_handler.handle_transfer_request(user_id, message, intent, entities, send_follow_up_callback)
        
        elif intent == "beneficiary_transfer":
            return await self.beneficiary_handler.handle_beneficiary_transfer(user_id, message, entities, self.memory, self.balance_handler)
        
        elif intent == "account_resolve":
            return await self.transfer_handler.handle_account_resolution(user_id, entities, self.memory, send_follow_up_callback)
        
        elif intent == "account_bank_amount_transfer":
            return await self._handle_account_bank_amount_transfer(user_id, message, entities, send_follow_up_callback, send_receipt_callback)
        
        elif intent == "banks":
            return await self._handle_banks_request(user_id, message)
        
        elif intent == "nickname_creation":
            return await self._handle_nickname_creation(user_id, message)
        
        else:
            # Fallback for unknown banking intent
            logger.error(f"Unknown banking intent: {intent}")
            return await self._handle_fallback_response(user_id, message)
    
    async def _handle_nickname_creation(self, user_id: str, message: str) -> str:
        """Handle nickname creation requests like 'remember yinka is my igbo plug'."""
        try:
            # Extract nickname mapping from the message
            nickname_mapping = self.message_processor.extract_nickname_mapping(message)
            
            if not nickname_mapping:
                return "I couldn't understand the nickname you want to create. Please try: 'Remember [name] is my [nickname]'"
            
            recipient_name = nickname_mapping['recipient_name']
            custom_nickname = nickname_mapping['custom_nickname']
            
            # Use the same recipient lookup system as transfers (checks both MongoDB and Paystack)
            try:
                from app.utils.recipient_cache import RecipientCache
                recipient_cache = RecipientCache(self.paystack, self.recipient_manager)
                
                # Check if recipient exists (same as transfer flow)
                recipient = await recipient_cache.find_recipient_by_name(user_id, recipient_name)
                
                if not recipient:
                    return f"I couldn't find **{recipient_name}** in your recipients. Please send money to them first, then I can create the nickname."
                
                # If found in Paystack but not in MongoDB, save to MongoDB first
                if recipient.get('source') == 'paystack':
                    # Save the Paystack recipient to MongoDB first
                    await self.memory.save_recipient(user_id, {
                        'account_name': recipient['account_name'],
                        'account_number': recipient['account_number'],
                        'bank_name': recipient['bank_name'],
                        'bank_code': recipient['bank_code'],
                        'nickname': recipient_name
                    })
                    logger.info(f"✅ Imported Paystack recipient {recipient_name} to MongoDB for nickname creation")
                
                # Now save the custom nickname
                success = await self.memory.save_recipient_nickname(
                    user_id=user_id,
                    recipient_name=recipient_name,
                    custom_nickname=custom_nickname,
                    recipient_data=recipient
                )
                
                if success:
                    return f"✅ Got it! I'll remember **{recipient_name}** as your **{custom_nickname}**.\n\nNow you can say 'Send 5k to my {custom_nickname}' and I'll know who you mean! 😊"
                else:
                    return f"Sorry, I couldn't save that nickname. Please try again."
                    
            except ImportError:
                # Fallback to original method if recipient_cache not available
                recipient = await self.recipient_manager.find_recipient_by_name(user_id, recipient_name)
                
                if not recipient:
                    return f"I couldn't find **{recipient_name}** in your saved recipients. Please send money to them first, then I can create the nickname."
                
                success = await self.memory.save_recipient_nickname(
                    user_id=user_id,
                    recipient_name=recipient_name,
                    custom_nickname=custom_nickname,
                    recipient_data=recipient
                )
                
                if success:
                    return f"✅ Got it! I'll remember **{recipient_name}** as your **{custom_nickname}**.\n\nNow you can say 'Send 5k to my {custom_nickname}' and I'll know who you mean! 😊"
                else:
                    return f"Sorry, I couldn't save that nickname. Please try again."
                
        except Exception as e:
            logger.error(f"Nickname creation failed: {e}")
            return "Something went wrong while creating the nickname. Please try again."

    async def _handle_conversational_intent(self, user_id: str, message: str, intent: str, entities: Dict, send_follow_up_callback=None) -> str:
        """Handle conversational intents with ChatGPT-like AI responses."""
        
        # For simple social interactions, provide instant responses without "thinking" delays
        instant_response_intents = ["greeting", "thanks", "greeting_response", "confirmation", "denial"]
        
        if intent in instant_response_intents and not send_follow_up_callback:
            # Provide instant LLM response without two-way messaging
            if intent == "greeting":
                return await self.response_handler.format_greeting_response(message)
            elif intent == "thanks":
                return await self.response_handler.format_thanks_response(message)
            elif intent == "greeting_response":
                return await self.response_handler.format_casual_response(message)
            elif intent in ["confirmation", "denial"]:
                return await self.response_handler.format_casual_response(message)
        
        # For complex conversational intents or when follow-up is needed, use AI handler
        if send_follow_up_callback:
            return await self.ai_handler.handle_ai_conversation_with_callback(user_id, message, send_follow_up_callback)
        else:
            return await self.ai_handler.handle_general_conversation(user_id, message)

    async def _analyze_transfer_context(self, user_id: str, message: str, entities: Dict) -> Optional[Dict]:
        """Analyze if this is a transfer-related conversation that needs assistance."""
        
        # Check if entities contain transfer-related information
        has_account = 'account_number' in entities
        has_bank = 'bank_name' in entities or 'bank_code' in entities
        has_amount = 'amount' in entities
        
        # Check for transfer-related keywords in message
        transfer_keywords = ['send', 'transfer', 'pay', 'opay', 'kuda', 'access', 'gtb', 'account']
        has_transfer_context = any(keyword in message.lower() for keyword in transfer_keywords)
        
        if has_transfer_context and (has_account or has_bank or has_amount):
            return {
                'type': 'incomplete_transfer',
                'has_account': has_account,
                'has_bank': has_bank,
                'has_amount': has_amount,
                'entities': entities
            }
        
        return None

    async def _handle_conversational_transfer(self, user_id: str, message: str, entities: Dict, context: Dict, send_follow_up_callback) -> str:
        """Handle conversational transfer building with human-like assistance."""
        
        has_account = context.get('has_account', False)
        has_bank = context.get('has_bank', False)
        has_amount = context.get('has_amount', False)
        
        # Get current conversation state
        current_state = await self.memory.get_conversation_state(user_id)
        
        if has_account and has_bank:
            # We have account and bank, but no amount - this is likely "Opay 8181648623" scenario
            account_number = entities['account_number']
            bank_name = entities.get('bank_name', 'Unknown Bank')
            bank_code = entities.get('bank_code')
            
            if not bank_code:
                # Try to resolve bank code from name
                bank_code = BankResolver.resolve_bank_code(bank_name)
            
            if bank_code:
                # Store this information and ask what they want to do
                await self.memory.set_conversation_state(user_id, {
                    'type': 'account_identified',
                    'account_number': account_number,
                    'bank_name': bank_name,
                    'bank_code': bank_code,
                    'timestamp': datetime.utcnow().isoformat()
                })
                
                # Generate human-like response
                human_responses = [
                    f"I see you mentioned that {bank_name.title()} account {account_number}. What would you like to do with it? Send money or just verify the account?",
                    f"Got it - {bank_name.title()} account {account_number}. Are you looking to send money to this account or check something else?",
                    f"That's a {bank_name.title()} account number. Do you want to send money to {account_number} or need help with something else?",
                    f"I notice you mentioned {account_number} for {bank_name.title()}. Want to send money there or just checking the account?"
                ]
                return random.choice(human_responses)
            
        elif has_account and has_amount:
            # Has account and amount but missing bank - ask for bank
            account_number = entities['account_number']
            amount = entities['amount']
            
            await self.memory.set_conversation_state(user_id, {
                'type': 'transfer_missing_bank',
                'account_number': account_number,
                'amount': amount,
                'timestamp': datetime.utcnow().isoformat()
            })
            
            human_responses = [
                f"I see you want to send ₦{amount:,} to {account_number}. Which bank is this account with?",
                f"Got the amount (₦{amount:,}) and account number ({account_number}). What bank should I send to?",
                f"Perfect! ₦{amount:,} to {account_number}. Just need to know which bank this account belongs to.",
                f"I have ₦{amount:,} for {account_number}. Which bank is this account with?"
            ]
            return random.choice(human_responses)
            
        elif has_bank and has_amount:
            # Has bank and amount but missing account number
            bank_name = entities.get('bank_name', 'that bank')
            amount = entities['amount']
            
            await self.memory.set_conversation_state(user_id, {
                'type': 'transfer_missing_account',
                'bank_name': bank_name,
                'amount': amount,
                'timestamp': datetime.utcnow().isoformat()
            })
            
            human_responses = [
                f"So you want to send ₦{amount:,} to someone at {bank_name.title()}. What's their account number?",
                f"₦{amount:,} to {bank_name.title()} - got it! What's the account number?",
                f"I have the amount (₦{amount:,}) and bank ({bank_name.title()}). Just need the account number to send the money.",
                f"Ready to send ₦{amount:,} to {bank_name.title()}! What account number should I send to?"
            ]
            return random.choice(human_responses)
        
        else:
            # Partial information - provide helpful guidance
            if current_state and current_state.get('type') == 'account_identified':
                # User previously mentioned an account, now they might be saying what to do
                stored_account = current_state.get('account_number')
                stored_bank = current_state.get('bank_name')
                
                if 'send' in message.lower() or has_amount:
                    amount = entities.get('amount')
                    if amount:
                        # They want to send money and specified amount
                        return await self._proceed_with_transfer(user_id, current_state, amount, send_follow_up_callback)
                    else:
                        # They want to send but no amount yet
                        human_responses = [
                            f"Perfect! How much do you want to send to that {stored_bank} account ({stored_account})?",
                            f"Got it! What amount should I send to {stored_account} ({stored_bank})?",
                            f"Sure thing! How much money do you want to send to that {stored_bank} account?",
                            f"No problem! What's the amount you want to transfer to {stored_account}?"
                        ]
                        return random.choice(human_responses)
                        
                elif any(word in message.lower() for word in ['check', 'verify', 'resolve', 'who']):
                    # They want to verify the account
                    return await self._verify_account_human_style(user_id, current_state, send_follow_up_callback)
            
            # Default helpful response for incomplete transfer context
            transfer_help_responses = [
                "I can help you send money! I'll need the amount, account number, and bank name. Try something like 'Send 5000 to 1234567890 GTBank'",
                "Want to send money? Just tell me how much, the account number, and which bank. Like 'Transfer 2k to 9876543210 Opay'",
                "I'm here to help with transfers! Give me the amount, account number and bank name all together and I'll take care of it.",
                "To send money, I need three things: amount, account number, and bank. Try 'Send 1500 to 1122334455 Kuda'"
            ]
            return random.choice(transfer_help_responses)

    async def _proceed_with_transfer(self, user_id: str, stored_state: Dict, amount: int, send_follow_up_callback) -> str:
        """Proceed with transfer using stored account information."""
        
        # Create complete transfer entities
        entities = {
            'amount': amount,
            'account_number': stored_state['account_number'],
            'bank_name': stored_state['bank_name'],
            'bank_code': stored_state['bank_code']
        }
        
        # Clear the temporary state
        await self.memory.clear_conversation_state(user_id)
        
        # Process as a normal transfer
        return await self.transfer_handler.handle_transfer_request(
            user_id, f"Send {amount} to {entities['account_number']} {entities['bank_name']}", 
            "transfer", entities, send_follow_up_callback
        )

    async def _verify_account_human_style(self, user_id: str, stored_state: Dict, send_follow_up_callback) -> str:
        """Verify account with human-like response."""
        
        entities = {
            'account_number': stored_state['account_number'],
            'bank_name': stored_state['bank_name'],
            'bank_code': stored_state['bank_code']
        }
        
        # Clear the temporary state
        await self.memory.clear_conversation_state(user_id)
        
        # Process as account resolution
        return await self.transfer_handler.handle_account_resolution(user_id, entities, self.memory, send_follow_up_callback)
    
    async def _handle_pending_confirmation(self, user_id: str, message: str, state: Dict, send_follow_up_callback, send_receipt_callback=None) -> str:
        """Handle pending confirmation for transfers."""
        try:
            state_type = state.get("type")
            intent, entities = self.message_processor.parse_message(message)
            confirmed = self.conversation_state.extract_confirmation_from_message(message)

            if confirmed == "yes" or intent == "confirmation":
                if state_type == "beneficiary_transfer_pending_confirmation":
                    return await self._process_beneficiary_transfer_confirmation(user_id, state, send_follow_up_callback, send_receipt_callback)
                elif state_type == "direct_transfer_pending_confirmation":
                    return await self._process_direct_transfer_confirmation(user_id, state, send_follow_up_callback, send_receipt_callback)
                elif state_type == "transfer_pending_confirmation":
                    return await self._process_direct_transfer_confirmation(user_id, state, send_follow_up_callback, send_receipt_callback)
                elif state_type == "account_bank_amount_transfer_pending_confirmation":
                    return await self._handle_account_bank_amount_confirmation(user_id, message, state, send_follow_up_callback, send_receipt_callback)
                else:
                    await self.memory.clear_conversation_state(user_id)
                    return "Something went wrong with the confirmation. Please try again."
            elif confirmed == "no" or intent == "denial":
                await self.memory.clear_conversation_state(user_id)
                return "Transfer cancelled. What else can I help you with?"
            else:
                if intent in ["balance", "history", "list_beneficiaries", "greeting", "banks"]:
                    await self.memory.clear_conversation_state(user_id)
                    return await self._route_to_handler(user_id, message, intent, entities, send_follow_up_callback, send_receipt_callback)
                else:
                    # Unclear response, ask for clarification
                    return "Please respond with 'yes' to confirm or 'no' to cancel the transfer."
                
        except Exception as e:
            logger.error(f"Pending confirmation handling failed: {e}")
            await self.memory.clear_conversation_state(user_id)
            return await self._handle_error_response(user_id, message, str(e))
    
    async def _process_beneficiary_transfer_confirmation(self, user_id: str, state: Dict, send_follow_up_callback, send_receipt_callback=None) -> str:
        """Process confirmed beneficiary transfer."""
        try:
            amount = state.get('amount')
            recipient_code = state.get('recipient_code')
            account_name = state.get('account_name')
            account_number = state.get('account_number')
            bank_code = state.get('bank_code')
            bank_name = state.get('bank_name')
            
            # Clear conversation state first
            await self.memory.clear_conversation_state(user_id)
            
            if not amount:
                return "Transfer amount is missing. Please try again."
            
            # If we have a recipient_code (from existing beneficiary), use it directly
            if recipient_code:
                logger.info(f"Processing transfer using existing recipient code: {recipient_code}")
                
                # Initiate transfer using existing recipient
                transfer_data = await self.paystack.initiate_transfer(
                    amount=AmountConverter.to_kobo(amount),
                    recipient_code=recipient_code,
                    reason=f"Transfer via TizLion AI to {account_name}"
                )
                
                if transfer_data and transfer_data.get('status'):
                    # Save transfer record to database for tracking
                    transfer_record = {
                        'amount': amount,
                        'recipient': account_name,
                        'account_number': account_number,
                        'bank_code': bank_code,
                        'bank_name': bank_name,
                        'reference': transfer_data.get('reference', f"BEN_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"),
                        'status': transfer_data.get('status', 'unknown'),
                        'reason': f"Transfer via TizLion AI to {account_name}",
                        'timestamp': datetime.utcnow().isoformat(),
                        'paystack_response': transfer_data
                    }
                    
                    await self.memory.save_transfer(user_id, transfer_record)
                    
                    # Save transfer context
                    await self.memory.save_banking_operation_context(
                        user_id=user_id,
                        operation_type="transfer_completed",
                        operation_data={
                            'amount': amount,
                            'recipient_code': recipient_code,
                            'account_name': account_name,
                            'transfer_id': transfer_data.get('data', {}).get('id')
                        },
                        api_response=transfer_data
                    )
                    asyncio.create_task(
                        self._generate_and_send_receipt(user_id, transfer_record, send_follow_up_callback, send_receipt_callback)
                    )
                    return f"✅ **Transfer Successful**\n\n₦{amount:,.2f} sent to {account_name}."
                else:
                    return "❌ **Transfer Failed**\n\nSomething went wrong while processing your transfer. Please try again."
            
            # If no recipient_code, but we have account details, create new recipient
            elif account_number and bank_code and account_name:
                logger.info(f"Creating new recipient for transfer: {account_number}")
                
                # Create recipient
                recipient = await self.paystack.create_transfer_recipient(
                    recipient_type="nuban",
                    name=account_name,
                    account_number=account_number,
                    bank_code=bank_code,
                    currency="NGN"
                )
                
                if recipient and recipient.get('status'):
                    new_recipient_code = recipient.get('data', {}).get('recipient_code')
                    
                    # Initiate transfer
                    transfer_data = await self.paystack.initiate_transfer(
                        amount=AmountConverter.to_kobo(amount),
                        recipient_code=new_recipient_code,
                        reason=f"Transfer via TizLion AI to {account_name}"
                    )
                    
                    if transfer_data and transfer_data.get('status'):
                        # Save transfer record to database for tracking
                        transfer_record = {
                            'amount': amount,
                            'recipient': account_name,
                            'account_number': account_number,
                            'bank_code': bank_code,
                            'bank_name': bank_name,
                            'reference': transfer_data.get('reference', f"NEW_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"),
                            'status': transfer_data.get('status', 'unknown'),
                            'reason': f"Transfer via TizLion AI to {account_name}",
                            'timestamp': datetime.utcnow().isoformat(),
                            'paystack_response': transfer_data
                        }
                        
                        await self.memory.save_transfer(user_id, transfer_record)
                        
                        # Auto-save recipient for future transfers
                        try:
                            recipient_data = {
                                'account_name': account_name,
                                'account_number': account_number,
                                'bank_code': bank_code,
                                'bank_name': bank_name,
                                'recipient_code': new_recipient_code
                            }
                            
                            save_result = await self.memory.save_recipient(user_id, recipient_data)
                            if save_result:
                                logger.info(f"✅ Auto-saved new recipient {account_name} for user {user_id}")
                                
                        except Exception as save_error:
                            logger.error(f"Auto-save recipient failed: {save_error}")
                            # Don't fail the transfer response if recipient save fails
                        
                        asyncio.create_task(
                            self._generate_and_send_receipt(user_id, transfer_record, send_follow_up_callback, send_receipt_callback)
                        )
                        return f"✅ **Transfer Successful**\n\n₦{amount:,.2f} sent to {account_name}."
                return "❌ **Transfer Failed**\n\nCouldn't create recipient or process transfer. Please try again."
            else:
                return "Transfer information is incomplete. Please try again."
        except Exception as e:
            logger.error(f"Beneficiary transfer confirmation failed: {e}")
            return "❌ **Transfer Failed**\n\nSomething went wrong while processing your transfer. Please try again."
    
    async def _process_direct_transfer_confirmation(self, user_id: str, state: Dict, send_follow_up_callback, send_receipt_callback=None) -> str:
        """Process confirmed direct transfer."""
        try:
            amount = state.get('amount')
            account_number = state.get('account_number')
            bank_code = state.get('bank_code')
            bank_name = state.get('bank_name')  # Added missing bank_name
            account_name = state.get('account_name')
            
            # Clear conversation state
            await self.memory.clear_conversation_state(user_id)
            
            if not all([amount, account_number, bank_code]):
                return "Transfer information is incomplete. Please try again."
            
            # Process the actual transfer directly (don't route back to confirmation)
            try:
                # Create recipient if needed
                recipient_code = await self._get_or_create_recipient(
                    account_number, bank_code, account_name
                )
                
                if not recipient_code:
                    return "❌ **Transfer Failed**\n\nCouldn't create recipient. Please try again."
                
                # Initiate transfer via Paystack (with proper logging and reference)
                amount_kobo = AmountConverter.to_kobo(amount)
                transfer_reference = f"WA_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{user_id[-4:]}"
                
                logger.info(f"Initiating Paystack transfer: {AmountConverter.format_ngn(amount)} ({amount_kobo} kobo) to {recipient_code}")
                
                transfer_data = await self.paystack.initiate_transfer(
                    amount=amount_kobo,
                    recipient_code=recipient_code,
                    reason=f"Transfer via TizLion AI to {account_name}",
                    reference=transfer_reference
                )
                
                logger.info(f"Paystack transfer response: {transfer_data}")
                
                # Save transfer record to database for tracking
                transfer_record = {
                    'amount': amount,
                    'recipient': account_name,
                    'account_number': account_number,
                    'bank_code': bank_code,
                    'bank_name': bank_name,
                    'reference': transfer_reference,
                    'status': transfer_data.get('status', 'unknown') if transfer_data else 'failed',
                    'reason': f"Transfer via TizLion AI to {account_name}",
                    'timestamp': datetime.utcnow().isoformat(),
                    'paystack_response': transfer_data
                }
                
                await self.memory.save_transfer(user_id, transfer_record)
                
                if transfer_data and transfer_data.get('status'):
                    # Auto-save recipient for future transfers
                    try:
                        recipient_data = {
                            'account_name': account_name,
                            'account_number': account_number,
                            'bank_code': bank_code,
                            'bank_name': bank_name,
                            'recipient_code': recipient_code
                        }
                        
                        save_result = await self.memory.save_recipient(user_id, recipient_data)
                        if save_result:
                            logger.info(f"✅ Auto-saved recipient {account_name} for user {user_id}")
                            
                    except Exception as save_error:
                        logger.error(f"Auto-save recipient failed: {save_error}")
                    
                    # Generate and send receipt
                        asyncio.create_task(
                            self._generate_and_send_receipt(user_id, transfer_record, send_follow_up_callback, send_receipt_callback)
                        )
                    
                    # Return simple success message (receipt will be sent separately)
                    return f"✅ **Transfer Successful**\n\n₦{amount:,.2f} sent to {account_name}."
                
                return "❌ **Transfer Failed**\n\nSomething went wrong while processing your transfer. Please try again."
                    
            except Exception as transfer_error:
                logger.error(f"Direct transfer processing failed: {transfer_error}")
                
                # Provide specific error messages based on error type
                error_str = str(transfer_error).lower()
                if "network" in error_str or "timeout" in error_str:
                    return "❌ **Network Error**\n\nThere's a network issue. Please check your connection and try again."
                elif "insufficient" in error_str:
                    return "❌ **Insufficient Balance**\n\nYou don't have enough money for this transfer."
                elif "recipient" in error_str or "bank" in error_str:
                    return "❌ **Account Error**\n\nThere's an issue with the recipient's account details. Please verify and try again."
                elif "api" in error_str or "service" in error_str:
                    return "❌ **Service Temporarily Unavailable**\n\nOur payment service is having issues. Please try again in a few minutes."
                else:
                    return "❌ **Transfer Failed**\n\nSomething went wrong while processing your transfer. Please try again or contact support if the issue persists."
            
        except Exception as e:
            logger.error(f"Direct transfer confirmation failed: {e}")
            return await self._handle_error_response(user_id, message, str(e))
    
    async def _get_or_create_recipient(self, account_number: str, bank_code: str, account_name: str) -> Optional[str]:
        """Get or create transfer recipient."""
        try:
            logger.info(f"Creating Paystack recipient: {account_name} ({account_number} at bank {bank_code})")
            
            # Create recipient via Paystack
            recipient = await self.paystack.create_transfer_recipient(
                recipient_type="nuban",
                name=account_name,
                account_number=account_number,
                bank_code=bank_code,
                currency="NGN"
            )
            
            logger.info(f"Paystack recipient creation response: {recipient}")
            
            if recipient:
                # Try different possible response structures
                recipient_code = (
                    recipient.get('recipient_code') or
                    recipient.get('data', {}).get('recipient_code') or 
                    recipient.get('recipientCode')
                )
                
                if recipient_code:
                    logger.info(f"✅ Created recipient with code: {recipient_code}")
                    return recipient_code
                else:
                    logger.error(f"No recipient_code found in response: {recipient}")
                    return None
            else:
                logger.error(f"Empty response from Paystack recipient creation")
                return None
            
        except Exception as e:
            logger.error(f"Recipient creation failed: {e}")
            return None

    async def _handle_account_bank_amount_transfer(self, user_id: str, message: str, entities: Dict, send_follow_up_callback=None, send_receipt_callback=None) -> str:
        """Handle account + bank + amount transfer requests with account resolution."""
        try:
            account_number = entities.get('account_number')
            bank_code = entities.get('bank_code')
            bank_name = entities.get('bank_name')
            amount = entities.get('amount')
            
            if not account_number or not bank_code:
                return "I need the account number and bank to process this transfer. Please try again."
            
            # Check if amount is provided, if not ask for it
            if not amount:
                # Set state to ask for amount after account resolution
                await self.memory.set_conversation_state(user_id, {
                    'type': 'account_resolved_pending_amount',
                    'account_number': account_number,
                    'bank_code': bank_code,
                    'bank_name': bank_name,
                    'timestamp': datetime.utcnow().isoformat()
                })
                
                human_responses = [
                    f"I can send money to that {bank_name} account ({account_number}). How much should I send?",
                    f"Got the account details! What amount do you want to send to {account_number} ({bank_name})?",
                    f"Perfect! How much money should I transfer to that {bank_name} account?",
                    f"Ready to send money to {account_number} ({bank_name}). What's the amount?"
                ]
                return random.choice(human_responses)
            
            # Check balance first
            balance_check = await self.balance_handler.check_sufficient_balance(amount)
            if not balance_check['sufficient']:
                return f"❌ **Insufficient Balance**\n\nYou're trying to send ₦{amount:,.2f} but your balance is {balance_check['formatted_balance']}."
            
            # Resolve account to get real account name
            try:
                account_info = await self.paystack.resolve_account(account_number, bank_code)
                account_name = account_info.get('account_name', 'Unknown Account')
                
                # Set confirmation state
                await self.memory.set_conversation_state(user_id, {
                    'type': 'account_bank_amount_transfer_pending_confirmation',
                    'amount': amount,
                    'account_number': account_number,
                    'bank_code': bank_code,
                    'bank_name': bank_name,
                    'account_name': account_name,
                    'timestamp': datetime.utcnow().isoformat()
                })
                
                formatted_amount = f"₦{amount:,.2f}"
                
                # Human-like confirmation responses
                confirmation_responses = [
                    f"💰 **Transfer Confirmation**\n\nSend {formatted_amount} to **{account_name}** at {bank_name}?",
                    f"💰 **Transfer Confirmation**\n\nSend {formatted_amount} to **{account_name}** ({bank_name} account {account_number})?",
                    f"💰 **Transfer Confirmation**\n\nReady to transfer {formatted_amount} to **{account_name}** at {bank_name}?",
                    f"💰 **Transfer Confirmation**\n\nSend {formatted_amount} to **{account_name}** ({bank_name})?"
                ]
                
                return random.choice(confirmation_responses)
                
            except Exception as e:
                logger.error(f"Account resolution failed: {e}")
                # Fallback - ask user to verify account details
                return f"I couldn't verify that {bank_name} account {account_number}. Please double-check the account number and bank name, then try again."
                
        except Exception as e:
            logger.error(f"Account bank amount transfer handling failed: {e}")
            return await self._handle_error_response(user_id, message, str(e))
    
    async def _handle_account_bank_amount_confirmation(self, user_id: str, message: str, state: Dict, send_follow_up_callback, send_receipt_callback=None) -> str:
        """Handle confirmation for account + bank + amount transfers."""
        try:
            amount = state.get('amount')
            account_number = state.get('account_number')
            bank_code = state.get('bank_code')
            bank_name = state.get('bank_name')  # Added this missing field
            account_name = state.get('account_name')
            
            # Clear conversation state
            await self.memory.clear_conversation_state(user_id)
            
            if not all([amount, account_number, bank_code]):
                return "Transfer information is incomplete. Please try again."
            
            # Process the actual transfer directly (don't route back to confirmation)
            try:
                # Create recipient if needed
                recipient_code = await self._get_or_create_recipient(
                    account_number, bank_code, account_name
                )
                
                if not recipient_code:
                    return "❌ **Transfer Failed**\n\nCouldn't create recipient. Please try again."
                
                # Initiate transfer via Paystack (with proper logging and reference)
                amount_kobo = AmountConverter.to_kobo(amount)
                transfer_reference = f"WA_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{user_id[-4:]}"
                
                logger.info(f"Initiating Paystack transfer: {AmountConverter.format_ngn(amount)} ({amount_kobo} kobo) to {recipient_code}")
                
                transfer_data = await self.paystack.initiate_transfer(
                    amount=amount_kobo,
                    recipient_code=recipient_code,
                    reason=f"Transfer via TizLion AI to {account_name}",
                    reference=transfer_reference
                )
                
                logger.info(f"Paystack transfer response: {transfer_data}")
                
                # Save transfer record to database for tracking
                transfer_record = {
                    'amount': amount,
                    'recipient': account_name,
                    'account_number': account_number,
                    'bank_code': bank_code,
                    'bank_name': bank_name,
                    'reference': transfer_reference,
                    'status': transfer_data.get('status', 'unknown') if transfer_data else 'failed',
                    'reason': f"Transfer via TizLion AI to {account_name}",
                    'timestamp': datetime.utcnow().isoformat(),
                    'paystack_response': transfer_data
                }
                
                await self.memory.save_transfer(user_id, transfer_record)
                
                if transfer_data and transfer_data.get('status'):
                    # Auto-save recipient for future transfers
                    try:
                        recipient_data = {
                            'account_name': account_name,
                            'account_number': account_number,
                            'bank_code': bank_code,
                            'bank_name': bank_name,
                            'recipient_code': recipient_code
                        }
                        
                        save_result = await self.memory.save_recipient(user_id, recipient_data)
                        if save_result:
                            logger.info(f"✅ Auto-saved recipient {account_name} for user {user_id}")
                            
                    except Exception as save_error:
                        logger.error(f"Auto-save recipient failed: {save_error}")
                    
                    # Generate and send receipt
                        asyncio.create_task(
                            self._generate_and_send_receipt(user_id, transfer_record, send_follow_up_callback, send_receipt_callback)
                        )
                    
                    # Return simple success message (receipt will be sent separately)
                    return f"✅ **Transfer Successful**\n\n₦{amount:,.2f} sent to {account_name}."
                else:
                    return "❌ **Transfer Failed**\n\nSomething went wrong while processing your transfer. Please try again."
                    
            except Exception as transfer_error:
                logger.error(f"Account bank amount transfer processing failed: {transfer_error}")
                return "❌ **Transfer Failed**\n\nCouldn't process the transfer. Please try again."
            
        except Exception as e:
            logger.error(f"Account bank amount confirmation failed: {e}")
            return await self._handle_error_response(user_id, message, str(e))
    
    async def _handle_banks_request(self, user_id: str, message: str = "list banks") -> str:
        """Handle banks listing request."""
        try:
            banks = await self.paystack.list_banks()
            
            if not banks:
                return "Sorry, I couldn't fetch the bank list right now. Please try again later."
            
            # Format bank list
            formatted_banks = "🏦 **Available Banks:**\n\n"
            for bank in banks[:20]:  # Limit to first 20 banks
                formatted_banks += f"• {bank.get('name', 'Unknown')}\n"
            
            if len(banks) > 20:
                formatted_banks += f"\n... and {len(banks) - 20} more banks."
            
            return formatted_banks
            
        except Exception as e:
            logger.error(f"Banks request failed: {e}")
            return await self._handle_error_response(user_id, message, str(e))
    
    async def _handle_fallback_response(self, user_id: str, message: str) -> str:
        """Handle fallback responses using LLM instead of static templates."""
        # Use LLM-based fallback response
        return await self.response_handler.format_fallback_response(message)
    
    async def _handle_error_response(self, user_id: str, message: str, error_details: str) -> str:
        """Generate intelligent error responses using LLM."""
        try:
            if self.ai_enabled and self.ai_client:
                system_prompt = """You are TizBot, a helpful Nigerian banking assistant. Something went wrong, but you should respond naturally and helpfully without being overly technical.

Guidelines:
- Acknowledge that something went wrong without going into technical details
- Offer to help the user try again or with something else
- Be encouraging and supportive
- Use Nigerian expressions naturally when appropriate
- Keep it short and friendly
- Don't mention specific error codes or technical jargon

Examples:
- "Oops! Something went wrong there. Let me try to help you again - what did you want to do?"
- "Sorry about that! There was a small hiccup. Want to try again or need help with something else?"
- "My bad! Something didn't work right. No worries though - I'm here to help. What can I do for you?"
"""
                
                user_prompt = f"Generate a friendly error response. The user said: '{message}' and something went wrong."
                
                completion = await self.ai_client.chat.completions.create(
                    model=self.ai_model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    max_tokens=100,
                    temperature=0.8
                )
                
                ai_response = completion.choices[0].message.content
                if ai_response and ai_response.strip():
                    return ai_response.strip()
            
            # Fallback to enhanced static responses
            error_responses = [
                "Oops! Something went wrong there. Let me try to help you again - what did you want to do?",
                "Sorry about that! There was a small hiccup. Want to try again or need help with something else?",
                "My bad! Something didn't work right. No worries though - I'm here to help. What can I do for you?",
                "Looks like we hit a snag! Don't worry, I'm still here to help. What would you like to try?"
            ]
            return random.choice(error_responses)
            
        except Exception as e:
            logger.error(f"Error response generation failed: {e}")
            return "Something went wrong, but I'm still here to help! What would you like to do?"
    
    # Utility methods for backward compatibility
    async def get_balance(self) -> str:
        """Get current balance (utility method)."""
        return await self.balance_handler.get_current_balance_text()
    
    async def clear_conversation_state(self, user_id: str):
        """Clear conversation state (utility method)."""
        await self.memory.clear_conversation_state(user_id)
    
    async def _handle_greeting_during_transaction(self, user_id: str, message: str, state: Dict, intent: str) -> str:
        """Handle greetings and casual messages when user is in the middle of a transaction."""
        
        message_lower = message.lower().strip()
        state_type = state.get('type')
        
        # Acknowledge the greeting and gently remind about the pending transaction
        if intent == "greeting":
            if message_lower in ["hi", "hello", "hey", "yo", "yoo"]:
                greeting_responses = [
                    "Hey there! 👋",
                    "Hi! 😊",
                    "Hello! 👋",
                    "Hey! 😊"
                ]
                greeting_response = random.choice(greeting_responses)
            else:
                greeting_response = "Hi there! 👋"
        elif intent == "thanks":
            greeting_response = "You're welcome! 😊"
        else:
            greeting_response = "Hi! 😊"
        
        # Provide contextual reminder based on the transaction state
        if state_type == 'account_resolution_pending_amount':
            account_name = state.get('account_name', 'the account')
            bank_name = state.get('bank_name', 'bank')
            
            reminders = [
                f" I was helping you send money to **{account_name}** at {bank_name}. How much would you like to send?",
                f" We were setting up a transfer to **{account_name}** at {bank_name}. What amount should I send?",
                f" You wanted to send money to **{account_name}** at {bank_name}. How much?",
                f" Still need the amount for that transfer to **{account_name}** at {bank_name}. How much would you like to send?"
            ]
            
            reminder = random.choice(reminders)
            return greeting_response + reminder
            
        elif state_type == 'beneficiary_transfer_pending_amount':
            account_name = state.get('account_name', 'your contact')
            
            reminders = [
                f" I was helping you send money to **{account_name}**. How much would you like to send?",
                f" We were setting up a transfer to **{account_name}**. What amount?",
                f" Still need the amount for that transfer to **{account_name}**. How much?"
            ]
            
            reminder = random.choice(reminders)
            return greeting_response + reminder
            
        elif state_type in ['direct_transfer_pending_confirmation', 'account_bank_amount_transfer_pending_confirmation', 'beneficiary_transfer_pending_confirmation']:
            # User is at confirmation stage
            amount = state.get('amount', 0)
            account_name = state.get('account_name', 'the recipient')
            
            reminders = [
                f" I was waiting for you to confirm sending ₦{amount:,.2f} to **{account_name}**. Should I proceed? (yes/no)",
                f" We're ready to send ₦{amount:,.2f} to **{account_name}**. Confirm with 'yes' or cancel with 'no'.",
                f" Still waiting for confirmation on that ₦{amount:,.2f} transfer to **{account_name}**. Yes or no?"
            ]
            
            reminder = random.choice(reminders)
            return greeting_response + reminder
        
        else:
            # Generic fallback
            return greeting_response + " I was helping you with something. What would you like to do?"

    async def _generate_and_send_receipt(
        self,
        user_id: str,
        transfer_record: Dict,
        send_follow_up_callback=None,
        send_receipt_callback=None,
    ) -> bool:
        """Generate and send receipt image. Uses send_receipt_callback if provided (e.g. Telegram), else WhatsApp."""
        try:
            receipt_data = {
                "amount": transfer_record.get("amount", 0),
                "recipient_name": transfer_record.get("recipient", "Unknown"),
                "account_number": transfer_record.get("account_number", "N/A"),
                "bank_name": transfer_record.get("bank_name", "Unknown Bank"),
                "reference": transfer_record.get("reference", "N/A"),
                "status": "success",
                "timestamp": transfer_record.get("timestamp", datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")),
            }
            receipt_path = generate_receipt_image(receipt_data)
            if not receipt_path:
                logger.warning("Receipt generation failed")
                return False

            await self.memory.save_receipt(user_id=user_id, reference=receipt_data["reference"], receipt_path=receipt_path)
            caption = "✅ Transfer successful! Here's your receipt."

            if send_receipt_callback:
                try:
                    with open(receipt_path, "rb") as f:
                        image_bytes = f.read()
                    await send_receipt_callback(user_id, image_bytes, caption)
                    logger.info(f"Receipt image sent to {user_id} via channel callback")
                    return True
                except Exception as send_error:
                    logger.error(f"Failed to send receipt via callback: {send_error}")
                    return True
            if send_follow_up_callback:
                try:
                    from app.services.whatsapp_service import WhatsAppService
                    whatsapp_service = WhatsAppService()
                    asyncio.create_task(
                        whatsapp_service.send_receipt_image(to=user_id, image_path=receipt_path, caption=caption)
                    )
                    logger.info(f"Receipt image sent to {user_id}")
                    return True
                except Exception as send_error:
                    logger.error(f"Failed to send receipt image: {send_error}")
                    return True
            return True
        except Exception as e:
            logger.error(f"Receipt generation and sending failed: {e}")
            return False

    # Health check method
    def health_check(self) -> Dict[str, Any]:
        """Return health status of the agent and its components."""
        return {
            "agent_status": "healthy",
            "ai_enabled": self.ai_enabled,
            "ai_model": self.ai_model,
            "handlers": {
                "message_processor": "initialized",
                "balance_handler": "initialized",
                "transfer_handler": "initialized",
                "history_handler": "initialized",
                "beneficiary_handler": "initialized",
                "ai_handler": "initialized"
            },
            "services": {
                "paystack": "connected" if self.paystack else "disconnected",
                "memory": "connected" if self.memory else "disconnected",
                "recipient_manager": "connected" if self.recipient_manager else "disconnected"
            }
        } 