#!/usr/bin/env python3
"""
Balance Handler Module
Handles all balance-related operations for the Financial Agent.
"""

import asyncio
from typing import Dict, Optional, Any, List, cast
from datetime import datetime
from app.utils.logger import get_logger
from app.services.paystack_service import PaystackService
from app.utils.amount_converter import AmountConverter
import json

logger = get_logger("balance_handler")


class BalanceHandler:
    """Handles balance checking and related operations."""
    
    def __init__(self, paystack_service: PaystackService, memory_manager=None, ai_client=None, ai_model: Optional[str] = None, ai_enabled: bool = False):
        self.paystack = paystack_service
        self.memory = memory_manager
        self.ai_client = ai_client
        self.ai_model = ai_model
        self.ai_enabled = ai_enabled
    
    async def handle_balance_request(self, user_id: str, message: str) -> str:
        """Handle balance check requests."""
        try:
            logger.info(f"Processing balance request for user: {user_id}")
            
            # Get balance from Paystack
            balance_response = await self.paystack.get_balance()
            
            if not balance_response:
                return "❌ Unable to fetch balance at the moment. Please try again later."
            
            # Parse balance response
            balance_info = self._parse_balance_response(balance_response)
            
            # Store balance check in memory if available
            if self.memory:
                await self._store_balance_check(user_id, balance_info)
            
            return self._format_balance_response(balance_info)
            
        except Exception as e:
            logger.error(f"Balance request failed: {e}")
            return "❌ Unable to fetch balance. Please try again or contact support."
    
    def _parse_balance_response(self, balance_response: list) -> Dict[str, Any]:
        """Parse balance response from Paystack."""
        try:
            balance_info: Dict[str, Any] = {
                'ngn_balance': 0,
                'total_balance': 0,
                'currencies': [],
                'available': True
            }
            
            if isinstance(balance_response, list) and balance_response:
                for balance in balance_response:
                    if isinstance(balance, dict):
                        currency = balance.get('currency', 'NGN')
                        amount = balance.get('balance', 0)
                        
                        if currency == 'NGN':
                            balance_info['ngn_balance'] = AmountConverter.to_ngn(amount)
                        
                        balance_info['currencies'].append({
                            'currency': currency,
                            'amount': AmountConverter.to_ngn(amount)
                        })
                        
                        balance_info['total_balance'] += AmountConverter.to_ngn(amount)
            
            return balance_info
            
        except Exception as e:
            logger.error(f"Balance parsing failed: {e}")
            return {
                'ngn_balance': 0,
                'total_balance': 0,
                'currencies': [],
                'available': False,
                'error': str(e)
            }
    
    def _format_balance_response(self, balance_info: Dict) -> str:
        """Format balance response for user."""
        try:
            if not balance_info.get('available', True):
                return "❌ Balance information temporarily unavailable."
            
            ngn_balance = balance_info.get('ngn_balance', 0)
            currencies = balance_info.get('currencies', [])
            
            response = f"💰 **Your Account Balance**\n\n"
            response += f"**NGN Balance**: ₦{ngn_balance:,.2f}\n"
            
            # Show other currencies if available
            other_currencies = [c for c in currencies if c['currency'] != 'NGN']
            if other_currencies:
                response += "\n**Other Currencies:**\n"
                for currency in other_currencies:
                    response += f"• {currency['currency']}: {currency['amount']:,.2f}\n"
            
            response += f"\n✅ Balance retrieved successfully!"
            return response
            
        except Exception as e:
            logger.error(f"Balance formatting failed: {e}")
            return "💰 **Your Account Balance**\n\nBalance retrieved successfully!"
    
    async def _store_balance_check(self, user_id: str, balance_info: Dict):
        """Store balance check in memory for analytics."""
        try:
            if self.memory is None:
                return
            
            # Only store if memory manager has the required method
            if hasattr(self.memory, 'save_balance_check'):
                await self.memory.save_balance_check(user_id, balance_info)
            else:
                logger.debug("Memory manager does not support balance check storage")
                
        except Exception as e:
            logger.error(f"Failed to store balance check: {e}")
    
    async def get_cached_balance(self, user_id: str) -> Optional[Dict]:
        """Get cached balance if available."""
        try:
            if self.memory is None:
                return None
            
            # Only retrieve if memory manager has the required method
            if hasattr(self.memory, 'get_cached_balance'):
                return cast(Optional[Dict], await self.memory.get_cached_balance(user_id))
            else:
                logger.debug("Memory manager does not support balance caching")
                return None
                
        except Exception as e:
            logger.error(f"Failed to get cached balance: {e}")
            return None
    
    async def handle_balance_inquiry(self, user_id: str, message: str, entities: Optional[Dict] = None) -> str:
        """Handle balance inquiry with entity extraction."""
        try:
            logger.info(f"Processing balance inquiry for user: {user_id}")
            
            # Check for cached balance first
            cached_balance = await self.get_cached_balance(user_id)
            if cached_balance and self._is_cache_valid(cached_balance):
                return self._format_balance_response(cached_balance)
            
            # Otherwise, fetch fresh balance
            return await self.handle_balance_request(user_id, message)
            
        except Exception as e:
            logger.error(f"Balance inquiry failed: {e}")
            return "❌ Unable to process balance inquiry. Please try again."
    
    def _is_cache_valid(self, cached_balance: Dict) -> bool:
        """Check if cached balance is still valid."""
        try:
            # TODO: Implement cache validation logic
            # For now, always return False to fetch fresh balance
            return False
            
        except Exception as e:
            logger.error(f"Cache validation failed: {e}")
            return False
    
    async def check_sufficient_balance(self, amount: float) -> Dict:
        """Check if user has sufficient balance for transfer."""
        try:
            balance_data = await self.paystack.get_balance()
            
            if balance_data:
                # Get NGN balance (primary balance)
                ngn_balance = 0
                for balance_info in balance_data:
                    if balance_info.get('currency') == 'NGN':
                        ngn_balance = AmountConverter.to_ngn(balance_info.get('balance', 0))
                        break
                
                return {
                    'sufficient': ngn_balance >= amount,
                    'balance': ngn_balance,
                    'formatted_balance': f"₦{ngn_balance:,.2f}"
                }
            
            return {
                'sufficient': False,
                'balance': 0,
                'formatted_balance': "₦0.00"
            }
            
        except Exception as e:
            logger.error(f"Balance check failed: {e}")
            return {
                'sufficient': False,
                'balance': 0,
                'formatted_balance': "Unable to check balance"
            }
    
    async def get_current_balance_text(self) -> str:
        """Get formatted current balance text."""
        try:
            balance_data = await self.paystack.get_balance()
            if balance_data:
                for balance_info in balance_data:
                    if balance_info.get('currency') == 'NGN':
                        balance = AmountConverter.to_ngn(balance_info.get('balance', 0))
                        return AmountConverter.format_ngn(balance)
            return "Unable to retrieve"
        except:
            return "Unable to retrieve"

    async def handle_balance_check_with_ai(self, user_id: str, message: str, send_follow_up_callback) -> str:
        """Handle balance check requests with immediate response + background processing."""
        try:
            # More human-like immediate acknowledgment responses
            responses = [
                "Let me check your balance real quick! 💰",
                "Getting your current balance... One sec! ⏳",
                "Checking your account balance now... 💭",
                "Hold on, let me pull up your balance! 💰",
                "Getting your balance info... Give me a moment! ⏳"
            ]
            import random
            immediate_response = random.choice(responses)
            
            # Start background processing task with proper error handling
            task = asyncio.create_task(
                self._process_balance_check_background(user_id, message, send_follow_up_callback)
            )
            # Add error callback to catch any unhandled exceptions
            task.add_done_callback(lambda t: self._handle_background_task_error(t, user_id, send_follow_up_callback))
            
            # Return immediate response to user
            return immediate_response
            
        except Exception as e:
            logger.error(f"Failed to start balance check: {e}", exc_info=True)
            # Fallback to traditional method if background processing fails
            try:
                return await self.handle_balance_check(user_id)
            except Exception as fallback_error:
                logger.error(f"Fallback balance check also failed: {fallback_error}", exc_info=True)
                return "Sorry, I'm having trouble checking your balance right now. Please try again."
    
    def _handle_background_task_error(self, task, user_id: str, send_follow_up_callback):
        """Handle errors in background tasks."""
        try:
            if task.exception():
                error = task.exception()
                logger.error(f"Background balance check task failed: {error}", exc_info=True)
                # Try to send error message to user
                asyncio.create_task(
                    send_follow_up_callback(user_id, "Sorry, I couldn't get your balance right now. Please try again.")
                )
        except Exception as e:
            logger.error(f"Error handling background task error: {e}", exc_info=True)
    
    async def _process_balance_check_background(self, user_id: str, message: str, send_follow_up_callback):
        """Process balance check in background and send second response."""
        try:
            logger.info(f"🔄 Starting background balance check for user {user_id}")
            
            # Get balance data from API
            try:
                balance_data = await self.paystack.get_balance()
                logger.info(f"Balance data received: {balance_data}")
            except Exception as api_error:
                logger.error(f"Paystack API error when fetching balance: {api_error}", exc_info=True)
                await send_follow_up_callback(user_id, f"Sorry, I couldn't get your balance right now. Error: {str(api_error)[:50]}")
                return
            
            if not balance_data or not isinstance(balance_data, list) or len(balance_data) == 0:
                logger.warning(f"Empty or invalid balance data received: {balance_data}")
                # Send error response
                await send_follow_up_callback(user_id, "Sorry, I couldn't get your balance right now. Please try again.")
                return
            
            # Process balance data
            primary_balance = balance_data[0]
            current_balance = AmountConverter.to_ngn(primary_balance.get('balance', 0))
            
            # Get recent transactions context
            recent_transactions = await self._get_recent_transaction_context()
            
            # Generate AI-powered response or fallback
            try:
                if self.ai_enabled and self.ai_client:
                    final_response = await self._generate_smart_balance_response(user_id, current_balance, recent_transactions)
                    if final_response:
                        # Store balance check context
                        if self.memory:
                            await self.memory.save_banking_operation_context(
                                user_id=user_id,
                                operation_type="balance_check",
                                operation_data={'requested_by': user_id, 'balance_amount': current_balance},
                                api_response={'success': True, 'current_balance': current_balance}
                            )
                        
                        # Send AI-powered response
                        await send_follow_up_callback(user_id, final_response)
                        logger.info(f"✅ Background balance check completed for user {user_id}")
                        return
                
                # Fallback to simple response  
                fallback_responses = [
                    f"Your balance is ₦{current_balance:,.2f}. Looking good! 💰",
                    f"You've got ₦{current_balance:,.2f} in your account. Nice! 💰",
                    f"Your current balance is ₦{current_balance:,.2f}. Not bad! 💰"
                ]
                import random
                final_response = random.choice(fallback_responses)
                
            except Exception as ai_error:
                logger.error(f"AI balance processing failed: {ai_error}")
                # Simple fallback
                final_response = f"Your balance is ₦{current_balance:,.2f}. Not bad! 💰"
            
            # Store balance check context
            if self.memory:
                await self.memory.save_banking_operation_context(
                    user_id=user_id,
                    operation_type="balance_check",
                    operation_data={'requested_by': user_id, 'balance_amount': current_balance},
                    api_response={'success': True, 'current_balance': current_balance}
                )
            
            # Send the final response
            await send_follow_up_callback(user_id, final_response)
            logger.info(f"✅ Background balance check completed for user {user_id}")
            
        except Exception as e:
            logger.error(f"Background balance check failed: {e}")
            await send_follow_up_callback(user_id, "Something went wrong while checking your balance. Please try again.")

    async def handle_balance_check(self, user_id: str) -> str:
        """Handle balance check requests with comprehensive context storage."""
        try:
            # Get balance data from API - returns a list, not a dict
            balance_data = await self.paystack.get_balance()
            
            # Check if we got valid data
            if not balance_data or not isinstance(balance_data, list) or len(balance_data) == 0:
                # Save failed operation context if memory manager exists
                if self.memory:
                    await self.memory.save_banking_operation_context(
                        user_id=user_id,
                        operation_type="balance_check",
                        operation_data={'requested_by': user_id},
                        api_response={'success': False, 'error': 'No balance data'}
                    )
                return self._handle_balance_error()
            
            # Process balance data - get the first/primary balance
            primary_balance = balance_data[0]
            current_balance = AmountConverter.to_ngn(primary_balance.get('balance', 0))
            
            # Get additional context
            recent_transactions = await self._get_recent_transaction_context()
            
            # Prepare comprehensive operation data
            operation_data = {
                'requested_by': user_id,
                'balance_amount': current_balance,
                'currency': primary_balance.get('currency', 'NGN'),
                'account_type': primary_balance.get('type', 'main')
            }
            
            # Prepare comprehensive API response
            api_response = {
                'success': True,
                'balance_data': primary_balance,
                'current_balance': current_balance,
                'recent_transactions': recent_transactions,
                'context_stored': True
            }
            
            # Save banking operation context if memory manager exists
            if self.memory:
                await self.memory.save_banking_operation_context(
                    user_id=user_id,
                    operation_type="balance_check",
                    operation_data=operation_data,
                    api_response=api_response
                )
                
                # Store detailed transaction context for AI reference
                await self._store_comprehensive_transaction_context(user_id, {
                    'current_balance': current_balance,
                    'recent_activity': recent_transactions,
                    'balance_response': primary_balance
                })
            
            # Generate AI-powered response if enabled
            # if self.ai_enabled and self.ai_client: # This line was removed as per the new_code
            #     response = await self._generate_smart_balance_response(user_id, current_balance, recent_transactions)
            #     if response:
            #         return response
            
            # Fallback to simple response
            return f"Your balance is ₦{current_balance:,.2f}. Not bad!"
            
        except Exception as e:
            logger.error(f"Balance check failed: {e}")
            # Save error context if memory manager exists
            if self.memory:
                await self.memory.save_banking_operation_context(
                    user_id=user_id,
                    operation_type="balance_check",
                    operation_data={'requested_by': user_id},
                    api_response={'success': False, 'error': str(e)}
                )
            return self._handle_balance_error()
    
    async def _generate_smart_balance_response(self, user_id: str, balance: float, recent_transactions: List[Dict]) -> Optional[str]:
        """Generate AI-powered balance response with smart context."""
        try:
            # Get conversation context
            context = await self.memory.get_smart_conversation_context(user_id, "balance check")
            
            # Import ResponseFormatter for safe JSON serialization
            from app.utils.response_utils import ResponseFormatter
            formatter = ResponseFormatter()
            
            # Safely serialize context data
            recent_transactions_safe = formatter.to_json_safe_dict({'transactions': recent_transactions[:3]})
            context_safe = formatter.to_json_safe_dict(context)
            
            # Build context-aware prompt
            system_prompt = f"""You are TizBot, a smart and conversational Nigerian banking assistant. Respond naturally about the user's balance.

🤖 **YOUR PERSONALITY:**
- Name: TizBot - friendly, smart, conversational
- Use Nigerian expressions naturally
- Be helpful and engaging
- Sound like a smart friend, not a robot

Current balance: ₦{balance:,.2f}

Recent transaction context:
{formatter.safe_json_dumps(recent_transactions_safe) if recent_transactions else 'No recent transactions'}

Conversation context:
{formatter.safe_json_dumps(context_safe)}

Guidelines:
- Be conversational and friendly
- Reference recent transactions if relevant
- Keep response under 2 sentences
- Use Nigerian expressions naturally
- Don't be overly formal

Example: "Your balance is ₦7,480. Looking good, especially with that recent ₦4k transaction!"
"""
            
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": "What's my balance?"}
            ]
            
            # Add conversation history for context
            conversations = context.get('recent_conversations', [])
            for conv in conversations[-3:]:
                if not conv.get('message', '').startswith('['):
                    messages.insert(-1, {
                        "role": conv.get('role', 'user'),
                        "content": conv.get('message', '')[:100]
                    })
            
            completion = await self.ai_client.chat.completions.create(
                model=self.ai_model,
                messages=messages,
                max_tokens=150,
                temperature=0.7
            )
            
            response = cast(str, completion.choices[0].message.content)
            if response and response.strip():
                return response.strip()
                
        except Exception as e:
            logger.error(f"Smart balance response failed: {e}")
        
        return None
    
    async def _store_comprehensive_transaction_context(self, user_id: str, data: Dict):
        """Store comprehensive transaction context for AI reference."""
        try:
            # Get detailed recent transactions 
            recent_transactions = await self.paystack.list_transactions(per_page=10)
            transactions = recent_transactions.get('data', []) if recent_transactions else []
            
            # Create comprehensive transaction context
            transaction_context: Dict[str, Any] = {
                'timestamp': datetime.now().isoformat(),
                'balance_info': {
                    'current_balance': data['current_balance'],
                    'recent_activity': data['recent_activity'],
                    'balance_response': data.get('balance_response', {})
                },
                'detailed_transactions': []
            }
            
            # Store detailed transaction info for AI context
            for tx in transactions:
                tx_info = {
                    'amount': AmountConverter.to_ngn(tx.get('amount', 0)),
                    'type': tx.get('channel', 'transfer'),
                    'status': tx.get('status', 'unknown'),
                    'date': tx.get('created_at', ''),
                    'reference': tx.get('reference', ''),
                    'description': tx.get('channel', 'transfer'),
                    'gateway_response': tx.get('gateway_response', ''),
                    'customer': tx.get('customer', {}),
                    'metadata': tx.get('metadata', {})
                }
                transaction_context['detailed_transactions'].append(tx_info)
            
            # Save comprehensive context for AI
            await self.memory.save_message(
                user_id=user_id,
                message="[TRANSACTION_CONTEXT_DETAILED]",
                role="system",
                metadata={
                    'type': 'transaction_context',
                    'context': transaction_context,
                    'stored_for': 'ai_reference',
                    'context_version': '2.0'
                }
            )
            
            logger.debug(f"Stored comprehensive transaction context for user {user_id}")
            
        except Exception as e:
            logger.error(f"Failed to store comprehensive transaction context: {e}")
    
    async def _get_recent_transaction_context(self) -> List[Dict]:
        """Get recent transaction context for balance responses."""
        try:
            transactions_response = await self.paystack.list_transactions(per_page=5)
            
            if not transactions_response or not transactions_response.get('status'):
                return []
            
            transactions = transactions_response.get('data', [])
            context: List[Dict] = []
            
            for tx in transactions:
                context.append({
                    'amount': AmountConverter.to_ngn(tx.get('amount', 0)),
                    'type': tx.get('channel', 'transfer'),
                    'date': tx.get('created_at', ''),
                    'status': tx.get('status', 'success'),
                    'reference': tx.get('reference', '')
                })
            
            return context
            
        except Exception as e:
            logger.error(f"Failed to get recent transaction context: {e}")
            return []

    def _handle_balance_error(self) -> str:
        """Helper to provide a consistent error message for balance checks."""
        return "Sorry, I couldn't check your balance right now. Please try again."

    async def _get_account_balance(self, user_id: str) -> Dict:
        """Get account balance data for internal use."""
        try:
            balance_data = await self.paystack.get_balance()
            
            if balance_data:
                # Get NGN balance (primary balance)
                ngn_balance = 0
                for balance_info in balance_data:
                    if balance_info.get('currency') == 'NGN':
                        ngn_balance = AmountConverter.to_ngn(balance_info.get('balance', 0))
                        break
                
                return {
                    'success': True,
                    'balance': ngn_balance,
                    'formatted_balance': f"₦{ngn_balance:,.2f}",
                    'currency': 'NGN'
                }
            
            return {
                'success': False,
                'balance': 0,
                'formatted_balance': "₦0.00",
                'error': 'Unable to retrieve balance'
            }
            
        except Exception as e:
            logger.error(f"Account balance retrieval failed: {e}")
            return {
                'success': False,
                'balance': 0,
                'formatted_balance': "Unable to retrieve balance",
                'error': str(e)
            }

    async def _process_balance_check_traditional(self, user_id: str) -> str:
        """Process balance check using traditional method."""
        try:
            balance_data = await self._get_account_balance(user_id)
            
            if balance_data['success']:
                return self._format_simple_balance_response(balance_data['balance'])
            else:
                return "Sorry, I couldn't check your balance right now. Try again?"
                
        except Exception as e:
            logger.error(f"Traditional balance check failed: {e}")
            return "Sorry, I couldn't check your balance right now. Try again?"

    def _format_simple_balance_response(self, balance: float) -> str:
        """Format balance response in a natural, conversational way."""
        try:
            # Natural, conversational response
            if balance > 10000:
                return f"You've got ₦{balance:,.2f} in your account. Looking good! 💰"
            elif balance > 1000:
                return f"Your balance is ₦{balance:,.2f}. Not bad!"
            elif balance > 0:
                return f"You have ₦{balance:,.2f} left. Might want to top up soon."
            else:
                return f"Your balance is ₦{balance:,.2f}. Time to add some funds!"
                
        except Exception as e:
            logger.error(f"Balance response formatting failed: {e}")
            return f"Your balance is ₦{balance:,.2f}" 