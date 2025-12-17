#!/usr/bin/env python3
"""
History Handler Module
Handles all transaction history operations for the Financial Agent.
"""

import asyncio
import json
from typing import Dict, Optional, List, Any, cast
from datetime import datetime, timedelta
from app.utils.logger import get_logger
from app.services.paystack_service import PaystackService

logger = get_logger("history_handler")


class HistoryHandler:
    """Handles all transaction history operations."""
    
    def __init__(self, paystack_service: PaystackService, memory_manager=None, ai_client=None, ai_model=None, ai_enabled=False):
        self.paystack = paystack_service
        self.memory = memory_manager  # Properly initialize memory manager
        self.ai_client = ai_client
        self.ai_model = ai_model
        self.ai_enabled = ai_enabled
    
    async def handle_history_request_with_ai(self, user_id: str, message: str, send_follow_up_callback) -> str:
        """Handle transaction history requests with immediate response + background processing."""
        try:
            # Check if this is a specific transaction-only request (money received only)
            is_transactions_only = any(keyword in message.lower() for keyword in [
                'transactions only', 'money received', 'incoming only', 'received money',
                'money in', 'incoming transactions', 'credits only', 'deposits only'
            ])
            
            # Default to comprehensive history (both money in and out) for general "history" requests
            if is_transactions_only:
                # More human-like immediate response for transaction-only request
                responses = [
                    "Checking the money you've received! Give me a sec... 💰",
                    "Looking up your incoming transactions... One moment! ⏳",
                    "Getting your received money records... Hold on! 💭"
                ]
                import random
                immediate_response = random.choice(responses)
                
                # Start transaction-only background processing
                asyncio.create_task(self._process_transaction_history_background(user_id, message, send_follow_up_callback))
            else:
                # Comprehensive history is the default for "history", "my history", etc.
                responses = [
                    "Let me pull up your complete financial picture - both money in and out! Give me a sec... 💭",
                    "Checking everything for you - all the money coming in and going out! One moment... ⏳",
                    "Getting your full financial story ready - incoming and outgoing! Hold on... 🔍",
                    "Checking your money movements - both received and sent! One sec... 🔍"
                ]
                import random
                immediate_response = random.choice(responses)
                
                # Start comprehensive background processing (includes both incoming and outgoing)
                asyncio.create_task(self._process_comprehensive_history_background(user_id, message, send_follow_up_callback))
            
            # Return immediate response to user
            return immediate_response
            
        except Exception as e:
            logger.error(f"Failed to start history request: {e}")
            # Fallback to traditional method if background processing fails
            return await self.handle_history_request(user_id, message, entities={})
    
    async def handle_transfers_sent_with_ai(self, user_id: str, message: str, send_follow_up_callback) -> str:
        """Handle transfers sent requests with immediate response + background processing."""
        try:
            # More human-like immediate acknowledgment responses
            responses = [
                "Checking the money you've sent out! Give me a sec... 💸",
                "Let me see what transfers you've made! One moment... ⏳", 
                "Looking up all the transfers you sent... Hold on! 🔍",
                "Getting your outgoing money records ready! ⏳"
            ]
            import random
            immediate_response = random.choice(responses)
            
            # Start background processing task (don't await it)
            asyncio.create_task(self._process_transfers_sent_background(user_id, message, send_follow_up_callback))
            
            # Return immediate response to user
            return immediate_response
            
        except Exception as e:
            logger.error(f"Failed to start transfers sent request: {e}")
            # Fallback to traditional method if background processing fails
            return await self.handle_transfers_sent_request(user_id, message, entities={})
    
    async def _process_comprehensive_history_background(self, user_id: str, message: str, send_follow_up_callback):
        """Process comprehensive history in background and send second response."""
        try:
            logger.info(f"🔄 Starting background comprehensive history processing for user {user_id}")
            
            # Get comprehensive financial history (both incoming and outgoing)
            comprehensive_data = await self._fetch_comprehensive_history_for_ai(user_id, message)
            
            if not comprehensive_data or 'error' in comprehensive_data:
                # Send error response
                await send_follow_up_callback(user_id, "Sorry, I couldn't retrieve your history right now. Please try again later.")
                return
            
            # Generate AI explanation or fallback
            try:
                final_response = await self._explain_comprehensive_history_with_ai(user_id, message, comprehensive_data)
            except Exception as ai_error:
                logger.error(f"AI processing failed in background: {ai_error}")
                # Create fallback response
                final_response = self._create_comprehensive_fallback_response(comprehensive_data)
            
            # Send the complete results as second message
            await send_follow_up_callback(user_id, final_response)
            logger.info(f"✅ Background comprehensive history processing completed for user {user_id}")
            
        except Exception as e:
            logger.error(f"Background history processing failed: {e}")
            await send_follow_up_callback(user_id, "Something went wrong while getting your history. Please try again.")
    
    async def _process_transfers_sent_background(self, user_id: str, message: str, send_follow_up_callback):
        """Process transfers sent in background and send second response."""
        try:
            logger.info(f"🔄 Starting background transfers sent processing for user {user_id}")
            
            # Get transfers data
            transfers_data = await self._fetch_transfers_data_for_ai(user_id, message)
            
            if not transfers_data or 'error' in transfers_data:
                # Send error response
                await send_follow_up_callback(user_id, "Sorry, I couldn't retrieve your transfer history right now. Please try again later.")
                return
            
            # Generate AI explanation or fallback
            try:
                final_response = await self._explain_transfers_with_ai(user_id, message, transfers_data)
            except Exception as ai_error:
                logger.error(f"AI processing failed in background: {ai_error}")
                # Create simple fallback response
                if transfers_data.get('transfer_count', 0) > 0:
                    total_sent = sum(t.get('amount', 0) for t in transfers_data.get('transfers', []))
                    final_response = f"You've sent ₦{total_sent:,.0f} across {transfers_data['transfer_count']} transfers {transfers_data.get('period', 'recently')}."
                else:
                    final_response = f"No transfers found {transfers_data.get('period', 'for the period you requested')}."
            
            # Send the complete results as second message
            await send_follow_up_callback(user_id, final_response)
            logger.info(f"✅ Background transfers sent processing completed for user {user_id}")
            
        except Exception as e:
            logger.error(f"Background transfers sent processing failed: {e}")
            await send_follow_up_callback(user_id, "Something went wrong while getting your transfer history. Please try again.")
    
    async def _process_transaction_history_background(self, user_id: str, message: str, send_follow_up_callback):
        """Process regular transaction history in background and send second response."""
        try:
            logger.info(f"🔄 Starting background transaction history processing for user {user_id}")
            
            # Get transaction history data
            transaction_data = await self._fetch_transaction_data_for_ai(user_id, message)
            
            if not transaction_data or 'error' in transaction_data:
                # Send error response
                await send_follow_up_callback(user_id, "Sorry, I couldn't retrieve your transaction history right now. Please try again later.")
                return
            
            # Generate AI explanation or fallback
            try:
                final_response = await self._explain_transactions_with_ai(user_id, message, transaction_data)
            except Exception as ai_error:
                logger.error(f"AI processing failed in background: {ai_error}")
                # Create fallback response
                final_response = self._create_transaction_fallback_response(transaction_data)
            
            # Send the complete results as second message
            await send_follow_up_callback(user_id, final_response)
            logger.info(f"✅ Background transaction history processing completed for user {user_id}")
            
        except Exception as e:
            logger.error(f"Background transaction history processing failed: {e}")
            await send_follow_up_callback(user_id, "Something went wrong while getting your transaction history. Please try again.")
    
    async def _fetch_comprehensive_history_for_ai(self, user_id: str, message: str) -> Dict:
        """Fetch comprehensive financial history including BOTH transactions (incoming) AND transfers (outgoing)."""
        try:
            # Parse time filter
            from_date, to_date, period_text = self.parse_time_filter(message)
            
            # Get transactions (incoming money)
            if from_date:
                transaction_response = await self.paystack.list_transactions(
                    per_page=20,
                    from_date=from_date
                )
            else:
                transaction_response = await self.paystack.list_transactions(
                    per_page=20
                )
            
            # Get transfers (outgoing money)
            if from_date and to_date:
                transfers_result = await self.paystack.list_transfers(
                    per_page=20,
                    from_date=from_date,
                    to_date=to_date
                )
            else:
                transfers_result = await self.paystack.list_transfers(
                    per_page=20
                )
            
            # Get current balance
            balance_data = await self.paystack.get_balance()
            current_balance = 0
            if balance_data:
                for balance_info in balance_data:
                    if balance_info.get('currency') == 'NGN':
                        current_balance = balance_info.get('balance', 0) / 100
                        break
            
            transactions = transaction_response.get('data', []) if transaction_response else []
            transfers = transfers_result.get('data', []) if transfers_result else []
            
            # Filter transfers by date if specified
            if from_date and to_date:
                filtered_transfers = []
                for tf in transfers:
                    transfer_date = tf.get('createdAt', tf.get('created_at', ''))
                    if transfer_date:
                        try:
                            tf_date = datetime.fromisoformat(transfer_date.replace('Z', '+00:00')).date()
                            from_dt = datetime.strptime(from_date, "%Y-%m-%d").date()
                            to_dt = datetime.strptime(to_date, "%Y-%m-%d").date()
                            if from_dt <= tf_date <= to_dt:
                                filtered_transfers.append(tf)
                        except:
                            filtered_transfers.append(tf)
                transfers = filtered_transfers
            
            # Structure comprehensive data for AI
            structured_data = {
                'period': period_text,
                'current_balance': current_balance,
                'transaction_count': len(transactions),
                'transfer_count': len(transfers),
                'incoming_transactions': [],
                'outgoing_transfers': []
            }
            
            # Process incoming transactions
            total_received = 0
            for tx in transactions[:10]:  # Limit for AI processing
                amount = tx.get('amount', 0) / 100
                total_received += amount
                
                tx_data = {
                    'amount': amount,
                    'status': tx.get('status', 'unknown'),
                    'channel': tx.get('channel', 'unknown'),
                    'date': tx.get('created_at', '')[:10] if tx.get('created_at') else 'unknown',
                    'type': 'received'
                }
                structured_data['incoming_transactions'].append(tx_data)
            
            # Process outgoing transfers
            total_sent = 0
            for tf in transfers[:10]:  # Limit for AI processing
                amount = tf.get('amount', 0) / 100
                total_sent += amount
                
                # Get recipient name
                recipient = tf.get('recipient', {})
                recipient_name = recipient.get('name', 'Unknown') if isinstance(recipient, dict) else str(recipient)
                
                # Get date
                date_str = tf.get('createdAt', tf.get('created_at', ''))
                date = date_str[:10] if date_str else 'unknown'
                
                tf_data = {
                    'amount': amount,
                    'recipient': recipient_name,
                    'status': tf.get('status', 'unknown'),
                    'date': date,
                    'type': 'sent'
                }
                structured_data['outgoing_transfers'].append(tf_data)
            
            structured_data['total_received'] = total_received
            structured_data['total_sent'] = total_sent
            structured_data['net_flow'] = total_received - total_sent
            
            # Save transactions to database for future reference (async, don't wait)
            if transaction_response and transaction_response.get('data'):
                asyncio.create_task(self._save_transactions_to_database(user_id, transaction_response['data']))
            
            return structured_data
            
        except Exception as e:
            logger.error(f"Failed to fetch comprehensive history for AI: {e}")
            return {'error': str(e)}
    
    async def _fetch_transfers_data_for_ai(self, user_id: str, message: str) -> Dict:
        """Fetch transfers data in a structured format for AI processing with combined sources."""
        try:
            # Parse time filter
            from_date, to_date, period_text = self.parse_time_filter(message)
            
            # Get transfers from BOTH database and API
            database_transfers = []
            api_transfers = []
            
            # 1. Get from database
            if self.memory and hasattr(self.memory, 'get_transfer_history'):
                try:
                    database_transfers = await self.memory.get_transfer_history(user_id, limit=30)
                except Exception as db_error:
                    logger.warning(f"Database transfer retrieval failed: {db_error}")
            
            # 2. Get from API
            try:
                if from_date and to_date:
                    transfers_result = await self.paystack.list_transfers(
                        per_page=20,
                        from_date=from_date,
                        to_date=to_date
                    )
                else:
                    transfers_result = await self.paystack.list_transfers(
                        per_page=20
                    )
                api_transfers = transfers_result.get('data', []) if transfers_result else []
            except Exception as api_error:
                logger.warning(f"API transfer retrieval failed: {api_error}")
            
            # Get current balance
            balance_data = await self.paystack.get_balance()
            current_balance = 0
            if balance_data:
                for balance_info in balance_data:
                    if balance_info.get('currency') == 'NGN':
                        current_balance = balance_info.get('balance', 0) / 100
                        break
            
            # Combine transfers from both sources
            transfers = self._combine_transfer_sources(database_transfers, api_transfers)
            
            # Filter by date if specified
            if from_date and to_date:
                filtered_transfers = []
                for tf in transfers:
                    transfer_date = tf.get('createdAt', tf.get('created_at', ''))
                    if transfer_date:
                        try:
                            tf_date = datetime.fromisoformat(transfer_date.replace('Z', '+00:00')).date()
                            from_dt = datetime.strptime(from_date, "%Y-%m-%d").date()
                            to_dt = datetime.strptime(to_date, "%Y-%m-%d").date()
                            if from_dt <= tf_date <= to_dt:
                                filtered_transfers.append(tf)
                        except:
                            filtered_transfers.append(tf)
                transfers = filtered_transfers
            
            # Structure data for AI
            structured_data = {
                'period': period_text,
                'current_balance': current_balance,
                'transfer_count': len(transfers),
                'transfers': []
            }
            
            # Process transfers for AI
            total_sent = 0
            for tf in transfers[:10]:  # Limit for AI processing
                amount = tf.get('amount', 0) / 100
                total_sent += amount
                
                # Get recipient name
                recipient = tf.get('recipient', {})
                recipient_name = recipient.get('name', 'Unknown') if isinstance(recipient, dict) else str(recipient)
                
                # Get date
                date_str = tf.get('createdAt', tf.get('created_at', ''))
                date = date_str[:10] if date_str else 'unknown'
                
                tf_data = {
                    'amount': amount,
                    'recipient': recipient_name,
                    'status': tf.get('status', 'unknown'),
                    'date': date,
                    'reason': tf.get('reason', '')[:30] + '...' if tf.get('reason') else ''  # Shortened for AI
                }
                structured_data['transfers'].append(tf_data)
            
            structured_data['total_sent'] = total_sent
            
            return structured_data
            
        except Exception as e:
            logger.error(f"Failed to fetch transfers data for AI: {e}")
            return {'error': str(e)}
    
    async def _fetch_transaction_data_for_ai(self, user_id: str, message: str) -> Dict:
        """Fetch transaction data for AI processing with combined database and API sources."""
        try:
            # Parse time filter
            from_date, to_date, period_text = self.parse_time_filter(message)
            
            # Get transactions from BOTH database and API
            database_transactions = []
            api_transactions = []
            
            # 1. Get from database
            if self.memory and hasattr(self.memory, 'get_transaction_history'):
                try:
                    database_transactions = await self.memory.get_transaction_history(user_id, limit=30)
                    logger.info(f"Retrieved {len(database_transactions)} transactions from database")
                except Exception as db_error:
                    logger.warning(f"Database transaction retrieval failed: {db_error}")
            
            # 2. Get from API
            try:
                if from_date:
                    transaction_response = await self.paystack.list_transactions(
                        per_page=20,
                        from_date=from_date
                    )
                else:
                    transaction_response = await self.paystack.list_transactions(
                        per_page=20
                    )
                api_transactions = transaction_response.get('data', []) if transaction_response else []
                logger.info(f"Retrieved {len(api_transactions)} transactions from Paystack API")
            except Exception as api_error:
                logger.warning(f"API transaction retrieval failed: {api_error}")
            
            # Get current balance
            balance_data = await self.paystack.get_balance()
            current_balance = 0
            if balance_data:
                for balance_info in balance_data:
                    if balance_info.get('currency') == 'NGN':
                        current_balance = balance_info.get('balance', 0) / 100
                        break
            
            # Combine transactions from both sources
            transactions = self._combine_transaction_sources(database_transactions, api_transactions)
            
            # Filter by date if specified
            if from_date and to_date:
                filtered_transactions = []
                for tx in transactions:
                    transaction_date = tx.get('created_at', tx.get('timestamp', ''))
                    if transaction_date:
                        try:
                            tx_date = datetime.fromisoformat(transaction_date.replace('Z', '+00:00')).date()
                            from_dt = datetime.strptime(from_date, "%Y-%m-%d").date()
                            to_dt = datetime.strptime(to_date, "%Y-%m-%d").date()
                            if from_dt <= tx_date <= to_dt:
                                filtered_transactions.append(tx)
                        except:
                            filtered_transactions.append(tx)
                transactions = filtered_transactions
            
            # Structure data for AI
            structured_data = {
                'period': period_text,
                'current_balance': current_balance,
                'transaction_count': len(transactions),
                'transactions': []
            }
            
            # Process transactions for AI
            total_received = 0
            for tx in transactions[:10]:  # Limit for AI processing
                amount = tx.get('amount', 0) / 100
                total_received += amount
                
                tx_data = {
                    'amount': amount,
                    'status': tx.get('status', 'unknown'),
                    'channel': tx.get('channel', 'unknown'),
                    'date': tx.get('created_at', tx.get('timestamp', ''))[:10] if tx.get('created_at', tx.get('timestamp')) else 'unknown',
                    'type': 'received',
                    'source': tx.get('source', 'api')
                }
                structured_data['transactions'].append(tx_data)
            
            structured_data['total_received'] = total_received
            
            # Save transactions to database for future reference
            if api_transactions:
                asyncio.create_task(self._save_transactions_to_database(user_id, api_transactions))
            
            return structured_data
            
        except Exception as e:
            logger.error(f"Failed to fetch transaction data for AI: {e}")
            return {'error': str(e)}
    
    def parse_time_filter(self, message: str) -> tuple:
        """Parse time-related keywords from message and return date range."""
        
        message_lower = message.lower()
        today = datetime.now()
        
        # Enhanced logging for debugging
        logger.info(f"🗓️ Parsing time filter from message: '{message}'")
        
        # Today
        if any(phrase in message_lower for phrase in ["today", "tod"]):
            from_date = today.strftime("%Y-%m-%d")
            to_date = today.strftime("%Y-%m-%d")
            logger.info(f"🗓️ Detected 'today': {from_date}")
            return from_date, to_date, "Today"
            
        # This week (last 7 days including today)
        elif any(phrase in message_lower for phrase in ["this week", "week", "7 days"]):
            from_date = (today - timedelta(days=6)).strftime("%Y-%m-%d")
            to_date = today.strftime("%Y-%m-%d")
            logger.info(f"🗓️ Detected 'this week' (7 days): {from_date} to {to_date}")
            return from_date, to_date, "This Week"
            
        # Last week
        elif any(phrase in message_lower for phrase in ["last week", "past week", "previous week"]):
            last_week_start = today - timedelta(days=today.weekday() + 7)
            last_week_end = last_week_start + timedelta(days=6)
            from_date = last_week_start.strftime("%Y-%m-%d")
            to_date = last_week_end.strftime("%Y-%m-%d")
            logger.info(f"🗓️ Detected 'last week': {from_date} to {to_date}")
            return from_date, to_date, "Last Week"
            
        # This month
        elif any(phrase in message_lower for phrase in ["this month", "month"]):
            from_date = today.replace(day=1).strftime("%Y-%m-%d")
            to_date = today.strftime("%Y-%m-%d")
            logger.info(f"🗓️ Detected 'this month': {from_date} to {to_date}")
            return from_date, to_date, "This Month"
            
        # Last month
        elif any(phrase in message_lower for phrase in ["last month", "past month", "previous month"]):
            first_day_this_month = today.replace(day=1)
            last_day_last_month = first_day_this_month - timedelta(days=1)
            first_day_last_month = last_day_last_month.replace(day=1)
            from_date = first_day_last_month.strftime("%Y-%m-%d")
            to_date = last_day_last_month.strftime("%Y-%m-%d")
            logger.info(f"🗓️ Detected 'last month': {from_date} to {to_date}")
            return from_date, to_date, "Last Month"
        
        # Recent/All time (no filter)
        else:
            logger.info(f"🗓️ No specific time filter detected, using 'All Time'")
            return None, None, "All Time"
    
    def _create_comprehensive_fallback_response(self, data: Dict) -> str:
        """Create a natural fallback response when AI fails, using Nigerian conversational style."""
        try:
            # Create natural response based on data
            balance_text = f"₦{data['current_balance']:,.0f}"
            
            if data['transfer_count'] > 0 and data['transaction_count'] > 0:
                # Both incoming and outgoing activity
                return f"You've been active! Received ₦{data['total_received']:,.0f} from {data['transaction_count']} transactions and sent ₦{data['total_sent']:,.0f} from {data['transfer_count']} transfers. Your balance is {balance_text}."
            
            elif data['transaction_count'] > 0:
                # Only incoming activity
                if data['transaction_count'] == 1:
                    return f"You received ₦{data['total_received']:,.0f} from 1 transaction. Your balance is {balance_text}."
                else:
                    return f"You received ₦{data['total_received']:,.0f} from {data['transaction_count']} transactions. Your balance is {balance_text}."
            
            elif data['transfer_count'] > 0:
                # Only outgoing activity
                if data['transfer_count'] == 1:
                    return f"You sent ₦{data['total_sent']:,.0f} from 1 transfer. Your balance is {balance_text}."
                else:
                    return f"You sent ₦{data['total_sent']:,.0f} from {data['transfer_count']} transfers. Your balance is {balance_text}."
            
            else:
                # No activity
                return f"No recent activity found for {data['period'].lower()}. Your current balance is {balance_text}."
                
        except Exception as e:
            logger.error(f"Failed to create fallback response: {e}")
            return f"Your current balance is ₦{data.get('current_balance', 0):,.0f}."
    
    async def _explain_comprehensive_history_with_ai(self, user_id: str, message: str, data: Dict) -> str:
        """Use AI to explain comprehensive financial history (both incoming and outgoing) in a conversational way."""
        try:
            if not self.ai_enabled or not self.ai_client:
                # Fallback to traditional response
                return self._create_comprehensive_fallback_response(data)
            
            # Create conversational prompt for explaining comprehensive history
            system_prompt = """You are a friendly Nigerian banking assistant explaining complete financial history to a user.

IMPORTANT GUIDELINES:
- Speak like a helpful Nigerian friend, not a formal banker
- Use natural Nigerian English and expressions 
- Keep responses conversational and relatable (3-5 sentences max)
- Focus on the complete picture - money in AND money out
- Don't use technical jargon or reference numbers
- Make it sound like you're explaining to a friend over WhatsApp
- Be encouraging and paint a clear picture of their financial activity
- Highlight both incoming and outgoing money naturally

Examples of GOOD responses:
- "You've been active this week! ₦13k came in from payments, but you sent ₦1.5k to Temmy. Net gain of ₦11.5k - not bad at all!"
- "This month you received ₦25k total and sent out ₦8k to different people. Your balance is sitting pretty at ₦45k now!"
- "Quiet period o - just ₦4k came in and you sent ₦2k to John. Your account balance is ₦7.5k, still looking good!"

Examples of BAD responses:
- "📊 Complete Financial History: Incoming ₦13,000, Outgoing ₦1,500, Net Flow ₦11,500..."
- "Your comprehensive transaction analysis shows 4 incoming and 1 outgoing..."
- "Based on your complete financial data, you have maintained positive cash flow..."

Be natural, friendly, and paint the full financial picture!"""

            # Prepare comprehensive summary for AI
            user_prompt = f"""The user asked: "{message}"

Here's their complete financial history for {data['period']}:
- Current balance: ₦{data['current_balance']:,.2f}
- Money received: ₦{data['total_received']:,.2f} from {data['transaction_count']} transactions
- Money sent: ₦{data['total_sent']:,.2f} from {data['transfer_count']} transfers
- Net flow: ₦{data['net_flow']:,.2f}

Recent activity:"""

            # Combine and sort recent activity by date
            all_activity = []
            
            for tx in data['incoming_transactions'][:3]:
                all_activity.append((tx['date'], f"₦{tx['amount']:,.2f} received via {tx['channel']}"))
            
            for tf in data['outgoing_transfers'][:3]:
                all_activity.append((tf['date'], f"₦{tf['amount']:,.2f} sent to {tf['recipient']}"))
            
            # Sort by date (most recent first)
            all_activity.sort(reverse=True)
            
            if all_activity:
                for date, activity in all_activity[:5]:  # Show max 5 recent activities
                    user_prompt += f"\n• {activity} on {date}"
            else:
                user_prompt += f"\n• No activity found for {data['period'].lower()}"

            user_prompt += f"\n\nExplain their complete financial picture like a friend would - natural, encouraging, and comprehensive."

            # Generate AI response
            if not self.ai_model:
                # Fallback if model is None
                return self._create_comprehensive_fallback_response(data)
                
            logger.info(f"🤖 Generating comprehensive AI explanation for user {user_id}")
            
            try:
                # Use asyncio.wait_for for proper timeout handling
                import asyncio
                
                completion_task = self.ai_client.chat.completions.create(
                    model=self.ai_model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    max_tokens=250,
                    temperature=0.8  # More creative for natural conversation
                )
                
                # Wait for AI response with 10 second timeout
                completion = await asyncio.wait_for(completion_task, timeout=10.0)

                ai_response = cast(str, completion.choices[0].message.content)
                if ai_response:
                    logger.info(f"✅ AI comprehensive explanation generated successfully")
                    return ai_response.strip()
                else:
                    logger.warning(f"⚠️ AI returned empty response, using fallback")
                    # Create smart fallback response
                    return self._create_comprehensive_fallback_response(data)
                    
            except asyncio.TimeoutError:
                logger.error(f"⏰ AI call timed out after 10 seconds, using fallback response")
                return self._create_comprehensive_fallback_response(data)
            except Exception as ai_error:
                logger.error(f"❌ AI completion failed: {ai_error}")
                return self._create_comprehensive_fallback_response(data)

        except Exception as e:
            logger.error(f"AI comprehensive history explanation failed: {e}")
            # Fallback to traditional method
            return self._create_comprehensive_fallback_response(data)
    
    async def _explain_transfers_with_ai(self, user_id: str, message: str, data: Dict) -> str:
        """Use AI to explain transfers data in a conversational, human-like way."""
        try:
            if not self.ai_enabled or not self.ai_client:
                # Fallback to traditional response
                return await self.handle_transfers_sent_request(user_id, message, entities={})
            
            # Create conversational prompt for explaining transfers
            system_prompt = """You are a friendly Nigerian banking assistant explaining transfer history to a user.

IMPORTANT GUIDELINES:
- Speak like a helpful Nigerian friend, not a formal banker
- Use natural Nigerian English and expressions
- Keep responses conversational and relatable (2-4 sentences max)
- Focus on what users actually care about - who they sent money to and how much
- Don't use technical jargon, reference numbers, or formal language
- Make it sound like you're explaining to a friend over WhatsApp
- Be encouraging and positive about their financial activity

Examples of GOOD responses:
- "You sent ₦1,500 to Temmy this week - just that one transfer. Your balance is still good at ₦7,470!"
- "Looks like you've been sending money around! ₦15k total this month - mostly to family. Balance sitting at ₦25k."
- "Quiet week for transfers o - just sent ₦2k to John on Monday. You still have ₦45k left."

Examples of BAD responses:
- "📤 Your Outgoing Transfers Analysis: Total sent ₦1,500, Number of transfers: 1..."
- "Transfer summary shows the following outgoing payment details..."
- "Based on your transfer data, you have made 1 successful transaction..."

Be natural, friendly, and encouraging!"""

            # Prepare transfers summary for AI
            user_prompt = f"""The user asked: "{message}"

Here's their transfer data for {data['period']}:
- Current balance: ₦{data['current_balance']:,.2f}
- Total sent: ₦{data['total_sent']:,.2f}
- Number of transfers: {data['transfer_count']}

Recent transfers:"""

            if data['transfers']:
                for tf in data['transfers'][:5]:  # Show max 5 to AI
                    status_text = "successful" if tf['status'] == 'success' else tf['status']
                    reason_text = f" ({tf['reason']})" if tf['reason'] else ""
                    user_prompt += f"\n• ₦{tf['amount']:,.2f} to {tf['recipient']} on {tf['date']}{reason_text}"
            else:
                user_prompt += f"\n• No transfers made in {data['period'].lower()}"

            user_prompt += f"\n\nExplain this to them like a friend would - natural, encouraging, and conversational."

            # Generate AI response
            if not self.ai_model:
                # Fallback if model is None
                return await self.handle_transfers_sent_request(user_id, message, entities={})
                
            completion = await self.ai_client.chat.completions.create(
                model=self.ai_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                max_tokens=200,
                temperature=0.8  # More creative for natural conversation
            )

            ai_response = cast(str, completion.choices[0].message.content)
            if ai_response:
                return ai_response.strip()
            else:
                # Fallback if AI doesn't respond
                return await self.handle_transfers_sent_request(user_id, message, entities={})

        except Exception as e:
            logger.error(f"AI transfers explanation failed: {e}")
            # Fallback to traditional method
            return await self.handle_transfers_sent_request(user_id, message, entities={})
    
    async def handle_history_request(self, user_id: str, message: str, entities: Dict) -> str:
        """Handle transaction history requests with comprehensive context storage."""
        try:
            logger.info(f"Processing history request for user {user_id}")
            
            # Save initial history request context
            await self.memory.save_banking_operation_context(
                user_id=user_id,
                operation_type="history_request_initiated",
                operation_data={
                    'message': message,
                    'entities': entities,
                    'timestamp': datetime.utcnow().isoformat()
                },
                api_response={'status': 'initiated', 'success': True}
            )
            
            # Determine time filter from message
            from_date, to_date, period = self._extract_time_filter(message)
            
            # Get transactions from Paystack API
            logger.info(f"Fetching transactions with time filter: {period}")
            transactions_response = await self.paystack.list_transactions(per_page=20)
            
            if not transactions_response or not transactions_response.get('status'):
                # Save API error context
                await self.memory.save_banking_operation_context(
                    user_id=user_id,
                    operation_type="history_api_error",
                    operation_data={'time_filter': period, 'message': message},
                    api_response={'success': False, 'error': 'api_failure'}
                )
                return "❌ Could not fetch your transaction history right now. Please try again."
            
            transactions = transactions_response.get('data', [])
            
            # Filter transactions based on time
            filtered_transactions = self._filter_transactions_by_time(transactions, from_date if from_date else "", to_date if to_date else "")
            
            # Save successful history retrieval context
            await self.memory.save_banking_operation_context(
                user_id=user_id,
                operation_type="history_retrieved",
                operation_data={
                    'time_filter': period,
                    'total_transactions': len(transactions),
                    'filtered_transactions': len(filtered_transactions),
                    'message': message
                },
                api_response={
                    'success': True,
                    'transaction_count': len(filtered_transactions),
                    'api_response': transactions_response
                }
            )
            
            # Store detailed transaction context for AI reference
            await self._store_detailed_history_context(user_id, filtered_transactions, period)
            
            if not filtered_transactions:
                period_text = self._get_period_text(period)
                
                # Check current balance for context
                balance_response = await self.paystack.get_balance()
                current_balance = 0
                if balance_response and isinstance(balance_response, list):
                    # balance_response is a List[Dict], not a Dict
                    if balance_response:  # Check if list is not empty
                        for balance_info in balance_response:
                            if balance_info.get('currency') == 'NGN':
                                current_balance = balance_info.get('balance', 0) / 100
                                break
                
                return f"📊 **Your Transaction History ({period_text}):**\n\nNo transactions found for the specified period.\n\n💰 **Current Balance**: ₦{current_balance:,.2f}"
            
            # Generate AI-powered response if enabled
            if self.ai_enabled and self.ai_client:
                ai_response = await self._generate_smart_history_response(user_id, filtered_transactions, period, message)
                if ai_response:
                    return ai_response
            
            # Fallback to structured response
            return await self._format_transaction_history(filtered_transactions, period)
            
        except Exception as e:
            logger.error(f"History request handling failed: {e}")
            # Save error context
            await self.memory.save_banking_operation_context(
                user_id=user_id,
                operation_type="history_request_error",
                operation_data={'message': message, 'entities': entities},
                api_response={'success': False, 'error': str(e)}
            )
            return f"❌ Failed to get transaction history: {str(e)}"
    
    async def _store_detailed_history_context(self, user_id: str, transactions: List[Dict], time_filter: str):
        """Store detailed transaction history context for AI reference."""
        try:
            # Create comprehensive transaction history context
            history_context: Dict[str, Any] = {
                'timestamp': datetime.utcnow().isoformat(),
                'time_filter': time_filter,
                'transaction_count': len(transactions),
                'transactions_summary': [],
                'total_incoming': 0,
                'total_outgoing': 0,
                'period_analysis': {}
            }
            
            # Analyze transactions
            for tx in transactions:
                amount = tx.get('amount', 0) / 100
                status = tx.get('status', 'unknown')
                channel = tx.get('channel', 'unknown')
                date = tx.get('created_at', '')
                
                # Categorize transaction
                if channel in ['dedicated_nuban', 'bank_transfer'] and status == 'success':
                    history_context['total_incoming'] += amount
                elif channel in ['transfer'] and status == 'success':
                    history_context['total_outgoing'] += amount
                
                # Store transaction summary
                tx_summary = {
                    'amount': amount,
                    'type': channel,
                    'status': status,
                    'date': date,
                    'reference': tx.get('reference', ''),
                    'customer_info': tx.get('customer', {}),
                    'metadata': tx.get('metadata', {})
                }
                history_context['transactions_summary'].append(tx_summary)
            
            # Add period analysis
            history_context['period_analysis'] = {
                'net_change': history_context['total_incoming'] - history_context['total_outgoing'],
                'transaction_frequency': len(transactions),
                'most_common_type': self._get_most_common_transaction_type(transactions)
            }
            
            # Save comprehensive context for AI
            await self.memory.save_message(
                user_id=user_id,
                message="[HISTORY_CONTEXT_DETAILED]",
                role="system",
                metadata={
                    'type': 'history_context',
                    'context': history_context,
                    'stored_for': 'ai_reference',
                    'context_version': '2.0'
                }
            )
            
            logger.debug(f"Stored detailed history context for user {user_id}")
            
        except Exception as e:
            logger.error(f"Failed to store detailed history context: {e}")
    
    async def _generate_smart_history_response(self, user_id: str, transactions: List[Dict], 
                                             time_filter: str, original_message: str) -> Optional[str]:
        """Generate AI-powered history response with smart context."""
        try:
            # Get conversation context
            context = await self.memory.get_smart_conversation_context(user_id, original_message)
            
            # Prepare transaction summary for AI
            tx_summary = []
            total_in = 0
            total_out = 0
            
            for tx in transactions[:5]:  # Limit to top 5 for AI processing
                amount = tx.get('amount', 0) / 100
                channel = tx.get('channel', 'transfer')
                status = tx.get('status', 'success')
                date = tx.get('created_at', '')[:10] if tx.get('created_at') else ''
                
                if channel in ['dedicated_nuban', 'bank_transfer']:
                    total_in += amount
                else:
                    total_out += amount
                
                tx_summary.append({
                    'amount': amount,
                    'type': channel,
                    'date': date,
                    'status': status
                })
            
            # Build AI prompt using safe JSON serialization
            from app.utils.response_utils import ResponseFormatter
            formatter = ResponseFormatter()
            
            period_text = self._get_period_text(time_filter)
            system_prompt = f"""You are TizBot, a smart and conversational Nigerian banking assistant. Present transaction history in a natural, conversational way.

🤖 **YOUR PERSONALITY:**
- Name: TizBot - friendly, smart, conversational
- Use Nigerian expressions naturally
- Be helpful and engaging
- Sound like a smart friend, not a robot

Transaction Summary ({period_text}):
- Total transactions: {len(transactions)}
- Money received: ₦{total_in:,.2f}
- Money sent: ₦{total_out:,.2f}
- Net change: ₦{total_in - total_out:,.2f}

Recent transactions:
{formatter.safe_json_dumps(tx_summary, indent=2)}

Conversation context:
{formatter.safe_json_dumps(context, indent=2)}

Guidelines:
- Be conversational and friendly
- Highlight interesting patterns or notable transactions
- Keep response under 4 sentences
- Use emojis appropriately
- Reference specific amounts and dates naturally

Example: "📊 Your transaction history for this week shows ₦4,000 came in on July 8th from a dedicated NUBAN transfer, and you sent ₦1,500 total. Looking good with a net gain of ₦2,500!"
"""
            
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Show me my transaction history {time_filter}"}
            ]
            
            completion = await self.ai_client.chat.completions.create(
                model=self.ai_model,
                messages=messages,
                max_tokens=200,
                temperature=0.7
            )
            
            response = cast(str, completion.choices[0].message.content)
            if response and response.strip():
                return response.strip()
                
        except Exception as e:
            logger.error(f"Smart history response failed: {e}")
        
        return None
    
    def _get_most_common_transaction_type(self, transactions: List[Dict]) -> str:
        """Get the most common transaction type."""
        type_counts: Dict[str, int] = {}
        for tx in transactions:
            tx_type = tx.get('channel', 'unknown')
            type_counts[tx_type] = type_counts.get(tx_type, 0) + 1
        
        if not type_counts:
            return 'none'
        
        return max(type_counts, key=lambda k: type_counts[k])

    async def handle_transfers_sent_request(self, user_id: str, message: str, entities: Optional[Dict] = None) -> str:
        """Handle transfers sent requests with comprehensive time filtering and analytics."""
        try:
            logger.info(f"Processing transfers sent request for user {user_id}")
            
            # Parse time filter from message
            from_date, to_date, period_text = self.parse_time_filter(message)
            
            # Get transfers from Paystack API with time filtering
            if from_date and to_date:
                transfers_response = await self.paystack.list_transfers(
                    per_page=50,
                    from_date=from_date,
                    to_date=to_date
                )
            else:
                transfers_response = await self.paystack.list_transfers(per_page=50)
            
            if not transfers_response or not transfers_response.get('status'):
                return "❌ Could not fetch your transfer history right now. Please try again."
            
            transfers = transfers_response.get('data', [])
            
            # Get current balance for context
            balance_response = await self.paystack.get_balance()
            current_balance = 0
            if balance_response and isinstance(balance_response, list):
                for balance_info in balance_response:
                    if balance_info.get('currency') == 'NGN':
                        current_balance = balance_info.get('balance', 0) / 100
                        break
            
            if not transfers:
                return f"""📤 **Transfers Sent ({period_text})**

No transfers found for this period.

💰 **Current Balance**: ₦{current_balance:,.2f}

You can send money by typing: "Send 5000 to 1234567890 GTBank" """
            
            # Calculate analytics
            total_sent = sum(tf.get('amount', 0) for tf in transfers) / 100
            successful_transfers = [tf for tf in transfers if tf.get('status') == 'success']
            pending_transfers = [tf for tf in transfers if tf.get('status') == 'pending']
            failed_transfers = [tf for tf in transfers if tf.get('status') == 'failed']
            
            # Build comprehensive response
            response = f"""📤 **Transfers Sent ({period_text})**

**Summary:**
• Total sent: ₦{total_sent:,.2f}
• Successful: {len(successful_transfers)} transfers
• Pending: {len(pending_transfers)} transfers
• Failed: {len(failed_transfers)} transfers
• Current balance: ₦{current_balance:,.2f}

**Recent Transfers:**"""
            
            # Show recent transfers
            for i, transfer in enumerate(transfers[:5]):
                amount = transfer.get('amount', 0) / 100
                status = transfer.get('status', 'unknown')
                
                # Get recipient name
                recipient = transfer.get('recipient', {})
                if isinstance(recipient, dict):
                    recipient_name = recipient.get('name', 'Unknown')
                else:
                    recipient_name = str(recipient)
                
                # Get date
                date_str = transfer.get('createdAt', transfer.get('created_at', ''))
                date = date_str[:10] if date_str else 'N/A'
                
                # Status emoji
                status_emoji = "✅" if status == "success" else "⏳" if status == "pending" else "❌"
                
                response += f"\n{i+1}. {status_emoji} ₦{amount:,.2f} to {recipient_name} - {date}"
            
            if len(transfers) > 5:
                response += f"\n... and {len(transfers) - 5} more transfers"
            
            return response
            
        except Exception as e:
            logger.error(f"Transfers sent request failed: {e}")
            return "❌ Error retrieving transfer history. Please try again."

    async def _explain_transactions_with_ai(self, user_id: str, message: str, transaction_data: Dict) -> str:
        """Explain transactions using AI to generate human-like responses."""
        try:
            if not self.ai_enabled or not self.ai_client:
                return self._create_human_transaction_fallback_response(transaction_data)
            
            logger.info(f"Generating AI explanation for transactions for user {user_id}")
            
            # Get conversation context for better AI responses
            context = await self.memory.get_smart_conversation_context(user_id, message)
            
            # Prepare transaction data for AI
            transactions = transaction_data.get('transactions', [])
            transaction_count = transaction_data.get('transaction_count', 0)
            period = transaction_data.get('period', 'recently')
            current_balance = transaction_data.get('current_balance', 0)
            
            # Calculate totals and prepare summary
            total_received = 0
            transaction_summary = []
            
            for tx in transactions[:5]:  # Show recent 5 transactions
                amount = tx.get('amount', 0) / 100
                total_received += amount
                channel = tx.get('channel', 'transfer')
                date = tx.get('created_at', '')[:10] if tx.get('created_at') else 'recently'
                status = tx.get('status', 'success')
                
                transaction_summary.append({
                    'amount': amount,
                    'type': channel,
                    'date': date,
                    'status': status
                })
            
            # Create AI prompt for natural conversation
            system_prompt = f"""You are a friendly Nigerian banking assistant explaining transaction history to a user in a natural, conversational way.

Transaction Summary ({period}):
- Total transactions: {transaction_count}
- Total money received: ₦{total_received:,.2f}
- Current balance: ₦{current_balance:,.2f}

Recent transactions: {transaction_summary}

IMPORTANT GUIDELINES:
- Speak like a helpful Nigerian friend, not a formal banker
- Use natural Nigerian English and expressions 
- Keep responses conversational and brief (2-3 sentences max)
- Don't use technical jargon, emojis, or formal headers
- Focus on what matters most to the user
- Make it sound like you're explaining to a friend over WhatsApp
- Be encouraging and positive about their financial activity

Examples of GOOD responses:
- "You received ₦4,000 this week from a dedicated NUBAN transfer. Looking good with your balance at ₦31k!"
- "So you got ₦130 total from 4 transactions recently. Your balance is sitting at ₦31,440 now - not bad!"
- "This week you received ₦4k from transfers. Your account is looking good at ₦31,440!"

Examples of BAD responses:
- "📊 Transaction History (All Time) Summary: • Total transactions: 4..."
- "Your comprehensive transaction analysis shows..."
- "Based on your transaction data, you have received..."

Be natural, friendly, and conversational!"""

            user_prompt = f"The user asked: '{message}' - explain their transaction history in a natural, friendly way."
            
            # Generate AI response
            completion = await self.ai_client.chat.completions.create(
                model=self.ai_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                max_tokens=200,
                temperature=0.8  # More creative for natural conversation
            )
            
            response = cast(str, completion.choices[0].message.content)
            if response and response.strip():
                return response.strip()
                
            # Fallback if AI response is empty
            return self._create_human_transaction_fallback_response(transaction_data)
            
        except Exception as e:
            logger.error(f"AI transaction explanation failed: {e}")
            return self._create_human_transaction_fallback_response(transaction_data)

    def _create_human_transaction_fallback_response(self, transaction_data: Dict) -> str:
        """Create human-like fallback response for transaction history."""
        try:
            transaction_count = transaction_data.get('transaction_count', 0)
            transactions = transaction_data.get('transactions', [])
            period = transaction_data.get('period', 'recently')
            current_balance = transaction_data.get('current_balance', 0)
            
            if transaction_count == 0:
                return f"No transactions found {period}. Your balance is ₦{current_balance:,.2f}."
            
            # Calculate total received
            total_received = sum(tx.get('amount', 0) for tx in transactions) / 100
            
            # Human-like fallback responses
            if transaction_count == 1:
                return f"You received ₦{total_received:,.0f} from 1 transaction {period}. Your balance is ₦{current_balance:,.2f}."
            elif transaction_count <= 5:
                return f"You got ₦{total_received:,.0f} from {transaction_count} transactions {period}. Balance is ₦{current_balance:,.2f} now!"
            else:
                return f"You received ₦{total_received:,.0f} from {transaction_count} transactions {period}. Your account is sitting at ₦{current_balance:,.2f}!"
                
        except Exception as e:
            logger.error(f"Failed to create human transaction fallback response: {e}")
            return "Your transaction history has been retrieved successfully!"

    def _create_transaction_fallback_response(self, transaction_data: Dict) -> str:
        """Create fallback response for transaction history."""
        try:
            transaction_count = transaction_data.get('transaction_count', 0)
            transactions = transaction_data.get('transactions', [])
            period = transaction_data.get('period', 'recently')
            
            if transaction_count == 0:
                return f"📊 **Transaction History**\n\nNo transactions found {period}."
            
            # Calculate totals
            total_amount = sum(tx.get('amount', 0) for tx in transactions) / 100
            
            return f"""📊 **Transaction History ({period})**

**Summary:**
• Total transactions: {transaction_count}
• Total amount: ₦{total_amount:,.2f}

Your transaction history has been retrieved successfully!"""
            
        except Exception as e:
            logger.error(f"Failed to create transaction fallback response: {e}")
            return "📊 **Transaction History**\n\nYour transaction history has been retrieved."

    def _extract_time_filter(self, message: str) -> tuple:
        """Extract time filter from message with comprehensive date parsing."""
        try:
            logger.info(f"Extracting time filter from message: {message}")
            
            # Use the existing comprehensive parse_time_filter method
            return self.parse_time_filter(message)
            
        except Exception as e:
            logger.error(f"Time filter extraction failed: {e}")
            return None, None, "recently"

    def _filter_transactions_by_time(self, transactions: List[Dict], from_date: str, to_date: str) -> List[Dict]:
        """Filter transactions by time period with proper date parsing."""
        try:
            logger.info(f"Filtering transactions by time: {from_date} to {to_date}")
            
            # If no date filter provided, return all transactions
            if not from_date or not to_date:
                return transactions
            
            filtered_transactions = []
            
            # Parse filter dates
            from_dt = datetime.strptime(from_date, "%Y-%m-%d").date()
            to_dt = datetime.strptime(to_date, "%Y-%m-%d").date()
            
            for tx in transactions:
                tx_date_str = tx.get('created_at', '')
                if not tx_date_str:
                    continue
                
                try:
                    # Parse transaction date (format: 2024-01-15T10:30:00.000Z)
                    if 'T' in tx_date_str:
                        tx_date = datetime.fromisoformat(tx_date_str.replace('Z', '+00:00')).date()
                    else:
                        tx_date = datetime.strptime(tx_date_str[:10], "%Y-%m-%d").date()
                    
                    # Check if transaction date falls within filter range
                    if from_dt <= tx_date <= to_dt:
                        filtered_transactions.append(tx)
                        
                except (ValueError, IndexError) as date_error:
                    logger.warning(f"Could not parse transaction date '{tx_date_str}': {date_error}")
                    # Include transactions with unparseable dates to be safe
                    filtered_transactions.append(tx)
            
            logger.info(f"Filtered {len(transactions)} transactions to {len(filtered_transactions)} for period {from_date} to {to_date}")
            return filtered_transactions
            
        except Exception as e:
            logger.error(f"Transaction time filtering failed: {e}")
            return transactions

    def _get_period_text(self, time_filter: str) -> str:
        """Get period text description."""
        try:
            # TODO: Implement period text logic
            # This is a stub implementation to fix the missing method error
            if not time_filter:
                return "All Time"
            
            return time_filter.replace('_', ' ').title()
            
        except Exception as e:
            logger.error(f"Period text generation failed: {e}")
            return "Recently"

    async def _format_transaction_history(self, transactions: List[Dict], time_filter: str) -> str:
        """Format transaction history for display."""
        try:
            if not transactions:
                return f"📊 **Transaction History**\n\nNo transactions found for the specified period."
            
            period_text = self._get_period_text(time_filter)
            total_amount = sum(tx.get('amount', 0) for tx in transactions) / 100
            
            # Build formatted response
            response = f"📊 **Transaction History ({period_text})**\n\n"
            response += f"**Summary:**\n"
            response += f"• Total transactions: {len(transactions)}\n"
            response += f"• Total amount: ₦{total_amount:,.2f}\n\n"
            
            # Show recent transactions
            response += "**Recent Transactions:**\n"
            for i, tx in enumerate(transactions[:5]):  # Show top 5
                amount = tx.get('amount', 0) / 100
                status = tx.get('status', 'unknown')
                date = tx.get('created_at', '')[:10] if tx.get('created_at') else 'N/A'
                response += f"{i+1}. ₦{amount:,.2f} - {status} - {date}\n"
            
            if len(transactions) > 5:
                response += f"... and {len(transactions) - 5} more transactions\n"
            
            return response
            
        except Exception as e:
            logger.error(f"Transaction history formatting failed: {e}")
            return "📊 **Transaction History**\n\nYour transaction history has been retrieved." 

    async def handle_people_sent_money_request(self, user_id: str, message: str, send_follow_up_callback) -> str:
        """Handle 'who are the people i sent money to' requests with ONLY real data - no AI generation of fake information."""
        try:
            # Immediate response
            immediate_response = "Let me check who you've sent money to recently... 🔍"
            
            # Start background processing for actual data
            asyncio.create_task(self._process_people_sent_money_background(user_id, message, send_follow_up_callback))
            
            return immediate_response
            
        except Exception as e:
            logger.error(f"Failed to start people sent money request: {e}")
            return "Sorry, I couldn't check your transfer history right now. Please try again."
    
    async def _process_people_sent_money_background(self, user_id: str, message: str, send_follow_up_callback):
        """Process 'people sent money to' request with combined database and API data."""
        try:
            logger.info(f"🔄 Processing 'people sent money to' request for user {user_id}")
            
            # Get transfers from BOTH sources - Database (recent) and API (comprehensive)
            database_transfers = []
            api_transfers = []
            
            # 1. Get saved transfers from database (includes recipient details)
            if self.memory and hasattr(self.memory, 'get_transfer_history'):
                try:
                    database_transfers = await self.memory.get_transfer_history(user_id, limit=20)
                    logger.info(f"Retrieved {len(database_transfers)} transfers from database")
                except Exception as db_error:
                    logger.warning(f"Database transfer retrieval failed: {db_error}")
            
            # 2. Get transfers from Paystack API
            try:
                transfers_response = await self.paystack.list_transfers(per_page=20)
                if transfers_response and transfers_response.get('status'):
                    api_transfers = transfers_response.get('data', [])
                    logger.info(f"Retrieved {len(api_transfers)} transfers from Paystack API")
            except Exception as api_error:
                logger.warning(f"API transfer retrieval failed: {api_error}")
            
            # Combine and deduplicate transfers
            all_transfers = self._combine_transfer_sources(database_transfers, api_transfers)
            
            if not all_transfers:
                await send_follow_up_callback(user_id, "You haven't sent money to anyone yet through this platform.")
                return
            
            # Group transfers by recipient for consolidation
            recipients_data = {}
            
            for transfer in all_transfers:
                # Extract recipient name properly from different formats
                recipient_name = self._extract_recipient_name(transfer)
                bank_name = self._extract_bank_name(transfer)
                
                # Skip invalid entries
                if not recipient_name or recipient_name.lower() in ['unknown', 'none', '']:
                    continue
                
                # Clean and normalize names
                recipient_name = self._clean_recipient_name(recipient_name)
                bank_name = self._clean_bank_name(bank_name)
                
                # Create unique key - prioritize name over bank to avoid duplicates
                # Same person should be consolidated regardless of bank info availability
                recipient_key = recipient_name.lower().strip()
                
                # If this is a completely new recipient, store bank info
                # If recipient exists but with different bank, prefer the one with real bank info
                if recipient_key not in recipients_data:
                    # New recipient
                    pass
                elif bank_name != 'Unknown Bank' and recipients_data[recipient_key]['bank'] == 'Unknown Bank':
                    # Update existing recipient with better bank info
                    recipients_data[recipient_key]['bank'] = bank_name
                elif bank_name == 'Unknown Bank' and recipients_data[recipient_key]['bank'] != 'Unknown Bank':
                    # Keep existing better bank info
                    bank_name = recipients_data[recipient_key]['bank']
                
                # Get transfer details
                amount = transfer.get('amount', 0) / 100
                date_str = transfer.get('createdAt', transfer.get('created_at', transfer.get('timestamp', '')))
                
                # Initialize or update recipient data
                if recipient_key not in recipients_data:
                    recipients_data[recipient_key] = {
                        'name': recipient_name,
                        'bank': bank_name,
                        'total_amount': amount,
                        'transfer_count': 1,
                        'last_date': date_str,
                        'last_amount': amount
                    }
                else:
                    # Update with most recent transfer
                    recipients_data[recipient_key]['total_amount'] += amount
                    recipients_data[recipient_key]['transfer_count'] += 1
                    
                    # Keep most recent transfer details
                    if date_str > recipients_data[recipient_key]['last_date']:
                        recipients_data[recipient_key]['last_date'] = date_str
                        recipients_data[recipient_key]['last_amount'] = amount
            
            if not recipients_data:
                await send_follow_up_callback(user_id, "You haven't sent money to anyone yet through this platform.")
                return
            
            # Sort recipients by most recent transfer date
            sorted_recipients = sorted(
                recipients_data.items(),
                key=lambda x: x[1]['last_date'],
                reverse=True
            )
            
            # Build clean response
            response = "💸 *People you've sent money to:*\n\n"
            
            for i, (_, data) in enumerate(sorted_recipients[:10], 1):  # Limit to 10
                name = data['name']
                bank = data['bank']
                total_amount = data['total_amount']
                transfer_count = data['transfer_count']
                last_amount = data['last_amount']
                last_date = data['last_date'][:10] if data['last_date'] else 'Unknown date'
                
                # Format bank name for display
                bank_display = bank if bank != 'Unknown Bank' else ''
                bank_text = f" ({bank_display})" if bank_display else ""
                
                # Format transfer count
                count_text = f" ({transfer_count} transfers)" if transfer_count > 1 else ""
                
                response += f"{i}. *{name}*{bank_text}\n"
                
                if transfer_count > 1:
                    response += f"   • Total sent: ₦{total_amount:,.2f}{count_text}\n"
                    response += f"   • Last sent: ₦{last_amount:,.2f} on {last_date}\n\n"
                else:
                    response += f"   • Sent: ₦{total_amount:,.2f} on {last_date}\n\n"
            
            # Add summary if there are more recipients
            total_recipients = len(recipients_data)
            if total_recipients > 10:
                response += f"... and {total_recipients - 10} more recipients.\n\n"
            
            # Add overall summary
            total_transfers = len(all_transfers)
            total_amount = sum(data['total_amount'] for data in recipients_data.values())
            response += f"📊 *Summary:* {total_recipients} recipients, {total_transfers} transfers, ₦{total_amount:,.2f} total sent"
            
            await send_follow_up_callback(user_id, response)
            logger.info(f"✅ 'People sent money to' processing completed for user {user_id}")
            
        except Exception as e:
            logger.error(f"'People sent money to' processing failed: {e}")
            await send_follow_up_callback(user_id, "Something went wrong while checking your transfer history. Please try again.")
    
    def _combine_transfer_sources(self, database_transfers: List[Dict], api_transfers: List[Dict]) -> List[Dict]:
        """Combine and deduplicate transfers from database and API sources."""
        try:
            combined_transfers = []
            seen_references = set()
            
            # Prioritize database transfers (they have better recipient details)
            for db_transfer in database_transfers:
                reference = db_transfer.get('reference', '')
                if reference and reference not in seen_references:
                    seen_references.add(reference)
                    # Standardize database transfer format
                    standardized_transfer = {
                        'amount': db_transfer.get('amount', 0) * 100,  # Convert to kobo for consistency
                        'recipient': {
                            'name': db_transfer.get('recipient', 'Unknown'),
                            'details': {
                                'bank_name': db_transfer.get('bank_name', 'Unknown Bank'),
                                'account_number': db_transfer.get('account_number', '')
                            }
                        },
                        'status': db_transfer.get('status', 'unknown'),
                        'createdAt': db_transfer.get('timestamp', ''),
                        'reference': reference,
                        'source': 'database'
                    }
                    combined_transfers.append(standardized_transfer)
            
            # Add API transfers that aren't already in database
            for api_transfer in api_transfers:
                reference = api_transfer.get('reference', '')
                if reference and reference not in seen_references:
                    seen_references.add(reference)
                    # API transfers are already in the right format
                    api_transfer['source'] = 'api'
                    combined_transfers.append(api_transfer)
            
            # Sort by date (newest first)
            combined_transfers.sort(
                key=lambda x: x.get('createdAt', x.get('timestamp', '')), 
                reverse=True
            )
            
            logger.info(f"Combined {len(database_transfers)} database + {len(api_transfers)} API = {len(combined_transfers)} total transfers")
            return combined_transfers
            
        except Exception as e:
            logger.error(f"Failed to combine transfer sources: {e}")
            # Return API transfers as fallback
            return api_transfers
    
    def _combine_transaction_sources(self, database_transactions: List[Dict], api_transactions: List[Dict]) -> List[Dict]:
        """Combine and deduplicate transactions from database and API sources."""
        try:
            combined_transactions = []
            seen_references = set()
            
            # Prioritize database transactions (they might have additional context)
            for db_transaction in database_transactions:
                reference = db_transaction.get('reference', '')
                if reference and reference not in seen_references:
                    seen_references.add(reference)
                    # Database transactions are already in compatible format
                    db_transaction['source'] = 'database'
                    combined_transactions.append(db_transaction)
            
            # Add API transactions that aren't already in database
            for api_transaction in api_transactions:
                reference = api_transaction.get('reference', '')
                if reference and reference not in seen_references:
                    seen_references.add(reference)
                    # API transactions are already in the right format
                    api_transaction['source'] = 'api'
                    combined_transactions.append(api_transaction)
            
            # Sort by date (newest first)
            combined_transactions.sort(
                key=lambda x: x.get('created_at', x.get('timestamp', '')), 
                reverse=True
            )
            
            logger.info(f"Combined {len(database_transactions)} database + {len(api_transactions)} API = {len(combined_transactions)} total transactions")
            return combined_transactions
            
        except Exception as e:
            logger.error(f"Failed to combine transaction sources: {e}")
            # Return API transactions as fallback
            return api_transactions
    
    async def _save_transactions_to_database(self, user_id: str, transactions: List[Dict]):
        """Save API transactions to database for future reference."""
        try:
            if not self.memory or not hasattr(self.memory, 'save_transaction'):
                return
            
            saved_count = 0
            for transaction in transactions:
                try:
                    # Only save if transaction has required fields
                    if transaction.get('reference') and transaction.get('amount'):
                        success = await self.memory.save_transaction(user_id, transaction)
                        if success:
                            saved_count += 1
                except Exception as save_error:
                    logger.warning(f"Failed to save individual transaction: {save_error}")
            
            if saved_count > 0:
                logger.info(f"Saved {saved_count} new transactions to database for user {user_id}")
                
        except Exception as e:
            logger.error(f"Failed to save transactions to database: {e}")
    
    def _extract_recipient_name(self, transfer: Dict) -> str:
        """Extract recipient name from transfer data, handling multiple formats."""
        try:
            recipient_info = transfer.get('recipient', {})
            
            # Case 1: Standard recipient dict format
            if isinstance(recipient_info, dict):
                name = recipient_info.get('name')
                if name and isinstance(name, str):
                    return name
            
            # Case 2: String recipient (fallback from database)
            elif isinstance(recipient_info, str):
                # Check if it's a serialized dict string
                if recipient_info.startswith('{') and recipient_info.endswith('}'):
                    try:
                        import ast
                        parsed = ast.literal_eval(recipient_info)
                        if isinstance(parsed, dict):
                            return parsed.get('account_name', 'Unknown')
                    except:
                        pass
                return recipient_info
            
            # Case 3: Check direct fields in transfer (database format)
            direct_name = transfer.get('recipient')
            if direct_name and isinstance(direct_name, str) and not direct_name.startswith('{'):
                return direct_name
            
            # Case 4: Try Paystack API format
            if 'details' in recipient_info:
                api_name = recipient_info['details'].get('account_name')
                if api_name:
                    return api_name
            
            return 'Unknown'
            
        except Exception as e:
            logger.warning(f"Failed to extract recipient name: {e}")
            return 'Unknown'
    
    def _extract_bank_name(self, transfer: Dict) -> str:
        """Extract bank name from transfer data, handling multiple formats."""
        try:
            recipient_info = transfer.get('recipient', {})
            
            # Case 1: Database format - direct bank_name field
            bank_name = transfer.get('bank_name')
            if bank_name and isinstance(bank_name, str):
                return bank_name
            
            # Case 2: Nested in recipient details
            if isinstance(recipient_info, dict):
                details = recipient_info.get('details', {})
                if isinstance(details, dict):
                    bank_name = details.get('bank_name')
                    if bank_name:
                        return bank_name
            
            # Case 3: Paystack API format
            if isinstance(recipient_info, dict) and 'details' in recipient_info:
                bank_info = recipient_info['details'].get('bank_name')
                if bank_info:
                    return bank_info
            
            # Case 4: Check if recipient is a serialized dict with bank info
            if isinstance(recipient_info, str) and recipient_info.startswith('{'):
                try:
                    import ast
                    parsed = ast.literal_eval(recipient_info)
                    if isinstance(parsed, dict):
                        return parsed.get('bank_name', 'Unknown Bank')
                except:
                    pass
            
            return 'Unknown Bank'
            
        except Exception as e:
            logger.warning(f"Failed to extract bank name: {e}")
            return 'Unknown Bank'
    
    def _clean_recipient_name(self, name: str) -> str:
        """Clean and normalize recipient name for display."""
        if not name or name.lower() in ['unknown', 'none', '']:
            return 'Unknown'
        
        # Handle serialized dicts that slipped through
        if name.startswith('{') and name.endswith('}'):
            try:
                import ast
                parsed = ast.literal_eval(name)
                if isinstance(parsed, dict):
                    return parsed.get('account_name', 'Unknown')
            except:
                pass
        
        # Clean up the name
        name = name.strip()
        
        # Remove POS Transfer prefix if present
        if name.startswith('POS Transfer - '):
            name = name.replace('POS Transfer - ', '')
        
        # Title case for better display
        name = name.title()
        
        return name
    
    def _clean_bank_name(self, bank: str) -> str:
        """Clean and normalize bank name for display."""
        from app.utils.bank_resolver import BankResolver
        return BankResolver.clean_bank_name(bank) 