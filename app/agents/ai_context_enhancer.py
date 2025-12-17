#!/usr/bin/env python3
"""
AI Context Enhancer for PayStack WhatsApp Agent
Enhances AI responses by storing and retrieving transaction context.
"""

import asyncio
from typing import Dict, List, Optional, Any
from datetime import datetime
import json
from app.utils.logger import get_logger
from app.utils.memory_manager import MemoryManager

logger = get_logger("ai_context_enhancer")

class AIContextEnhancer:
    """Enhances AI responses with transaction context awareness."""
    
    def __init__(self, memory_manager: MemoryManager):
        self.memory = memory_manager
    
    async def store_transaction_context(self, user_id: str, balance_data: Dict, transaction_data: List[Dict]):
        """Store transaction context for future AI reference."""
        try:
            # Create comprehensive transaction context
            context: Dict[str, Any] = {
                'timestamp': datetime.now().isoformat(),
                'balance_info': {
                    'current_balance': balance_data.get('current_balance', 0),
                    'recent_activity': balance_data.get('recent_activity', 0)
                },
                'transactions': []
            }
            
            # Store detailed transaction info
            transactions_list = []
            for tx in transaction_data:
                tx_info = {
                    'amount': tx.get('amount', 0) / 100 if tx.get('amount') else 0,
                    'type': tx.get('channel', 'transfer'),
                    'status': tx.get('status', 'unknown'),
                    'date': tx.get('created_at', ''),
                    'reference': tx.get('reference', ''),
                    'description': self._get_transaction_description(tx)
                }
                transactions_list.append(tx_info)
            
            context['transactions'] = transactions_list
            
            # Store the context as metadata
            await self.memory.save_message(
                user_id=user_id,
                message="[AI_CONTEXT]",
                role="system",
                metadata={
                    'type': 'transaction_context',
                    'context': context
                }
            )
            
            logger.debug(f"Stored transaction context for user {user_id}")
            
        except Exception as e:
            logger.error(f"Failed to store transaction context: {e}")
    
    async def get_transaction_context_for_query(self, user_id: str, user_message: str) -> Optional[str]:
        """Get relevant transaction context for a user's query."""
        try:
            # Get recent conversation history
            conversation_history = await self.memory.get_conversation_history(user_id, limit=10)
            
            # Find the most recent transaction context
            transaction_context = None
            for msg in conversation_history:
                if (msg.get("role") == "system" and 
                    msg.get("message") == "[AI_CONTEXT]" and
                    msg.get("metadata", {}).get("type") == "transaction_context"):
                    
                    transaction_context = msg.get("metadata", {}).get("context", {})
                    break
            
            if not transaction_context:
                return None
            
            # Parse user message to find what they're asking about
            message_lower = user_message.lower()
            
            # Check for specific amount inquiries
            if "4k" in message_lower or "4000" in message_lower:
                return self._find_transaction_by_amount(transaction_context, 4000)
            
            if "5k" in message_lower or "5000" in message_lower:
                return self._find_transaction_by_amount(transaction_context, 5000)
            
            if "3k" in message_lower or "3000" in message_lower:
                return self._find_transaction_by_amount(transaction_context, 3000)
            
            # Check for general transaction inquiries
            if any(word in message_lower for word in ["transaction", "what", "which", "money"]):
                return self._get_recent_transaction_summary(transaction_context)
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get transaction context: {e}")
            return None
    
    def _find_transaction_by_amount(self, context: Dict, target_amount: float) -> Optional[str]:
        """Find transaction by amount with some tolerance."""
        try:
            transactions = context.get('transactions', [])
            
            for tx in transactions:
                tx_amount = tx.get('amount', 0)
                # Allow 10% tolerance for amount matching
                if abs(tx_amount - target_amount) <= (target_amount * 0.1):
                    date_str = tx.get('date', '')[:10] if tx.get('date') else 'recently'
                    return f"That ₦{tx_amount:,.0f} transaction was a {tx['type']} that came in on {date_str} - {tx['description']}"
            
            # If no exact match, return general info
            if transactions:
                latest_tx = transactions[0]
                return f"I mentioned recent transactions, but let me clarify: your latest transaction was ₦{latest_tx['amount']:,.0f} via {latest_tx['type']}"
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to find transaction by amount: {e}")
            return None
    
    def _get_recent_transaction_summary(self, context: Dict) -> str:
        """Get a summary of recent transactions."""
        try:
            transactions = context.get('transactions', [])
            
            if not transactions:
                return "I don't have recent transaction data available right now."
            
            # Get the most recent transaction
            latest_tx = transactions[0]
            date_str = latest_tx.get('date', '')[:10] if latest_tx.get('date') else 'recently'
            
            summary = f"Your most recent transaction was ₦{latest_tx['amount']:,.0f} via {latest_tx['type']} on {date_str}"
            
            # Add info about multiple transactions if available
            if len(transactions) > 1:
                summary += f". You've had {len(transactions)} transactions in the last few days."
            
            return summary
            
        except Exception as e:
            logger.error(f"Failed to get transaction summary: {e}")
            return "I mentioned your recent transactions, but I'm having trouble getting the details right now."
    
    def _get_transaction_description(self, tx: Dict) -> str:
        """Get a human-readable description of a transaction."""
        try:
            channel = tx.get('channel', 'transfer')
            status = tx.get('status', 'unknown')
            
            if channel == 'dedicated_nuban':
                return 'bank transfer to your dedicated account'
            elif channel == 'card':
                return 'card payment'
            elif channel == 'bank':
                return 'bank transfer'
            elif channel == 'transfer':
                return 'money transfer'
            else:
                return f'{channel} transaction'
                
        except Exception as e:
            logger.error(f"Failed to get transaction description: {e}")
            return 'transaction'
    
    async def enhance_ai_response(self, user_id: str, message: str, base_response: str) -> str:
        """Enhance AI response with transaction context if relevant."""
        try:
            # Check if user is asking about something specific
            if any(word in message.lower() for word in ["what", "which", "transaction", "4k", "5k", "3k"]):
                context_info = await self.get_transaction_context_for_query(user_id, message)
                
                if context_info:
                    # Replace generic responses with context-aware ones
                    if "I'm listening" in base_response or "How can I assist" in base_response:
                        return context_info
                    
                    # Append context to existing response
                    return f"{context_info}"
            
            return base_response
            
        except Exception as e:
            logger.error(f"Failed to enhance AI response: {e}")
            return base_response 