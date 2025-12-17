#!/usr/bin/env python3
"""
Unified Recipient Management System for Paystack WhatsApp AI Agent
Handles saving, retrieving, and managing transfer recipients using MongoDB.
Integrates with Paystack API for automatic recipient resolution.
"""

from typing import Dict, List, Optional, Any
from datetime import datetime
from .logger import get_logger
from .mongodb_manager import MongoDBManager
from ..services.paystack_service import PaystackService

logger = get_logger("recipient_manager")

# Bank nickname mappings for common user references
BANK_NICKNAMES = {
    # GTBank variations
    "gtbank": "Guaranty Trust Bank",
    "gt bank": "Guaranty Trust Bank", 
    "gtb": "Guaranty Trust Bank",
    "guaranty": "Guaranty Trust Bank",
    
    # UBA variations
    "uba": "United Bank For Africa",
    "united bank": "United Bank For Africa",
    
    # Access Bank variations
    "access": "Access Bank",
    
    # First Bank variations
    "first bank": "First Bank of Nigeria",
    "firstbank": "First Bank of Nigeria",
    "fbn": "First Bank of Nigeria",
    
    # Zenith Bank variations
    "zenith": "Zenith Bank",
    
    # Other common banks
    "fcmb": "First City Monument Bank",
    "union bank": "Union Bank of Nigeria",
    "sterling": "Sterling Bank",
    "wema": "Wema Bank",
    "fidelity": "Fidelity Bank",
    "kuda": "Kuda Bank",
    "opay": "Opay",
    "palmpay": "PalmPay",
    "moniepoint": "Moniepoint MFB",
    "carbon": "Carbon",
}


class RecipientManager:
    """
    Unified recipient management system using MongoDB and Paystack API.
    Replaces the old JSON-based beneficiary system.
    """
    
    def __init__(self):
        self.db = MongoDBManager()
        self.paystack = PaystackService()
    
    async def find_recipient_by_name(self, user_id: str, name: str) -> Optional[Dict]:
        """
        Find a recipient by name/nickname/custom_nickname. If not found, return None.
        This is the primary method for name-based recipient lookup.
        """
        try:
            if not self.db.is_connected():
                logger.warning("MongoDB not connected, recipient lookup disabled")
                return None
            
            # First, try to find by regular name/nickname
            recipient = await self.db.find_recipient(user_id, name)
            
            if recipient:
                logger.info(f"Found saved recipient '{name}' for user {user_id}")
                return {
                    "id": recipient["id"],
                    "nickname": recipient["nickname"] or recipient["account_name"],
                    "account_name": recipient["account_name"],
                    "account_number": recipient["account_number"],
                    "bank_name": recipient["bank_name"],
                    "bank_code": recipient["bank_code"],
                    "is_saved": True
                }
            
            # If not found, try to find by custom nickname
            recipient = await self.db.find_recipient_by_custom_nickname(user_id, name)
            
            if recipient:
                logger.info(f"Found saved recipient by custom nickname '{name}' for user {user_id}")
                return {
                    "id": recipient["id"],
                    "nickname": recipient["nickname"] or recipient["account_name"],
                    "account_name": recipient["account_name"],
                    "account_number": recipient["account_number"],
                    "bank_name": recipient["bank_name"],
                    "bank_code": recipient["bank_code"],
                    "is_saved": True,
                    "matched_custom_nickname": name
                }
            
            logger.info(f"No saved recipient found for '{name}' for user {user_id}")
            return None
            
        except Exception as e:
            logger.error(f"Error finding recipient by name: {e}")
            return None
    
    async def resolve_and_save_recipient(self, user_id: str, nickname: str, 
                                       account_number: str, bank_code: str) -> Optional[Dict]:
        """
        Resolve account details via Paystack API and save as a new recipient.
        """
        try:
            # First resolve the account with Paystack
            account_info = await self.paystack.resolve_account(account_number, bank_code)
            
            if not account_info or not account_info.get('account_name'):
                logger.error(f"Failed to resolve account {account_number} with bank code {bank_code}")
                return None
            
            account_name = account_info['account_name']
            
            # Get bank name from database instead of hardcoded mappings
            bank_info = await self.db.get_bank_by_code(bank_code)
            if bank_info:
                bank_name = bank_info['name']
            else:
                # Fallback to code if bank not found in database
                bank_name = f"Bank ({bank_code})"
                logger.warning(f"Bank code {bank_code} not found in database, using fallback name")
            
            # Save to MongoDB
            recipient_data = {
                "account_name": account_name,
                "account_number": account_number,
                "bank_name": bank_name,
                "bank_code": bank_code,
                "nickname": nickname
            }
            
            if self.db.is_connected():
                saved_id = await self.db.save_recipient(user_id, recipient_data)
                if saved_id:
                    logger.info(f"Saved new recipient '{nickname}' ({account_name}) for user {user_id}")
                    return {
                        "nickname": nickname,
                        "account_name": account_name,
                        "account_number": account_number,
                        "bank_name": bank_name,
                        "bank_code": bank_code,
                        "is_saved": True,
                        "is_new": True
                    }
            
            # Return resolved data even if save failed
            return {
                "nickname": nickname,
                "account_name": account_name,
                "account_number": account_number,
                "bank_name": bank_name,
                "bank_code": bank_code,
                "is_saved": False,
                "is_new": True
            }
            
        except Exception as e:
            logger.error(f"Error resolving and saving recipient: {e}")
            return None
    
    async def find_or_resolve_recipient(self, user_id: str, name_or_account: str, 
                                      bank_code: Optional[str] = None) -> Optional[Dict]:
        """
        Comprehensive recipient lookup:
        1. First try to find by name in saved recipients
        2. If not found and bank_code provided, resolve via Paystack API
        3. If resolved successfully, save as new recipient
        """
        try:
            # First try to find existing recipient by name
            recipient = await self.find_recipient_by_name(user_id, name_or_account)
            if recipient:
                return recipient
            
            # If not found and looks like account number with bank code, try to resolve
            if bank_code and name_or_account.isdigit() and len(name_or_account) == 10:
                logger.info(f"Attempting to resolve account {name_or_account} with bank {bank_code}")
                return await self.resolve_and_save_recipient(
                    user_id, 
                    f"Contact_{name_or_account[-4:]}", # Default nickname
                    name_or_account, 
                    bank_code
                )
            
            return None
            
        except Exception as e:
            logger.error(f"Error in find_or_resolve_recipient: {e}")
            return None
    
    async def save_recipient_with_nickname(self, user_id: str, nickname: str,
                                         account_name: str, account_number: str,
                                         bank_name: str, bank_code: str) -> bool:
        """
        Save a recipient with a custom nickname for easy future reference.
        """
        try:
            if not self.db.is_connected():
                logger.warning("MongoDB not connected, cannot save recipient")
                return False
            
            recipient_data = {
                "account_name": account_name,
                "account_number": account_number,
                "bank_name": bank_name,
                "bank_code": bank_code,
                "nickname": nickname
            }
            
            saved_id = await self.db.save_recipient(user_id, recipient_data)
            if saved_id:
                logger.info(f"Saved recipient '{nickname}' ({account_name}) for user {user_id}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error saving recipient with nickname: {e}")
            return False
    
    async def list_recipients(self, user_id: str) -> List[Dict]:
        """Get all saved recipients for a user."""
        try:
            if not self.db.is_connected():
                logger.warning("MongoDB not connected, cannot list recipients")
                return []
            
            recipients = await self.db.get_recipients(user_id)
            
            formatted_recipients = []
            for recipient in recipients:
                formatted_recipients.append({
                    "id": recipient.get("id"),
                    "nickname": recipient.get("nickname") or recipient.get("account_name"),
                    "display_name": recipient.get("nickname") or recipient.get("account_name"),
                    "name": recipient.get("account_name"),  # Add name field for cache lookup
                    "account_name": recipient.get("account_name"),
                    "account_number": recipient.get("account_number"),
                    "bank_name": recipient.get("bank_name"),
                    "bank_code": recipient.get("bank_code"),
                    "recipient_code": recipient.get("recipient_code"),  # Required for transfers
                    "custom_nicknames": recipient.get("custom_nicknames", []),  # Include custom nicknames!
                    "usage_count": recipient.get("use_count", 0),
                    "last_used": recipient.get("last_used")
                })
            
            return formatted_recipients
            
        except Exception as e:
            logger.error(f"Error listing recipients: {e}")
            return []
    
    async def has_recipients(self, user_id: str) -> bool:
        """Check if user has any saved recipients."""
        try:
            recipients = await self.list_recipients(user_id)
            return len(recipients) > 0
        except Exception as e:
            logger.error(f"Error checking if user has recipients: {e}")
            return False
    
    async def search_recipients(self, user_id: str, query: str) -> List[Dict]:
        """Search recipients by name, nickname, or account name."""
        try:
            recipients = await self.list_recipients(user_id)
            query_lower = query.lower()
            
            matches = []
            for recipient in recipients:
                if (query_lower in recipient["nickname"].lower() or
                    query_lower in recipient["account_name"].lower() or
                    query_lower in recipient.get("display_name", "").lower()):
                    matches.append(recipient)
            
            return matches
            
        except Exception as e:
            logger.error(f"Error searching recipients: {e}")
            return []
    
    async def remove_recipient(self, user_id: str, name: str) -> bool:
        """Remove a recipient by name/nickname."""
        try:
            # This would need to be implemented in MongoDB manager
            # For now, return False as removal is not critical
            logger.info(f"Recipient removal requested for '{name}' by user {user_id}")
            return False
            
        except Exception as e:
            logger.error(f"Error removing recipient: {e}")
            return False

    async def resolve_bank_name_to_code(self, bank_name: str) -> Optional[Dict]:
        """
        Resolve bank name to bank code using database lookup.
        This helps when users provide bank names instead of codes.
        Now includes nickname mapping for common bank references.
        """
        try:
            if not self.db.is_connected():
                logger.warning("MongoDB not connected, bank name resolution disabled")
                return None
            
            # First, check if the bank name is a common nickname
            bank_name_lower = bank_name.lower().strip()
            if bank_name_lower in BANK_NICKNAMES:
                mapped_name = BANK_NICKNAMES[bank_name_lower]
                logger.info(f"Mapped bank nickname '{bank_name}' to '{mapped_name}'")
                bank_name = mapped_name
            
            bank_info = await self.db.get_bank_by_name(bank_name)
            
            if bank_info:
                logger.info(f"Resolved bank name '{bank_name}' to code '{bank_info['code']}'")
                return bank_info
            
            # Try searching with partial matches
            search_results = await self.db.search_banks(bank_name)
            if search_results:
                # Return the first match
                bank_info = search_results[0]
                logger.info(f"Partially resolved bank name '{bank_name}' to '{bank_info['name']}' (Code: {bank_info['code']})")
                return bank_info
            
            logger.warning(f"Could not resolve bank name '{bank_name}' to any known bank")
            return None
            
        except Exception as e:
            logger.error(f"Error resolving bank name to code: {e}")
            return None
    
    async def list_all_banks(self) -> List[Dict]:
        """Get all available banks from database for AI agent reference."""
        try:
            if not self.db.is_connected():
                logger.warning("MongoDB not connected, cannot list banks")
                return []
            
            banks = await self.db.list_all_banks()
            logger.info(f"Retrieved {len(banks)} banks from database")
            return banks
            
        except Exception as e:
            logger.error(f"Error listing all banks: {e}")
            return []
    
    async def search_banks_by_name(self, query: str) -> List[Dict]:
        """Search banks by name or partial name match."""
        try:
            if not self.db.is_connected():
                logger.warning("MongoDB not connected, cannot search banks")
                return []
            
            banks = await self.db.search_banks(query)
            logger.info(f"Found {len(banks)} banks matching '{query}'")
            return banks
            
        except Exception as e:
            logger.error(f"Error searching banks: {e}")
            return []


# Global instance
recipient_manager = RecipientManager() 