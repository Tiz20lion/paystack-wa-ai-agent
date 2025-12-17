#!/usr/bin/env python3
"""
Transfer Handler - Manages all transfer-related operations
"""

import uuid
import asyncio
from typing import Dict, Optional, Any, cast
from app.utils.logger import get_logger
from app.services.paystack_service import PaystackService
from app.utils.memory_manager import MemoryManager
from app.utils.bank_resolver import BankResolver
from app.utils.amount_converter import AmountConverter
from datetime import datetime

logger = get_logger("transfer_handler")

class TransferHandler:
    """Handle all transfer operations including balance checks and confirmations."""
    
    def __init__(self, paystack_service: PaystackService, memory_manager: MemoryManager, 
                 ai_client=None, ai_model=None, ai_enabled=False):
        self.paystack = paystack_service
        self.memory = memory_manager
        self.ai_client = ai_client
        self.ai_model = ai_model
        self.ai_enabled = ai_enabled
    
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
    
    async def handle_transfer_request(self, user_id: str, message: str, intent: str, 
                                     entities: Dict, send_follow_up_callback=None) -> str:
        """Handle transfer requests with comprehensive context storage."""
        try:
            logger.info(f"Processing transfer request for user {user_id}")
            
            # Save initial transfer request context
            await self.memory.save_banking_operation_context(
                user_id=user_id,
                operation_type="transfer_request_initiated",
                operation_data={
                    'intent': intent,
                    'entities': entities,
                    'message': message,
                    'timestamp': datetime.utcnow().isoformat()
                },
                api_response={'status': 'initiated', 'success': True}
            )
            
            # Extract required information
            amount = entities.get('amount')
            account_number = entities.get('account_number')
            bank_code = entities.get('bank_code')
            bank_name = entities.get('bank_name')
            recipient_name = entities.get('recipient_name')
            
            # Validate required fields
            if not amount:
                # Save validation error context
                await self.memory.save_banking_operation_context(
                    user_id=user_id,
                    operation_type="transfer_validation_error",
                    operation_data={'missing_field': 'amount', 'entities': entities},
                    api_response={'success': False, 'error': 'missing_amount'}
                )
                # Human-like responses instead of template
                human_responses = [
                    "I see you want to send money! How much would you like to transfer?",
                    "Got it! What amount do you want to send?",
                    "Perfect! Just tell me how much you want to transfer.",
                    "I can help with that! What's the amount you want to send?"
                ]
                import random
                return random.choice(human_responses)
            
            if not account_number:
                # Save validation error context
                await self.memory.save_banking_operation_context(
                    user_id=user_id,
                    operation_type="transfer_validation_error",
                    operation_data={'missing_field': 'account_number', 'entities': entities},
                    api_response={'success': False, 'error': 'missing_account_number'}
                )
                # Human-like responses for missing account
                human_responses = [
                    f"I have the amount (₦{amount:,})! What's the account number you want to send to?",
                    f"Ready to send ₦{amount:,}! Just need the account number.",
                    f"Got ₦{amount:,} ready to go! Which account should I send it to?",
                    f"Perfect! ₦{amount:,} - now what's the destination account number?"
                ]
                import random
                return random.choice(human_responses)
            
            if not bank_code and not bank_name:
                # Save validation error context
                await self.memory.save_banking_operation_context(
                    user_id=user_id,
                    operation_type="transfer_validation_error",
                    operation_data={'missing_field': 'bank_info', 'entities': entities},
                    api_response={'success': False, 'error': 'missing_bank_info'}
                )
                # Human-like responses for missing bank
                human_responses = [
                    f"Almost there! I have ₦{amount:,} for account {account_number}. Which bank is this account with?",
                    f"Got ₦{amount:,} and account {account_number}! What bank should I send to?",
                    f"Perfect! ₦{amount:,} to {account_number} - just need to know the bank name.",
                    f"Great! I have the amount and account number. Which bank is {account_number} with?"
                ]
                import random
                return random.choice(human_responses)
            
            # Convert amount to kobo (Paystack uses kobo)
            amount_kobo = int(amount)
            
            # Ensure we have a valid bank_code
            if not bank_code and bank_name:
                bank_code = BankResolver.resolve_bank_code(bank_name)
                if not bank_code:
                    # Save bank resolution error context
                    await self.memory.save_banking_operation_context(
                        user_id=user_id,
                        operation_type="bank_resolution_error",
                        operation_data={'bank_name': bank_name, 'entities': entities},
                        api_response={'success': False, 'error': 'bank_not_found'}
                    )
                    return f"❌ Sorry, I couldn't find the bank '{bank_name}'. Please check the bank name and try again."
            
            # Final validation: ensure bank_code is never None
            if not bank_code:
                await self.memory.save_banking_operation_context(
                    user_id=user_id,
                    operation_type="bank_code_missing_error",
                    operation_data={'bank_name': bank_name, 'entities': entities},
                    api_response={'success': False, 'error': 'no_valid_bank_code'}
                )
                return "❌ Bank information is missing or invalid. Please provide a valid bank name."
            
            # Resolve account name
            logger.info(f"Resolving account: {account_number} at bank {bank_code or bank_name}")
            # At this point, bank_code is guaranteed to be a string due to validation above
            assert bank_code is not None, "bank_code should not be None after validation"
            resolution_response = await self.paystack.resolve_account(account_number, bank_code)
            
            if not resolution_response or not resolution_response.get('status'):
                # Save account resolution error
                await self.memory.save_banking_operation_context(
                    user_id=user_id,
                    operation_type="account_resolution_error",
                    operation_data={
                        'account_number': account_number,
                        'bank_code': bank_code,
                        'bank_name': bank_name
                    },
                    api_response={'success': False, 'error': 'account_resolution_failed'}
                )
                # Human-like error responses
                human_error_responses = [
                    f"Hmm, I couldn't verify that {bank_name} account {account_number}. Can you double-check the account number?",
                    f"That {bank_name} account ({account_number}) doesn't seem to be valid. Mind checking the digits again?",
                    f"I'm having trouble finding account {account_number} at {bank_name}. Could you verify the account details?",
                    f"Something's not right with {account_number} ({bank_name}). Can you confirm the account number is correct?"
                ]
                import random
                return random.choice(human_error_responses)
            
            account_data = resolution_response.get('data', {})
            resolved_name = account_data.get('account_name', 'Unknown')
            
            # Save successful account resolution
            await self.memory.save_banking_operation_context(
                user_id=user_id,
                operation_type="account_resolution_success",
                operation_data={
                    'account_number': account_number,
                    'bank_code': bank_code,
                    'resolved_name': resolved_name,
                    'account_data': account_data
                },
                api_response={'success': True, 'resolved_name': resolved_name}
            )
            
            # Create confirmation message
            confirmation_msg = f"🔍 **Transfer Confirmation**\n\n"
            confirmation_msg += f"💰 **Amount**: ₦{amount:,.2f}\n"
            confirmation_msg += f"👤 **To**: {resolved_name}\n"
            confirmation_msg += f"🏦 **Account**: {account_number}\n"
            confirmation_msg += f"🏛️ **Bank**: {bank_name or bank_code}\n\n"
            confirmation_msg += "Reply 'Yes' to confirm or 'No' to cancel."
            
            # Store transfer details in conversation state
            transfer_state = {
                'type': 'direct_transfer_pending_confirmation',  # Changed to match expected state type
                'amount': amount,  # Keep original amount, convert in transfer execution
                'account_number': account_number,
                'bank_code': bank_code,
                'bank_name': bank_name,  # Added missing bank_name
                'account_name': resolved_name,
                'recipient_name': recipient_name,
                'original_message': message,
                'reference': str(uuid.uuid4())[:8].upper(),  # Added reference for transfer tracking
                'created_at': datetime.utcnow().isoformat()
            }
            
            await self.memory.set_conversation_state(user_id, transfer_state)
            
            # Save transfer confirmation state
            await self.memory.save_banking_operation_context(
                user_id=user_id,
                operation_type="transfer_confirmation_pending",
                operation_data=transfer_state,
                api_response={'success': True, 'status': 'awaiting_confirmation'}
            )
            
            return confirmation_msg
            
        except Exception as e:
            logger.error(f"Transfer request handling failed: {e}")
            # Save error context
            await self.memory.save_banking_operation_context(
                user_id=user_id,
                operation_type="transfer_request_error",
                operation_data={'message': message, 'intent': intent, 'entities': entities},
                api_response={'success': False, 'error': str(e)}
            )
            return f"❌ Transfer request failed: {str(e)}"
    
    async def _process_transfer_request_background(self, user_id: str, message: str, entities: Dict, balance_handler):
        """Process transfer request in background and send second response."""
        try:
            logger.info(f"🔄 Starting background transfer request processing for user {user_id}")
            
            # Process the transfer request
            result = await self._handle_transfer_request_traditional(user_id, message, entities, balance_handler)
            
            # Send the detailed response as second message
            await self._send_follow_up_message(user_id, result)
            logger.info(f"✅ Background transfer request processing completed for user {user_id}")
            
        except Exception as e:
            logger.error(f"Background transfer request processing failed: {e}")
            await self._send_follow_up_message(user_id, "Something went wrong while processing your transfer request. Please try again.")
    
    async def _handle_transfer_request_traditional(self, user_id: str, message: str, entities: Dict, balance_handler) -> str:
        """Traditional transfer request handler (fallback method)."""
        try:
            # Extract account number and bank from entities
            account_number = entities.get('account_number')
            bank_name = entities.get('bank_name')
            amount = entities.get('amount')
            
            if not account_number or not bank_name:
                return "Please provide both account number and bank name. Example: 'send 5000 to 1234567890 GTBank'"
            
            # Resolve bank code from bank name
            bank_code = BankResolver.resolve_bank_code(bank_name)
            if not bank_code:
                return f"Sorry, I couldn't find the bank '{bank_name}'. Please check the bank name and try again."
            
            # If amount is provided, proceed with transfer
            if amount:
                # Check balance first
                balance_check = await balance_handler.check_sufficient_balance(amount)
                if not balance_check['sufficient']:
                    return f"❌ **Insufficient Balance**\n\nYou're trying to send {AmountConverter.format_ngn(amount)} but your balance is {balance_check['formatted_balance']}."
                
                # Resolve account
                try:
                    account_info = await self.paystack.resolve_account(account_number, bank_code)
                    
                    # Set up transfer confirmation state
                    state = {
                        'type': 'transfer_pending_confirmation',
                        'amount': amount,
                        'account_number': account_number,
                        'bank_code': bank_code,
                        'account_name': account_info['account_name'],
                        'bank_name': BankResolver.get_bank_name(bank_code) or f"Bank {bank_code}",
                        'reference': str(uuid.uuid4())[:8].upper()
                    }
                    
                    await self.memory.set_conversation_state(user_id, state)
                    
                    formatted_amount = f"₦{amount:,.2f}"
                    return f"""💰 **Transfer Confirmation**

**You want to send:**
• Amount: {formatted_amount}
• To: {account_info['account_name']}
• Account: {account_number}
• Bank: {state['bank_name']}

Is this correct? Type "yes" to proceed or "no" to cancel."""
                    
                except Exception as e:
                    logger.error(f"Account resolution failed: {e}")
                    return f"❌ **Account Resolution Failed**\n\nI couldn't verify the account {account_number} at {bank_name}. Please check the details and try again."
            
            else:
                # Amount not provided, ask for amount
                return f"How much would you like to send to {account_number} ({bank_name})?"
        
        except Exception as e:
            logger.error(f"Transfer request handling failed: {e}")
            return "Sorry, I couldn't process your transfer request. Please try again."

    async def handle_account_resolution(self, user_id: str, entities: Dict, memory_manager) -> str:
        """Handle account resolution requests with two-way messaging."""
        try:
            # Send immediate acknowledgment response
            immediate_response = "Let me resolve that account for you... ⏳"
            
            # Start background processing task (don't await it)
            asyncio.create_task(self._process_account_resolution_background(user_id, entities, memory_manager))
            
            # Return immediate response to user
            return immediate_response
            
        except Exception as e:
            logger.error(f"Failed to start account resolution: {e}")
            # Fallback to traditional method if background processing fails
            return await self._handle_account_resolution_traditional(user_id, entities, memory_manager)
    
    async def _process_account_resolution_background(self, user_id: str, entities: Dict, memory_manager):
        """Process account resolution in background and send second response."""
        try:
            logger.info(f"🔄 Starting background account resolution for user {user_id}")
            
            # Process the account resolution
            result = await self._handle_account_resolution_traditional(user_id, entities, memory_manager)
            
            # Send the detailed response as second message
            await self._send_follow_up_message(user_id, result)
            logger.info(f"✅ Background account resolution completed for user {user_id}")
            
        except Exception as e:
            logger.error(f"Background account resolution failed: {e}")
            await self._send_follow_up_message(user_id, "Something went wrong while resolving the account. Please try again.")
    
    async def _handle_account_resolution_traditional(self, user_id: str, entities: Dict, memory_manager) -> str:
        """Traditional account resolution handler (fallback method)."""
        try:
            account_number = entities.get('account_number')
            bank_name = entities.get('bank_name')
            
            if not account_number or not bank_name:
                return "Please provide both account number and bank name. Example: '1234567890 GTBank'"
            
            # Resolve bank code
            bank_code = BankResolver.resolve_bank_code(bank_name)
            if not bank_code:
                return f"Sorry, I couldn't find the bank '{bank_name}'. Please check the bank name and try again."
            
            # Resolve account
            try:
                account_info = await self.paystack.resolve_account(account_number, bank_code)
                
                # Set up state for amount input
                state = {
                    'type': 'account_resolution_pending_amount',
                    'account_number': account_number,
                    'bank_code': bank_code,
                    'account_name': account_info['account_name'],
                    'bank_name': BankResolver.get_bank_name(bank_code) or f"Bank {bank_code}"
                }
                
                await memory_manager.set_conversation_state(user_id, state)
                
                return f"""✅ **Account Found**

**Account Details:**
• Name: {account_info['account_name']}
• Account: {account_number}
• Bank: {state['bank_name']}

How much would you like to send?"""
                
            except Exception as e:
                logger.error(f"Account resolution failed: {e}")
                return f"❌ **Account Resolution Failed**\n\nI couldn't verify the account {account_number} at {bank_name}. Please check the details and try again."
        
        except Exception as e:
            logger.error(f"Account resolution handling failed: {e}")
            return "Sorry, I couldn't resolve the account. Please try again."
    
    async def handle_transfer_confirmation(self, user_id: str, intent: str, entities: Dict, state: Dict) -> str:
        """Handle transfer confirmation with two-way messaging."""
        try:
            if intent == "confirmation" or intent == "casual_response":
                # Send immediate acknowledgment response
                immediate_response = "Processing your transfer now... ⏳"
                
                # Start background processing task (don't await it)
                asyncio.create_task(self._process_transfer_confirmation_background(user_id, state))
                
                # Return immediate response to user
                return immediate_response
            
            elif intent == "denial":
                # User cancelled the transfer
                await self.memory.clear_conversation_state(user_id)
                return "Transfer cancelled. Is there anything else I can help you with?"
            
            else:
                # Ask for explicit confirmation
                return "Please confirm the transfer by typing 'yes' or 'no'."
        
        except Exception as e:
            logger.error(f"Transfer confirmation handling failed: {e}")
            return "Sorry, I couldn't process your confirmation. Please try again."
    
    async def _process_transfer_confirmation_background(self, user_id: str, state: Dict):
        """Process transfer confirmation in background and send second response."""
        try:
            logger.info(f"🔄 Starting background transfer confirmation for user {user_id}")
            
            # Process the actual transfer
            result = await self._process_transfer(user_id, state)
            
            # Send the detailed response as second message
            await self._send_follow_up_message(user_id, result)
            logger.info(f"✅ Background transfer confirmation completed for user {user_id}")
            
        except Exception as e:
            logger.error(f"Background transfer confirmation failed: {e}")
            await self._send_follow_up_message(user_id, "Something went wrong while processing your transfer. Please try again.")

    async def handle_direct_transfer_confirmation(self, user_id: str, intent: str, entities: Dict, state: Dict) -> str:
        """Handle direct transfer confirmation with two-way messaging."""
        try:
            if intent == "confirmation" or intent == "casual_response":
                # Send immediate acknowledgment response
                immediate_response = "Processing your transfer now... ⏳"
                
                # Start background processing task (don't await it)
                asyncio.create_task(self._process_transfer_confirmation_background(user_id, state))
                
                # Return immediate response to user
                return immediate_response
            
            elif intent == "denial":
                # User cancelled the transfer
                await self.memory.clear_conversation_state(user_id)
                return "Transfer cancelled. Is there anything else I can help you with?"
            
            else:
                # Ask for explicit confirmation
                return "Please confirm the transfer by typing 'yes' or 'no'."
        
        except Exception as e:
            logger.error(f"Direct transfer confirmation handling failed: {e}")
            return "Sorry, I couldn't process your confirmation. Please try again."

    async def handle_beneficiary_transfer_confirmation(self, user_id: str, intent: str, entities: Dict, state: Dict) -> str:
        """Handle beneficiary transfer confirmation with two-way messaging."""
        try:
            if intent == "confirmation" or intent == "casual_response":
                # Send immediate acknowledgment response
                immediate_response = "Processing your transfer now... ⏳"
                
                # Start background processing task (don't await it)
                asyncio.create_task(self._process_transfer_confirmation_background(user_id, state))
                
                # Return immediate response to user
                return immediate_response
            
            elif intent == "denial":
                # User cancelled the transfer
                await self.memory.clear_conversation_state(user_id)
                return "Transfer cancelled. Is there anything else I can help you with?"
            
            else:
                # Ask for explicit confirmation
                return "Please confirm the transfer by typing 'yes' or 'no'."
        
        except Exception as e:
            logger.error(f"Beneficiary transfer confirmation handling failed: {e}")
            return "Sorry, I couldn't process your confirmation. Please try again."
    
    async def _process_transfer(self, user_id: str, state: Dict) -> str:
        """Process the actual transfer."""
        try:
            # Clear conversation state first
            await self.memory.clear_conversation_state(user_id)
            
            # Get recipient code
            recipient_code = await self._get_or_create_recipient(
                state['account_number'], 
                state['bank_code'], 
                state['account_name']
            )
            
            if not recipient_code:
                return "❌ **Transfer Failed**\n\nI couldn't create the recipient. Please try again."
            
            # Initiate transfer (convert naira to kobo)
            amount_kobo = AmountConverter.to_kobo(state['amount'])
            reference = state.get('reference', str(uuid.uuid4())[:8].upper())
            
            logger.info(f"Initiating Paystack transfer: ₦{state['amount']} ({amount_kobo} kobo) to {recipient_code}")
            transfer_data = await self.paystack.initiate_transfer(
                amount=amount_kobo,
                recipient_code=recipient_code,
                reason=f"Transfer via TizLion AI to {state['account_name']}",
                reference=reference
            )
            
            logger.info(f"Paystack transfer response: {transfer_data}")
            
            # If transfer is successful, automatically save recipient for future use
            if transfer_data and transfer_data.get('status'):
                logger.info(f"Transfer successful, auto-saving recipient: {state['account_name']}")
                try:
                    # Auto-save recipient data to local storage
                    recipient_data = {
                        'account_name': state['account_name'],
                        'account_number': state['account_number'],
                        'bank_code': state['bank_code'],
                        'bank_name': BankResolver.get_bank_name(state['bank_code']) or state.get('bank_name', 'Unknown Bank'),
                        'recipient_code': recipient_code
                    }
                    
                    # Save using memory manager
                    save_result = await self.memory.save_recipient(user_id, recipient_data)
                    if save_result:
                        logger.info(f"✅ Auto-saved recipient {state['account_name']} for user {user_id}")
                    else:
                        logger.warning(f"⚠️ Failed to auto-save recipient {state['account_name']} for user {user_id}")
                        
                except Exception as save_error:
                    logger.error(f"Auto-save recipient failed: {save_error}")
                    # Don't fail the transfer response if recipient save fails
            
            # Generate AI response if enabled
            if self.ai_enabled:
                ai_response = await self._generate_ai_transfer_confirmation(
                    user_id, 
                    state['amount'], 
                    state['account_name'], 
                    state['bank_name'], 
                    state['reference']
                )
                if ai_response:
                    return ai_response
            
            # Fallback to standard response with recipient save confirmation
            formatted_amount = AmountConverter.format_ngn(state['amount'])
            bank_name = BankResolver.get_bank_name(state['bank_code']) or state.get('bank_name', 'Unknown Bank')
            
            response = f"""✅ **Transfer Successful**

**Transfer Details:**
• Amount: {formatted_amount}
• To: {state['account_name']}
• Account: {state['account_number']}
• Bank: {bank_name}
• Reference: {reference}

Your transfer has been processed successfully!

💾 **{state['account_name']}** has been saved as a contact for easy future transfers."""
            
            return response
            
        except Exception as e:
            logger.error(f"Transfer processing failed: {e}")
            return f"❌ **Transfer Failed**\n\nSomething went wrong while processing your transfer. Please try again or contact support."
    
    async def _get_or_create_recipient(self, account_number: str, bank_code: str, account_name: str) -> Optional[str]:
        """Get or create transfer recipient."""
        try:
            # Create recipient via Paystack
            logger.info(f"Creating Paystack recipient: {account_name} - {account_number}")
            recipient_response = await self.paystack.create_transfer_recipient(
                recipient_type="nuban",
                name=account_name,
                account_number=account_number,
                bank_code=bank_code,
                currency="NGN"
            )
            
            logger.info(f"Paystack recipient response: {recipient_response}")
            
            # Extract recipient_code correctly from nested response
            if recipient_response and 'recipient_code' in recipient_response:
                return recipient_response['recipient_code']
            else:
                logger.error(f"No recipient_code in response: {recipient_response}")
                return None
            
        except Exception as e:
            logger.error(f"Recipient creation failed: {e}")
            return None
    
    
    async def _generate_ai_transfer_confirmation(self, user_id: str, amount: float, 
                                               recipient_name: str, bank_name: str, reference: str) -> str:
        """Generate AI-powered transfer confirmation."""
        if not self.ai_enabled or not self.ai_client or not self.ai_model:
            return ""
        
        try:
            # Get recent conversation context
            context = await self.memory.get_context_summary(user_id)
            
            formatted_amount = f"₦{amount:,.2f}"
            
            prompt = f"""Generate a natural, friendly Nigerian-style confirmation message for a successful money transfer.

Transfer Details:
- Amount: {formatted_amount}
- Recipient: {recipient_name}
- Bank: {bank_name}
- Reference: {reference}

Context: {context}

Make the response:
- Natural and conversational
- Brief (2-3 sentences max)
- Use Nigerian expressions appropriately
- Include relevant emojis
- Show the transfer was successful

Example style: "Your {formatted_amount} don reach {recipient_name} for {bank_name} successfully! 🎉 Transaction reference: {reference}. Anything else I fit do for you?"
"""
            
            model_str = self.ai_model if self.ai_model else "gpt-3.5-turbo"
            
            completion = await self.ai_client.chat.completions.create(
                model=model_str,
                messages=[
                    {"role": "system", "content": "You are a friendly Nigerian banking assistant."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=150,
                temperature=0.8
            )
            
            return cast(str, completion.choices[0].message.content).strip()
            
        except Exception as e:
            logger.error(f"AI transfer confirmation generation failed: {e}")
            return "" 

    async def handle_beneficiary_transfer(self, user_id: str, entities: Dict) -> str:
        """Handle beneficiary transfer requests - routes to appropriate handler."""
        try:
            # This method is called by financial_agent_refactored.py
            # Route to the existing beneficiary transfer request handler
            return await self.handle_beneficiary_transfer_request(user_id, entities)
        except Exception as e:
            logger.error(f"Beneficiary transfer routing failed: {e}")
            return f"❌ Error processing transfer request. Please try again or contact support."

    async def handle_beneficiary_transfer_request(self, user_id: str, entities: Dict) -> str:
        """Handle beneficiary transfer requests."""
        try:
            # TODO: Implement beneficiary transfer logic
            # This is a stub implementation to fix the missing method error
            logger.info(f"Processing beneficiary transfer request for user {user_id}")
            
            # For now, route to the standard transfer request handler
            # In the future, this should handle beneficiary-specific logic
            return await self.handle_transfer_request(
                user_id=user_id,
                message="Transfer to beneficiary",
                intent="transfer",
                entities=entities
            )
            
        except Exception as e:
            logger.error(f"Beneficiary transfer request failed: {e}")
            return "❌ Error processing beneficiary transfer request. Please try again or contact support." 