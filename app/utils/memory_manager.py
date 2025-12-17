#!/usr/bin/env python3
"""
Memory Manager for LangGraph Agent
Manages conversation memory, recipient cache, and context using MongoDB Atlas.
"""

from typing import Dict, List, Optional, Any, cast
from datetime import datetime, timedelta
import json
from .logger import get_logger
from .mongodb_manager import mongodb_manager

logger = get_logger("memory_manager")


class MemoryManager:
    """Manages conversation memory and recipient cache using MongoDB Atlas."""
    
    def __init__(self):
        self.mongodb = mongodb_manager
        self.local_cache = {}  # Fallback in-memory cache if MongoDB is unavailable
    
    # Conversation Memory Management
    async def save_message(self, user_id: str, message: str, role: str = "user", 
                          metadata: Optional[Dict] = None) -> bool:
        """Save a conversation message to memory with enhanced context."""
        try:
            # Enhance metadata with context information
            enhanced_metadata = metadata or {}
            enhanced_metadata.update({
                'timestamp': datetime.utcnow().isoformat(),
                'context_enhanced': True
            })
            
            # Try MongoDB first
            if self.mongodb.is_connected():
                result = await self.mongodb.save_conversation(user_id, message, role, enhanced_metadata)
                if result:
                    logger.debug(f"Saved message to MongoDB for user {user_id}")
                    return True
            
            # Fallback to local cache
            if user_id not in self.local_cache:
                self.local_cache[user_id] = {"conversations": [], "recipients": []}
            
            conversation_entry = {
                "message": message,
                "role": role,
                "timestamp": datetime.utcnow(),
                "metadata": enhanced_metadata
            }
            
            self.local_cache[user_id]["conversations"].append(conversation_entry)
            
            # Keep only last 100 messages in local cache for better context
            if len(self.local_cache[user_id]["conversations"]) > 100:
                self.local_cache[user_id]["conversations"] = \
                    self.local_cache[user_id]["conversations"][-100:]
            
            logger.debug(f"Saved message to local cache for user {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save message: {e}")
            return False
    
    async def save_banking_operation_context(self, user_id: str, operation_type: str, 
                                           operation_data: Dict, api_response: Dict) -> bool:
        """Save banking operation context for AI reference."""
        try:
            # Create comprehensive banking context
            banking_context = {
                'operation_type': operation_type,
                'operation_data': operation_data,
                'api_response': api_response,
                'timestamp': datetime.utcnow().isoformat(),
                'success': api_response.get('success', True)
            }
            
            # Save as system message for AI context
            await self.save_message(
                user_id=user_id,
                message=f"[BANKING_OP:{operation_type}]",
                role="system",
                metadata={
                    'type': 'banking_operation',
                    'operation': operation_type,
                    'context': banking_context
                }
            )
            
            logger.debug(f"Saved banking operation context: {operation_type} for user {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save banking operation context: {e}")
            return False
    
    async def get_smart_conversation_context(self, user_id: str, current_query: str) -> Dict:
        """Get intelligent context for AI responses."""
        try:
            # Get recent conversation history
            conversations = await self.get_conversation_history(user_id, limit=10)
            
            # Extract banking operations
            banking_ops = []
            transaction_context = None
            
            for msg in conversations:
                metadata = msg.get('metadata', {})
                
                # Extract banking operations
                if metadata.get('type') == 'banking_operation':
                    banking_ops.append(metadata.get('context', {}))
                
                # Extract transaction context
                elif metadata.get('type') == 'transaction_context':
                    transaction_context = metadata.get('context', {})
            
            # Analyze current query
            query_analysis = self._analyze_query_for_context(current_query, conversations)
            
            return {
                'recent_conversations': conversations[-5:],  # Last 5 messages
                'banking_operations': banking_ops[-3:],      # Last 3 operations
                'transaction_context': transaction_context,
                'query_analysis': query_analysis
            }
            
        except Exception as e:
            logger.error(f"Failed to get smart conversation context: {e}")
            return {}
    
    def _analyze_query_for_context(self, query: str, conversations: List[Dict]) -> Dict:
        """Analyze query to understand what context is needed."""
        query_lower = query.lower()
        
        analysis: Dict[str, Any] = {
            'is_follow_up': False,
            'references_amount': None,  # Optional[str] - will contain the amount pattern if found
            'references_transaction': False,
            'needs_specific_details': False
        }
        
        # Check if it's a follow-up question
        follow_up_indicators = ['what', 'which', 'that', 'this', 'explain', 'tell me about']
        if any(indicator in query_lower for indicator in follow_up_indicators):
            analysis['is_follow_up'] = True
            analysis['needs_specific_details'] = True
        
        # Check for amount references
        amount_patterns = ['4k', '5k', '3k', '1k', '2k', 'thousand', 'naira', '₦']
        for pattern in amount_patterns:
            if pattern in query_lower:
                analysis['references_amount'] = pattern  # Store the actual pattern found
                analysis['references_transaction'] = True
                break
        
        # Check for transaction references
        transaction_words = ['transaction', 'transfer', 'payment', 'money', 'send', 'sent']
        if any(word in query_lower for word in transaction_words):
            analysis['references_transaction'] = True
        
        return analysis
    
    async def enhance_ai_response_with_context(self, user_id: str, query: str, base_response: str) -> str:
        """Enhance AI response with relevant context."""
        try:
            # Get smart context
            context = await self.get_smart_conversation_context(user_id, query)
            query_analysis = context.get('query_analysis', {})
            
            # If it's a follow-up question, provide specific context
            if query_analysis.get('is_follow_up') and query_analysis.get('references_transaction'):
                
                # Look for transaction references in recent conversations
                for conv in reversed(context.get('recent_conversations', [])):
                    if conv.get('role') == 'assistant':
                        message = conv.get('message', '')
                        
                        # If assistant mentioned an amount that user is asking about
                        if query_analysis.get('references_amount'):
                            amount_ref = query_analysis['references_amount']
                            if amount_ref in message.lower() or '₦' in message:
                                # Extract transaction details
                                transaction_context = context.get('transaction_context')
                                if transaction_context:
                                    # Find specific transaction
                                    for tx in transaction_context.get('recent_transactions', []):
                                        tx_amount = tx.get('amount', 0)
                                        if amount_ref == '4k' and abs(tx_amount - 4000) < 500:
                                            return f"That ₦{tx_amount:,.0f} transaction was a {tx.get('type', 'transfer')} that came in on {tx.get('date', '')[:10]} - it's what boosted your balance recently!"
                                        elif amount_ref == '5k' and abs(tx_amount - 5000) < 500:
                                            return f"The ₦{tx_amount:,.0f} transaction was a {tx.get('type', 'transfer')} from {tx.get('date', '')[:10]}."
                                
                                # Fallback if no specific transaction found
                                return f"I mentioned that amount based on your recent transaction activity. Would you like me to show you your detailed transaction history?"
            
            return base_response
            
        except Exception as e:
            logger.error(f"Failed to enhance AI response: {e}")
            return base_response
    
    async def get_conversation_history(self, user_id: str, limit: int = 20) -> List[Dict]:
        """Get conversation history for context."""
        try:
            # Try MongoDB first
            if self.mongodb.is_connected():
                history = await self.mongodb.get_conversation_history(user_id, limit)
                if history:
                    logger.debug(f"Retrieved {len(history)} messages from MongoDB for user {user_id}")
                    return cast(List[Dict[Any, Any]], history)
            
            # Fallback to local cache
            if user_id in self.local_cache and "conversations" in self.local_cache[user_id]:
                conversations = self.local_cache[user_id]["conversations"]
                limited_conversations = conversations[-limit:] if len(conversations) > limit else conversations
                logger.debug(f"Retrieved {len(limited_conversations)} messages from local cache for user {user_id}")
                return limited_conversations
            
            return []
            
        except Exception as e:
            logger.error(f"Failed to get conversation history: {e}")
            return []
    
    async def get_context_summary(self, user_id: str) -> str:
        """Get a summary of recent conversation context."""
        try:
            history = await self.get_conversation_history(user_id, 10)
            
            if not history:
                return "No previous conversation history."
            
            # Create context summary
            context_parts = []
            recent_messages = history[-5:]  # Last 5 messages
            
            for msg in recent_messages:
                role = msg.get("role", "user")
                message = msg.get("message", "")
                context_parts.append(f"{role.capitalize()}: {message}")
            
            context = "\n".join(context_parts)
            return f"Recent conversation:\n{context}"
            
        except Exception as e:
            logger.error(f"Failed to get context summary: {e}")
            return "Unable to retrieve conversation context."
    
    # Recipient Management
    async def save_recipient(self, user_id: str, recipient_data: Dict) -> bool:
        """Save a recipient for future use."""
        try:
            # Validate required fields
            required_fields = ["account_name", "account_number", "bank_name", "bank_code"]
            if not all(field in recipient_data for field in required_fields):
                logger.warning("Missing required recipient fields")
                return False
            
            # Try MongoDB first
            if self.mongodb.is_connected():
                result = await self.mongodb.save_recipient(user_id, recipient_data)
                if result:
                    logger.info(f"Saved recipient to MongoDB: {recipient_data['account_name']}")
                    return True
            
            # Fallback to local cache
            if user_id not in self.local_cache:
                self.local_cache[user_id] = {"conversations": [], "recipients": []}
            
            # Check if recipient already exists
            recipients = self.local_cache[user_id]["recipients"]
            for i, existing in enumerate(recipients):
                if existing["account_number"] == recipient_data["account_number"]:
                    recipients[i] = {**recipient_data, "last_used": datetime.utcnow()}
                    logger.info(f"Updated existing recipient in local cache: {recipient_data['account_name']}")
                    return True
            
            # Add new recipient
            recipient_data["last_used"] = datetime.utcnow()
            recipients.append(recipient_data)
            
            # Keep only last 20 recipients in local cache
            if len(recipients) > 20:
                self.local_cache[user_id]["recipients"] = recipients[-20:]
            
            logger.info(f"Saved new recipient to local cache: {recipient_data['account_name']}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save recipient: {e}")
            return False
    
    async def save_recipient_nickname(self, user_id: str, recipient_name: str, custom_nickname: str, recipient_data: Dict) -> bool:
        """Save a custom nickname for an existing recipient."""
        try:
            # Try MongoDB first
            if self.mongodb.is_connected():
                result = await self.mongodb.save_recipient_nickname(
                    user_id, recipient_name, custom_nickname, recipient_data
                )
                if result:
                    logger.info(f"Saved custom nickname '{custom_nickname}' for {recipient_name} in MongoDB for user {user_id}")
                    return True
            
            # Fallback to local cache (in-memory storage)
            if user_id not in self.local_cache:
                self.local_cache[user_id] = {"conversations": [], "recipients": []}
            
            # Look for existing recipient and update with nickname
            updated = False
            for recipient in self.local_cache[user_id]["recipients"]:
                if (recipient.get('account_name', '').lower() == recipient_name.lower() or 
                    recipient.get('nickname', '').lower() == recipient_name.lower()):
                    
                    # Add custom nickname to existing recipient
                    recipient['custom_nicknames'] = recipient.get('custom_nicknames', [])
                    if custom_nickname not in recipient['custom_nicknames']:
                        recipient['custom_nicknames'].append(custom_nickname)
                    updated = True
                    break
            
            if updated:
                logger.info(f"Saved custom nickname '{custom_nickname}' for {recipient_name} in local cache for user {user_id}")
                return True
            else:
                logger.warning(f"Recipient {recipient_name} not found in cache to add nickname")
                return False
            
        except Exception as e:
            logger.error(f"Failed to save recipient nickname: {e}")
            return False
    
    async def get_recipients(self, user_id: str) -> List[Dict]:
        """Get saved recipients for a user."""
        try:
            # Try MongoDB first
            if self.mongodb.is_connected():
                recipients = await self.mongodb.get_recipients(user_id)
                if recipients:
                    logger.debug(f"Retrieved {len(recipients)} recipients from MongoDB for user {user_id}")
                    return cast(List[Dict[Any, Any]], recipients)
            
            # Fallback to local cache
            if user_id in self.local_cache and "recipients" in self.local_cache[user_id]:
                recipients = self.local_cache[user_id]["recipients"]
                logger.debug(f"Retrieved {len(recipients)} recipients from local cache for user {user_id}")
                return recipients
            
            return []
            
        except Exception as e:
            logger.error(f"Failed to get recipients: {e}")
            return []
    
    async def find_recipient(self, user_id: str, search_term: str) -> Optional[Dict]:
        """Find a recipient by name or account number."""
        try:
            # Try MongoDB first
            if self.mongodb.is_connected():
                recipient = await self.mongodb.find_recipient(user_id, search_term)
                if recipient:
                    logger.debug(f"Found recipient in MongoDB: {recipient['account_name']}")
                    return cast(Optional[Dict[Any, Any]], recipient)
            
            # Fallback to local cache
            if user_id in self.local_cache and "recipients" in self.local_cache[user_id]:
                recipients = self.local_cache[user_id]["recipients"]
                
                for recipient in recipients:
                    # Search by account name, nickname, or account number
                    if (search_term.lower() in recipient.get("account_name", "").lower() or
                        search_term.lower() in recipient.get("nickname", "").lower() or
                        search_term == recipient.get("account_number")):
                        
                        # Update last_used
                        recipient["last_used"] = datetime.utcnow()
                        
                        logger.debug(f"Found recipient in local cache: {recipient['account_name']}")
                        return cast(Optional[Dict[Any, Any]], recipient)
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to find recipient: {e}")
            return None
    
    # Transfer History
    async def save_transfer_record(self, user_id: str, transfer_data: Dict) -> bool:
        """Legacy method - redirect to save_transfer."""
        return await self.save_transfer(user_id, transfer_data)
    
    async def get_transfer_history(self, user_id: str, limit: int = 10) -> List[Dict]:
        """Get transfer history for a user."""
        try:
            # Try MongoDB first
            if self.mongodb.is_connected():
                transfers = await self.mongodb.get_transfer_history(user_id, limit)
                if transfers:
                    logger.debug(f"Retrieved {len(transfers)} transfers from MongoDB for user {user_id}")
                    return transfers
            
            # Fallback to local cache
            if user_id in self.local_cache and "transfers" in self.local_cache[user_id]:
                transfers = self.local_cache[user_id]["transfers"]
                # Sort by timestamp (newest first) and limit
                sorted_transfers = sorted(
                    transfers, 
                    key=lambda x: x.get('timestamp', ''), 
                    reverse=True
                )
                limited_transfers = sorted_transfers[:limit]
                logger.debug(f"Retrieved {len(limited_transfers)} transfers from local cache for user {user_id}")
                return limited_transfers
            
            return []
            
        except Exception as e:
            logger.error(f"Failed to get transfer history: {e}")
            return []

    async def update_transfer_status(self, user_id: str, transfer_reference: str, status: str) -> bool:
        """Update transfer status by reference."""
        try:
            # Try MongoDB first
            if self.mongodb.is_connected():
                result = await self.mongodb.update_transfer_status(user_id, transfer_reference, status)
                if result:
                    logger.info(f"Updated transfer status in MongoDB: {transfer_reference} -> {status}")
                    return True
            
            # Fallback to local cache
            if user_id in self.local_cache and "transfers" in self.local_cache[user_id]:
                transfers = self.local_cache[user_id]["transfers"]
                
                for transfer in transfers:
                    if transfer.get('reference') == transfer_reference:
                        transfer['status'] = status
                        transfer['updated_at'] = datetime.utcnow().isoformat()
                        logger.info(f"Updated transfer status in local cache: {transfer_reference} -> {status}")
                        return True
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to update transfer status: {e}")
            return False
    
    # Analytics and Insights
    def get_recipient_suggestions(self, user_id: str, query: str) -> List[str]:
        """Get recipient suggestions based on query."""
        try:
            recipients = []
            
            # Get from local cache if available
            if user_id in self.local_cache and "recipients" in self.local_cache[user_id]:
                cache_recipients = self.local_cache[user_id]["recipients"]
                for recipient in cache_recipients:
                    if query.lower() in recipient.get("account_name", "").lower():
                        recipients.append(recipient["account_name"])
            
            return recipients[:5]  # Top 5 suggestions
            
        except Exception as e:
            logger.error(f"Failed to get recipient suggestions: {e}")
            return []
    
    def get_memory_status(self) -> Dict[str, Any]:
        """Get memory manager status."""
        status = {
            "mongodb_connected": self.mongodb.is_connected(),
            "local_cache_users": len(self.local_cache),
            "timestamp": datetime.utcnow()
        }
        
        if self.mongodb.is_connected():
            status["storage_mode"] = "MongoDB Atlas"
        else:
            status["storage_mode"] = "Local Cache (Fallback)"
        
        return status
    
    async def clear_user_memory(self, user_id: str) -> bool:
        """Clear all memory for a user (for privacy/GDPR compliance)."""
        try:
            # Clear from local cache
            if user_id in self.local_cache:
                del self.local_cache[user_id]
            
            # For MongoDB, this would require additional implementation
            # to remove user data across collections
            logger.info(f"Cleared memory for user {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to clear user memory: {e}")
            return False

    # Conversation State Management (for multi-step workflows)
    async def set_conversation_state(self, user_id: str, state: Dict) -> bool:
        """Set conversation state for multi-step workflows."""
        try:
            # Try MongoDB first
            if self.mongodb.is_connected():
                result = await self.mongodb.set_conversation_state(user_id, state)
                if result:
                    logger.debug(f"Saved conversation state to MongoDB for user {user_id}")
                    return True
            
            # Fallback to local cache
            if user_id not in self.local_cache:
                self.local_cache[user_id] = {"conversations": [], "recipients": [], "state": None}
            
            self.local_cache[user_id]["state"] = {
                **state,
                "timestamp": datetime.utcnow()
            }
            
            logger.debug(f"Saved conversation state to local cache for user {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to set conversation state: {e}")
            return False
    
    async def get_conversation_state(self, user_id: str) -> Optional[Dict]:
        """Get current conversation state."""
        try:
            # Try MongoDB first
            if self.mongodb.is_connected():
                state = await self.mongodb.get_conversation_state(user_id)
                if state:
                    # Check if state is not too old (expire after 30 minutes)
                    if 'timestamp' in state:
                        state_time = state['timestamp']
                        if isinstance(state_time, str):
                            state_time = datetime.fromisoformat(state_time.replace('Z', '+00:00'))
                        
                        if datetime.utcnow() - state_time.replace(tzinfo=None) > timedelta(minutes=30):
                            await self.clear_conversation_state(user_id)
                            return None
                    
                    logger.debug(f"Retrieved conversation state from MongoDB for user {user_id}")
                    return cast(Optional[Dict[Any, Any]], state)
            
            # Fallback to local cache
            if user_id in self.local_cache and "state" in self.local_cache[user_id]:
                state = self.local_cache[user_id]["state"]
                
                if state and 'timestamp' in state:
                    # Check if state is not too old (expire after 30 minutes)
                    if datetime.utcnow() - state['timestamp'] > timedelta(minutes=30):
                        self.local_cache[user_id]["state"] = None
                        return None
                
                logger.debug(f"Retrieved conversation state from local cache for user {user_id}")
                return cast(Optional[Dict[Any, Any]], state)
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get conversation state: {e}")
            return None
    
    async def clear_conversation_state(self, user_id: str) -> bool:
        """Clear conversation state."""
        try:
            # Try MongoDB first
            if self.mongodb.is_connected():
                result = await self.mongodb.clear_conversation_state(user_id)
                if result:
                    logger.debug(f"Cleared conversation state from MongoDB for user {user_id}")
                    return True
            
            # Fallback to local cache
            if user_id in self.local_cache:
                self.local_cache[user_id]["state"] = None
                logger.debug(f"Cleared conversation state from local cache for user {user_id}")
                return True
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to clear conversation state: {e}")
            return False
    
    # Enhanced Transfer Management
    async def save_transfer(self, user_id: str, transfer_data: Dict) -> bool:
        """Save transfer record with enhanced data structure."""
        try:
            # Validate required fields
            required_fields = ["amount", "recipient", "status"]
            if not all(field in transfer_data for field in required_fields):
                logger.warning("Missing required transfer fields")
                return False
            
            # Add timestamp if not present
            if "timestamp" not in transfer_data:
                transfer_data["timestamp"] = datetime.utcnow().isoformat()
            
            # Try MongoDB first
            if self.mongodb.is_connected():
                result = await self.mongodb.save_transfer(user_id, transfer_data)
                if result:
                    logger.info(f"Saved transfer to MongoDB: ₦{transfer_data['amount']}")
                    return True
            
            # Fallback to local cache
            if user_id not in self.local_cache:
                self.local_cache[user_id] = {"conversations": [], "recipients": [], "transfers": []}
            
            if "transfers" not in self.local_cache[user_id]:
                self.local_cache[user_id]["transfers"] = []
            
            self.local_cache[user_id]["transfers"].append(transfer_data)
            
            # Keep only last 50 transfers in local cache
            if len(self.local_cache[user_id]["transfers"]) > 50:
                self.local_cache[user_id]["transfers"] = \
                    self.local_cache[user_id]["transfers"][-50:]
            
            logger.info(f"Saved transfer to local cache: ₦{transfer_data['amount']}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save transfer: {e}")
            return False
    
    async def save_receipt(self, user_id: str, reference: str, receipt_path: str, receipt_url: Optional[str] = None) -> bool:
        """Save receipt metadata for future lookup."""
        try:
            receipt_data = {
                "reference": reference,
                "receipt_path": receipt_path,
                "receipt_url": receipt_url,
                "timestamp": datetime.utcnow().isoformat(),
                "user_id": user_id
            }
            
            # Try MongoDB first
            if self.mongodb.is_connected():
                result = await self.mongodb.save_receipt(user_id, receipt_data)
                if result:
                    logger.info(f"Saved receipt metadata to MongoDB: {reference}")
                    return True
            
            # Fallback to local cache
            if user_id not in self.local_cache:
                self.local_cache[user_id] = {"conversations": [], "recipients": [], "transfers": [], "receipts": []}
            
            if "receipts" not in self.local_cache[user_id]:
                self.local_cache[user_id]["receipts"] = []
            
            self.local_cache[user_id]["receipts"].append(receipt_data)
            
            # Keep only last 50 receipts in local cache
            if len(self.local_cache[user_id]["receipts"]) > 50:
                self.local_cache[user_id]["receipts"] = \
                    self.local_cache[user_id]["receipts"][-50:]
            
            logger.info(f"Saved receipt metadata to local cache: {reference}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save receipt metadata: {e}")
            return False
    
    async def get_receipt(self, user_id: str, reference: str) -> Optional[Dict]:
        """Get receipt metadata by reference."""
        try:
            # Try MongoDB first
            if self.mongodb.is_connected():
                receipt = await self.mongodb.get_receipt(user_id, reference)
                if receipt:
                    logger.debug(f"Retrieved receipt from MongoDB: {reference}")
                    return receipt
            
            # Fallback to local cache
            if user_id in self.local_cache and "receipts" in self.local_cache[user_id]:
                receipts = self.local_cache[user_id]["receipts"]
                
                for receipt in receipts:
                    if receipt.get('reference') == reference:
                        logger.debug(f"Retrieved receipt from local cache: {reference}")
                        return receipt
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get receipt: {e}")
            return None
    
    async def get_user_receipts(self, user_id: str, limit: int = 10) -> List[Dict]:
        """Get user's recent receipts."""
        try:
            receipts = []
            
            # Try MongoDB first
            if self.mongodb.is_connected():
                receipts = await self.mongodb.get_user_receipts(user_id, limit)
                if receipts:
                    logger.debug(f"Retrieved {len(receipts)} receipts from MongoDB for user {user_id}")
                    return receipts
            
            # Fallback to local cache
            if user_id in self.local_cache and "receipts" in self.local_cache[user_id]:
                all_receipts = self.local_cache[user_id]["receipts"]
                
                # Sort by timestamp (newest first) and limit
                sorted_receipts = sorted(
                    all_receipts, 
                    key=lambda x: x.get('timestamp', ''), 
                    reverse=True
                )
                
                receipts = sorted_receipts[:limit]
                logger.debug(f"Retrieved {len(receipts)} receipts from local cache for user {user_id}")
            
            return receipts
            
        except Exception as e:
            logger.error(f"Failed to get user receipts: {e}")
            return []
    
    async def save_transaction(self, user_id: str, transaction_data: Dict) -> bool:
        """Save transaction record (for incoming money)."""
        try:
            # Validate required fields
            required_fields = ["amount", "reference", "status"]
            if not all(field in transaction_data for field in required_fields):
                logger.warning("Missing required transaction fields")
                return False
            
            # Add timestamp if not present
            if "timestamp" not in transaction_data:
                transaction_data["timestamp"] = datetime.utcnow().isoformat()
            
            # Try MongoDB first
            if self.mongodb.is_connected():
                result = await self.mongodb.save_transaction(user_id, transaction_data)
                if result:
                    amount = transaction_data.get('amount', 0) / 100  # Convert from kobo
                    logger.info(f"Saved transaction to MongoDB: ₦{amount}")
                    return True
            
            # Fallback to local cache
            if user_id not in self.local_cache:
                self.local_cache[user_id] = {"conversations": [], "recipients": [], "transfers": [], "transactions": []}
            
            if "transactions" not in self.local_cache[user_id]:
                self.local_cache[user_id]["transactions"] = []
            
            self.local_cache[user_id]["transactions"].append(transaction_data)
            
            # Keep only last 50 transactions in local cache
            if len(self.local_cache[user_id]["transactions"]) > 50:
                self.local_cache[user_id]["transactions"] = \
                    self.local_cache[user_id]["transactions"][-50:]
            
            amount = transaction_data.get('amount', 0) / 100  # Convert from kobo
            logger.info(f"Saved transaction to local cache: ₦{amount}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save transaction: {e}")
            return False
    
    async def get_transaction_history(self, user_id: str, limit: int = 10) -> List[Dict]:
        """Get transaction history for a user."""
        try:
            # Try MongoDB first
            if self.mongodb.is_connected():
                transactions = await self.mongodb.get_transaction_history(user_id, limit)
                if transactions:
                    logger.debug(f"Retrieved {len(transactions)} transactions from MongoDB for user {user_id}")
                    return transactions
            
            # Fallback to local cache
            if user_id in self.local_cache and "transactions" in self.local_cache[user_id]:
                transactions = self.local_cache[user_id]["transactions"]
                # Sort by timestamp (newest first) and limit
                sorted_transactions = sorted(
                    transactions, 
                    key=lambda x: x.get('timestamp', ''), 
                    reverse=True
                )
                limited_transactions = sorted_transactions[:limit]
                logger.debug(f"Retrieved {len(limited_transactions)} transactions from local cache for user {user_id}")
                return limited_transactions
            
            return []
            
        except Exception as e:
            logger.error(f"Failed to get transaction history: {e}")
            return []


# Global instance
memory_manager = MemoryManager() 