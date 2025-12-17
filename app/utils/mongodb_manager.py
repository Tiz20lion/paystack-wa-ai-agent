#!/usr/bin/env python3
"""
MongoDB Atlas Manager for Paystack CLI App
Handles all MongoDB operations including conversations and recipient caching.
"""

import os
from datetime import datetime
from typing import Dict, List, Optional, Any, cast
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
from pymongo import ASCENDING, DESCENDING
from pymongo.database import Database
from .config import settings
from .logger import get_logger

logger = get_logger("mongodb_manager")


class MongoDBManager:
    """MongoDB Atlas connection and operations manager."""
    
    def __init__(self):
        self.client: Optional[MongoClient] = None
        self.db: Optional[Database] = None
        self.connected: bool = False
        self._connect()
    
    def _connect(self):
        """Connect to MongoDB Atlas."""
        try:
            mongodb_url = settings.mongodb_url
            if not mongodb_url or mongodb_url == "mongodb://localhost:27017":
                logger.warning("MongoDB Atlas URL not configured, using local fallback")
                return
            
            if "<db_password>" in mongodb_url:
                logger.warning("MongoDB password placeholder found - please replace <db_password> with actual password")
                return
            
            self.client = MongoClient(mongodb_url, server_api=ServerApi('1'))
            
            # Test connection
            self.client.admin.command('ping')
            
            self.db = self.client[settings.mongodb_database]
            self.connected = True
            
            # Validate database connection
            if self.db is not None:
                self.connected = True
            else:
                self.connected = False
            
            # Create indexes for better performance
            self._create_indexes()
            
            logger.info(f"✅ Connected to MongoDB Atlas database: {settings.mongodb_database}")
            
        except Exception as e:
            logger.error(f"Failed to connect to MongoDB Atlas: {e}")
            logger.info("App will continue without MongoDB features")
            self.connected = False
    
    def _create_indexes(self):
        """Create database indexes for better performance."""
        if not self.connected or self.db is None:
            return
            
        try:
            # Conversation indexes
            conversations = self.db.conversations
            conversations.create_index([("user_id", ASCENDING)])
            conversations.create_index([("timestamp", DESCENDING)])
            conversations.create_index([("user_id", ASCENDING), ("timestamp", DESCENDING)])
            
            # Recipient indexes
            recipients = self.db.recipients
            recipients.create_index([("user_id", ASCENDING)])
            recipients.create_index([("account_number", ASCENDING)])
            recipients.create_index([("user_id", ASCENDING), ("account_number", ASCENDING)], unique=True)
            
            # Conversation state indexes
            conversation_states = self.db.conversation_states
            conversation_states.create_index([("user_id", ASCENDING)], unique=True)
            
            # Bank indexes
            banks = self.db.banks
            banks.create_index([("code", ASCENDING)], unique=True)
            banks.create_index([("name", ASCENDING)])
            banks.create_index([("slug", ASCENDING)])
            
            logger.info("✅ Database indexes created successfully")
            
        except Exception as e:
            logger.warning(f"Failed to create database indexes: {e}")
    
    def is_connected(self) -> bool:
        """Check if MongoDB is connected."""
        return self.connected
    
    # Conversation Management
    async def save_conversation(self, user_id: str, message: str, role: str = "user", 
                              metadata: Optional[Dict] = None) -> Optional[str]:
        """Save a conversation message."""
        if not self.connected or self.db is None:
            return None
        
        try:
            conversation_doc = {
                "user_id": user_id,
                "message": message,
                "role": role,
                "timestamp": datetime.utcnow(),
                "metadata": metadata or {}
            }
            
            result = self.db.conversations.insert_one(conversation_doc)
            logger.debug(f"Saved conversation for user {user_id}")
            return str(result.inserted_id)
            
        except Exception as e:
            logger.error(f"Failed to save conversation: {e}")
            return None
    
    async def get_conversation_history(self, user_id: str, limit: int = 50) -> List[Dict]:
        """Get conversation history for a user."""
        if not self.connected or self.db is None:
            return []
        
        try:
            cursor = self.db.conversations.find(
                {"user_id": user_id}
            ).sort("timestamp", DESCENDING).limit(limit)
            
            conversations = list(cursor)
            
            # Convert ObjectId to string and format for return
            formatted_conversations = []
            for conv in reversed(conversations):  # Reverse to get chronological order
                formatted_conversations.append({
                    "id": str(conv["_id"]),
                    "message": conv["message"],
                    "role": conv["role"],
                    "timestamp": conv["timestamp"],
                    "metadata": conv.get("metadata", {})
                })
            
            return formatted_conversations
            
        except Exception as e:
            logger.error(f"Failed to get conversation history: {e}")
            return []
    
    # Recipient Management
    async def save_recipient(self, user_id: str, recipient_data: Dict) -> Optional[str]:
        """Save a recipient for future transfers."""
        if not self.connected or self.db is None:
            return None
        
        try:
            # Base document without use_count (to avoid conflict)
            recipient_doc = {
                "user_id": user_id,
                "account_name": recipient_data.get("account_name"),
                "account_number": recipient_data.get("account_number"),
                "bank_name": recipient_data.get("bank_name"),
                "bank_code": recipient_data.get("bank_code"),
                "nickname": recipient_data.get("nickname", ""),
                "last_used": datetime.utcnow()
            }
            
            # Use upsert to avoid duplicates
            filter_criteria = {
                "user_id": user_id,
                "account_number": recipient_data.get("account_number")
            }
            
            update_data = {
                "$set": {
                    **recipient_doc,
                    "last_used": datetime.utcnow()
                },
                "$inc": {"use_count": 1},
                "$setOnInsert": {
                    "created_at": datetime.utcnow()
                }
            }
            
            result = self.db.recipients.update_one(
                filter_criteria,
                update_data,
                upsert=True
            )
            
            logger.debug(f"Saved recipient for user {user_id}")
            return str(result.upserted_id) if result.upserted_id else "updated"
            
        except Exception as e:
            logger.error(f"Failed to save recipient: {e}")
            return None
    
    async def save_recipient_nickname(self, user_id: str, recipient_name: str, custom_nickname: str, recipient_data: Dict) -> bool:
        """Save a custom nickname for an existing recipient."""
        try:
            if not self.connected or self.db is None:
                return False
            
            # Update existing recipient with custom nickname (using partial matching like other lookups)
            result = self.db.recipients.update_one(
                {
                    "user_id": user_id,
                    "$or": [
                        {"account_name": {"$regex": recipient_name, "$options": "i"}},
                        {"nickname": {"$regex": recipient_name, "$options": "i"}}
                    ]
                },
                {
                    "$addToSet": {"custom_nicknames": custom_nickname},
                    "$set": {"updated_at": datetime.utcnow()}
                }
            )
            
            if result.modified_count > 0:
                logger.info(f"Added custom nickname '{custom_nickname}' to {recipient_name} for user {user_id}")
                return True
            else:
                # If no recipient was updated, try to find and create the nickname entry
                logger.warning(f"No recipient found to update with nickname '{custom_nickname}'")
                return False
                
        except Exception as e:
            logger.error(f"Failed to save recipient nickname: {e}")
            return False
    
    async def find_recipient_by_custom_nickname(self, user_id: str, custom_nickname: str) -> Optional[Dict]:
        """Find a recipient by their custom nickname."""
        try:
            if not self.connected or self.db is None:
                return None
            
            recipient = self.db.recipients.find_one({
                "user_id": user_id,
                "custom_nicknames": {"$in": [custom_nickname]}
            })
            
            if recipient:
                # Convert MongoDB ObjectId to string if present
                if '_id' in recipient:
                    recipient['id'] = str(recipient['_id'])
                    del recipient['_id']
                
                logger.info(f"Found recipient by custom nickname '{custom_nickname}' for user {user_id}")
                return recipient
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to find recipient by custom nickname: {e}")
            return None
    
    async def get_recipients(self, user_id: str) -> List[Dict]:
        """Get saved recipients for a user."""
        if not self.connected or self.db is None:
            return []
        
        try:
            cursor = self.db.recipients.find(
                {"user_id": user_id}
            ).sort("last_used", DESCENDING)
            
            recipients = list(cursor)
            
            # Format for return
            formatted_recipients = []
            for recipient in recipients:
                formatted_recipients.append({
                    "id": str(recipient["_id"]),
                    "account_name": recipient["account_name"],
                    "account_number": recipient["account_number"],
                    "bank_name": recipient["bank_name"],
                    "bank_code": recipient["bank_code"],
                    "recipient_code": recipient.get("recipient_code"),  # Add recipient_code for transfers
                    "nickname": recipient.get("nickname", ""),
                    "custom_nicknames": recipient.get("custom_nicknames", []),  # CRITICAL: Add custom_nicknames field
                    "last_used": recipient.get("last_used"),
                    "use_count": recipient.get("use_count", 1)
                })
            
            return formatted_recipients
            
        except Exception as e:
            logger.error(f"Failed to get recipients: {e}")
            return []
    
    async def find_recipient(self, user_id: str, search_term: str) -> Optional[Dict]:
        """Find a recipient by name or account number."""
        if not self.connected or self.db is None:
            return None
        
        try:
            # Search by account name, nickname, or account number
            search_criteria = {
                "user_id": user_id,
                "$or": [
                    {"account_name": {"$regex": search_term, "$options": "i"}},
                    {"nickname": {"$regex": search_term, "$options": "i"}},
                    {"account_number": search_term}
                ]
            }
            
            recipient = self.db.recipients.find_one(search_criteria)
            
            if recipient:
                # Update last_used timestamp
                self.db.recipients.update_one(
                    {"_id": recipient["_id"]},
                    {
                        "$set": {"last_used": datetime.utcnow()},
                        "$inc": {"use_count": 1}
                    }
                )
                
                return {
                    "id": str(recipient["_id"]),
                    "account_name": recipient["account_name"],
                    "account_number": recipient["account_number"],
                    "bank_name": recipient["bank_name"],
                    "bank_code": recipient["bank_code"],
                    "nickname": recipient.get("nickname", "")
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to find recipient: {e}")
            return None
    
    # Transfer History
    async def save_transfer_record(self, user_id: str, transfer_data: Dict) -> Optional[str]:
        """Legacy method - redirect to save_transfer."""
        return await self.save_transfer(user_id, transfer_data)
    
    async def get_transfer_history(self, user_id: str, limit: int = 20) -> List[Dict]:
        """Get transfer history for a user."""
        if not self.connected or self.db is None:
            return []
        
        try:
            cursor = self.db.transfers.find(
                {"user_id": user_id}
            ).sort("timestamp", DESCENDING).limit(limit)
            
            transfers = list(cursor)
            
            formatted_transfers = []
            for transfer in transfers:
                formatted_transfers.append({
                    "id": str(transfer["_id"]),
                    "amount": transfer["amount"],
                    "recipient": transfer["recipient"],
                    "reference": transfer["reference"],
                    "status": transfer["status"],
                    "reason": transfer["reason"],
                    "timestamp": transfer["timestamp"]
                })
            
            return formatted_transfers
            
        except Exception as e:
            logger.error(f"Failed to get transfer history: {e}")
            return []
    
    # Conversation State Management
    async def set_conversation_state(self, user_id: str, state: Dict) -> Optional[str]:
        """Set conversation state for multi-step workflows."""
        if not self.connected or self.db is None:
            return None
        
        try:
            state_doc = {
                "user_id": user_id,
                "state": state,
                "timestamp": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            }
            
            # Use upsert to replace existing state
            result = self.db.conversation_states.update_one(
                {"user_id": user_id},
                {"$set": state_doc},
                upsert=True
            )
            
            logger.debug(f"Set conversation state for user {user_id}")
            return str(result.upserted_id) if result.upserted_id else "updated"
            
        except Exception as e:
            logger.error(f"Failed to set conversation state: {e}")
            return None
    
    async def get_conversation_state(self, user_id: str) -> Optional[Dict]:
        """Get current conversation state."""
        if not self.connected or self.db is None:
            return None
        
        try:
            state_doc = self.db.conversation_states.find_one({"user_id": user_id})
            
            if state_doc:
                return {
                    **state_doc["state"],
                    "timestamp": state_doc["timestamp"]
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get conversation state: {e}")
            return None
    
    async def clear_conversation_state(self, user_id: str) -> bool:
        """Clear conversation state."""
        if not self.connected or self.db is None:
            return False
        
        try:
            result = self.db.conversation_states.delete_one({"user_id": user_id})
            logger.debug(f"Cleared conversation state for user {user_id}")
            return result.deleted_count > 0
            
        except Exception as e:
            logger.error(f"Failed to clear conversation state: {e}")
            return False
    
    # Enhanced Transfer Management
    async def save_transfer(self, user_id: str, transfer_data: Dict) -> Optional[str]:
        """Save enhanced transfer record."""
        if not self.connected or self.db is None:
            return None
        
        try:
            transfer_doc = {
                "user_id": user_id,
                "amount": transfer_data.get("amount"),
                "recipient": transfer_data.get("recipient"),
                "reference": transfer_data.get("reference"),
                "transfer_code": transfer_data.get("transfer_code"),
                "status": transfer_data.get("status", "pending"),
                "reason": transfer_data.get("reason", ""),
                "timestamp": transfer_data.get("timestamp", datetime.utcnow().isoformat()),
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
                "paystack_data": transfer_data.get("paystack_response", {})
            }
            
            result = self.db.transfers.insert_one(transfer_doc)
            logger.debug(f"Saved enhanced transfer record for user {user_id}")
            return str(result.inserted_id)
            
        except Exception as e:
            logger.error(f"Failed to save enhanced transfer: {e}")
            return None
    
    async def update_transfer_status(self, user_id: str, transfer_reference: str, status: str) -> bool:
        """Update transfer status by reference."""
        if not self.connected or self.db is None:
            return False
        
        try:
            result = self.db.transfers.update_one(
                {
                    "user_id": user_id,
                    "reference": transfer_reference
                },
                {
                    "$set": {
                        "status": status,
                        "updated_at": datetime.utcnow()
                    }
                }
            )
            
            logger.debug(f"Updated transfer status: {transfer_reference} -> {status}")
            return result.modified_count > 0
            
        except Exception as e:
            logger.error(f"Failed to update transfer status: {e}")
            return False
    
    # Enhanced Transaction Management
    async def save_transaction(self, user_id: str, transaction_data: Dict) -> Optional[str]:
        """Save enhanced transaction record (for incoming money)."""
        if not self.connected or self.db is None:
            return None
        
        try:
            transaction_doc = {
                "user_id": user_id,
                "amount": transaction_data.get("amount"),
                "channel": transaction_data.get("channel"),
                "reference": transaction_data.get("reference"),
                "status": transaction_data.get("status", "success"),
                "gateway_response": transaction_data.get("gateway_response", ""),
                "paid_at": transaction_data.get("paid_at"),
                "created_at": transaction_data.get("created_at", datetime.utcnow().isoformat()),
                "timestamp": transaction_data.get("timestamp", datetime.utcnow().isoformat()),
                "transaction_date": transaction_data.get("transaction_date"),
                "currency": transaction_data.get("currency", "NGN"),
                "customer_email": transaction_data.get("customer", {}).get("email") if transaction_data.get("customer") else None,
                "paystack_data": transaction_data.get("paystack_response", transaction_data),
                "saved_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            }
            
            # Use upsert to avoid duplicates based on reference
            result = self.db.transactions.update_one(
                {
                    "user_id": user_id,
                    "reference": transaction_data.get("reference")
                },
                {
                    "$set": transaction_doc,
                    "$setOnInsert": {"first_saved": datetime.utcnow()}
                },
                upsert=True
            )
            
            if result.upserted_id:
                logger.debug(f"Saved new transaction record for user {user_id}")
                return str(result.upserted_id)
            else:
                logger.debug(f"Updated existing transaction record for user {user_id}")
                return "updated"
            
        except Exception as e:
            logger.error(f"Failed to save transaction: {e}")
            return None
    
    async def get_transaction_history(self, user_id: str, limit: int = 20) -> List[Dict]:
        """Get transaction history from database."""
        if not self.connected or self.db is None:
            return []
        
        try:
            cursor = self.db.transactions.find(
                {"user_id": user_id}
            ).sort("created_at", DESCENDING).limit(limit)
            
            transactions = list(cursor)
            
            # Convert to format compatible with Paystack API
            formatted_transactions = []
            for tx in transactions:
                formatted_tx = {
                    "amount": tx.get("amount", 0),
                    "channel": tx.get("channel", "unknown"),
                    "reference": tx.get("reference", ""),
                    "status": tx.get("status", "success"),
                    "gateway_response": tx.get("gateway_response", ""),
                    "paid_at": tx.get("paid_at"),
                    "created_at": tx.get("created_at"),
                    "transaction_date": tx.get("transaction_date"),
                    "currency": tx.get("currency", "NGN"),
                    "customer": {"email": tx.get("customer_email")} if tx.get("customer_email") else {},
                    "source": "database"
                }
                formatted_transactions.append(formatted_tx)
            
            logger.debug(f"Retrieved {len(formatted_transactions)} transactions from database for user {user_id}")
            return formatted_transactions
            
        except Exception as e:
            logger.error(f"Failed to get transaction history: {e}")
            return []

    async def save_receipt(self, user_id: str, receipt_data: Dict) -> Optional[str]:
        """Save receipt metadata."""
        if not self.connected or self.db is None:
            return None
        
        try:
            receipt_doc = {
                "user_id": user_id,
                "reference": receipt_data.get("reference"),
                "receipt_path": receipt_data.get("receipt_path"),
                "receipt_url": receipt_data.get("receipt_url"),
                "timestamp": receipt_data.get("timestamp", datetime.utcnow().isoformat()),
                "created_at": datetime.utcnow()
            }
            
            result = self.db.receipts.insert_one(receipt_doc)
            
            if result.inserted_id:
                logger.debug(f"Receipt metadata saved: {receipt_data.get('reference')}")
                return str(result.inserted_id)
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to save receipt metadata: {e}")
            return None
    
    async def get_receipt(self, user_id: str, reference: str) -> Optional[Dict]:
        """Get receipt metadata by reference."""
        if not self.connected or self.db is None:
            return None
        
        try:
            receipt = self.db.receipts.find_one({
                "user_id": user_id,
                "reference": reference
            })
            
            if receipt:
                return {
                    "reference": receipt["reference"],
                    "receipt_path": receipt["receipt_path"],
                    "receipt_url": receipt.get("receipt_url"),
                    "timestamp": receipt["timestamp"],
                    "created_at": receipt["created_at"]
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get receipt: {e}")
            return None
    
    async def get_user_receipts(self, user_id: str, limit: int = 10) -> List[Dict]:
        """Get user's recent receipts."""
        if not self.connected or self.db is None:
            return []
        
        try:
            cursor = self.db.receipts.find(
                {"user_id": user_id}
            ).sort("created_at", DESCENDING).limit(limit)
            
            receipts = []
            for receipt in cursor:
                receipts.append({
                    "reference": receipt["reference"],
                    "receipt_path": receipt["receipt_path"], 
                    "receipt_url": receipt.get("receipt_url"),
                    "timestamp": receipt["timestamp"],
                    "created_at": receipt["created_at"]
                })
            
            return receipts
            
        except Exception as e:
            logger.error(f"Failed to get user receipts: {e}")
            return []

    def close(self):
        """Close MongoDB connection."""
        if self.client:
            self.client.close()
            logger.info("MongoDB connection closed")

    # Bank Management
    async def save_banks(self, banks_data: List[Dict]) -> bool:
        """Save Nigerian banks from Paystack API to database."""
        if not self.connected or self.db is None:
            return False
        
        try:
            # Use upsert to handle duplicates instead of clearing all
            banks_saved = 0
            banks_updated = 0
            
            for bank in banks_data:
                bank_doc = {
                    "name": bank.get("name"),
                    "slug": bank.get("slug"),
                    "code": bank.get("code"),
                    "longcode": bank.get("longcode"),
                    "gateway": bank.get("gateway"),
                    "pay_with_bank": bank.get("pay_with_bank", False),
                    "active": bank.get("active", True),
                    "is_deleted": bank.get("is_deleted", False),
                    "country": bank.get("country", "Nigeria"),
                    "currency": bank.get("currency", "NGN"),
                    "type": bank.get("type", "nuban"),
                    "updated_at": datetime.utcnow()
                }
                
                # Use upsert to avoid duplicates
                result = self.db.banks.update_one(
                    {"code": bank.get("code")},  # Filter by code
                    {
                        "$set": bank_doc,
                        "$setOnInsert": {"created_at": datetime.utcnow(), "use_count": 0}
                    },
                    upsert=True
                )
                
                if result.upserted_id:
                    banks_saved += 1
                elif result.modified_count > 0:
                    banks_updated += 1
            
            logger.info(f"✅ Banks processed: {banks_saved} new, {banks_updated} updated")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save banks: {e}")
            return False
    
    async def get_bank_by_code(self, bank_code: str) -> Optional[Dict]:
        """Get bank details by bank code."""
        if not self.connected or self.db is None:
            return None
        
        try:
            bank = self.db.banks.find_one({"code": bank_code})
            
            if bank:
                return {
                    "name": bank["name"],
                    "code": bank["code"],
                    "slug": bank["slug"],
                    "longcode": bank.get("longcode"),
                    "active": bank.get("active", True)
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get bank by code: {e}")
            return None
    
    async def get_bank_by_name(self, bank_name: str) -> Optional[Dict]:
        """Get bank details by bank name (case-insensitive)."""
        if not self.connected or self.db is None:
            return None
        
        try:
            # Try exact match first
            bank = self.db.banks.find_one({"name": {"$regex": f"^{bank_name}$", "$options": "i"}})
            
            if not bank:
                # Try partial match
                bank = self.db.banks.find_one({"name": {"$regex": bank_name, "$options": "i"}})
            
            if bank:
                return {
                    "name": bank["name"],
                    "code": bank["code"],
                    "slug": bank["slug"],
                    "longcode": bank.get("longcode"),
                    "active": bank.get("active", True)
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get bank by name: {e}")
            return None
    
    async def list_all_banks(self) -> List[Dict]:
        """Get all banks from database."""
        if not self.connected or self.db is None:
            return []
        
        try:
            cursor = self.db.banks.find({"active": True}).sort("name", ASCENDING)
            banks = list(cursor)
            
            formatted_banks = []
            for bank in banks:
                formatted_banks.append({
                    "name": bank["name"],
                    "code": bank["code"],
                    "slug": bank["slug"],
                    "longcode": bank.get("longcode"),
                    "active": bank.get("active", True)
                })
            
            return formatted_banks
            
        except Exception as e:
            logger.error(f"Failed to list banks: {e}")
            return []
    
    async def search_banks(self, query: str) -> List[Dict]:
        """Search banks by name or code."""
        if not self.connected or self.db is None:
            return []
        
        try:
            search_criteria = {
                "$and": [
                    {"active": True},
                    {
                        "$or": [
                            {"name": {"$regex": query, "$options": "i"}},
                            {"code": {"$regex": query, "$options": "i"}},
                            {"slug": {"$regex": query, "$options": "i"}}
                        ]
                    }
                ]
            }
            
            cursor = self.db.banks.find(search_criteria).sort("name", ASCENDING)
            banks = list(cursor)
            
            formatted_banks = []
            for bank in banks:
                formatted_banks.append({
                    "name": bank["name"],
                    "code": bank["code"],
                    "slug": bank["slug"],
                    "longcode": bank.get("longcode"),
                    "active": bank.get("active", True)
                })
            
            return formatted_banks
            
        except Exception as e:
            logger.error(f"Failed to search banks: {e}")
            return []


# Global instance
mongodb_manager = MongoDBManager() 