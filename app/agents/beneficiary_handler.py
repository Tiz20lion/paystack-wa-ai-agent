#!/usr/bin/env python3
"""
Beneficiary Handler Module
Handles all beneficiary/recipient management operations for the Financial Agent.
"""

import logging
from typing import Dict, Optional, List, Any
from app.utils.logger import get_logger
from app.services.paystack_service import PaystackService
from app.utils.recipient_manager import RecipientManager
from app.utils.recipient_cache import RecipientCache
from app.agents.response_handler import ResponseHandler
from app.utils.bank_resolver import BankResolver

logger = get_logger("beneficiary_handler")


class BeneficiaryHandler:
    """Handles all beneficiary and recipient management operations."""
    
    def __init__(self, paystack_service: PaystackService, recipient_manager: RecipientManager, memory_manager=None):
        self.paystack = paystack_service
        self.recipient_manager = recipient_manager
        self.memory = memory_manager  # Properly initialize memory manager
        self.recipient_cache = RecipientCache(paystack_service, recipient_manager)
        self.response_handler = ResponseHandler()
    
    async def handle_add_beneficiary_request(self, user_id: str, message: str, send_follow_up_callback=None) -> str:
        """Handle requests to add new beneficiaries with intelligent duplicate detection."""
        try:
            # Import here to avoid circular imports
            import asyncio
            
            # Send immediate acknowledgment response
            immediate_response = "Let me help you save that contact! ⏳"
            
            # Start background processing task if callback provided
            if send_follow_up_callback:
                asyncio.create_task(self._process_add_beneficiary_background(user_id, message, send_follow_up_callback))
                return immediate_response
            else:
                # Fallback to traditional method
                return await self._handle_add_beneficiary_traditional(user_id, message)
                
        except Exception as e:
            logger.error(f"Failed to start add beneficiary request: {e}")
            return await self._handle_add_beneficiary_traditional(user_id, message)
    
    async def handle_list_beneficiaries(self, user_id: str, send_follow_up_callback=None) -> str:
        """Handle requests to list saved recipients/beneficiaries."""
        try:
            # Import here to avoid circular imports
            import asyncio
            
            # Send immediate acknowledgment response
            immediate_response = "Let me check your saved recipients! ⏳"
            
            # Start background processing task if callback provided
            if send_follow_up_callback:
                asyncio.create_task(self._process_recipients_list_background(user_id, send_follow_up_callback))
                return immediate_response
            else:
                # Fallback to traditional method
                return await self._handle_list_beneficiaries_traditional(user_id)
                
        except Exception as e:
            logger.error(f"Failed to start recipients list request: {e}")
            return await self._handle_list_beneficiaries_traditional(user_id)
    
    async def _process_add_beneficiary_background(self, user_id: str, message: str, send_follow_up_callback):
        """Process add beneficiary request in background with comprehensive duplicate checking."""
        try:
            logger.info(f"🔄 Starting background add beneficiary processing for user {user_id}")
            
            # Extract account details from message
            account_details = self._extract_account_details_from_message(message)
            
            if not account_details:
                await send_follow_up_callback(user_id, 
                    "I couldn't find account details in your message. Please use format: 'Add 0123456789 Access Bank' or 'Save 1234567890 GTBank'")
                return
            
            # Check for existing recipients
            duplicate_check = await self._check_recipient_duplicates(user_id, account_details)
            
            if duplicate_check['is_duplicate']:
                # Send duplicate notification
                final_response = self.response_handler.format_duplicate_recipient_response(duplicate_check)
                await send_follow_up_callback(user_id, final_response)
                logger.info(f"✅ Duplicate recipient detected for user {user_id}")
                return
            
            # Resolve account details via Paystack API
            resolved_account = await self._resolve_and_create_recipient(user_id, account_details)
            
            if resolved_account['success']:
                # Save to local MongoDB as well
                local_save_result = await self._save_recipient_locally(user_id, resolved_account['data'])
                final_response = self.response_handler.format_successful_recipient_save_response(resolved_account['data'], local_save_result)
            else:
                final_response = f"❌ Couldn't resolve account {account_details['account_number']} at {account_details['bank_name']}. Please check the details and try again."
            
            # Send the results as second message
            await send_follow_up_callback(user_id, final_response)
            logger.info(f"✅ Background add beneficiary processing completed for user {user_id}")
            
        except Exception as e:
            logger.error(f"Background add beneficiary processing failed: {e}")
            await send_follow_up_callback(user_id, "Something went wrong while saving your contact. Please try again.")
    
    async def _process_recipients_list_background(self, user_id: str, send_follow_up_callback):
        """Process recipients list in background and send second response."""
        try:
            logger.info(f"🔄 Starting background recipients list processing for user {user_id}")
            
            # Get comprehensive recipients data (MongoDB + Paystack API)
            recipients_data = await self._fetch_comprehensive_recipients_data(user_id)
            
            if not recipients_data or 'error' in recipients_data:
                # Send error response
                await send_follow_up_callback(user_id, "Sorry, I couldn't retrieve your recipients right now. Please try again later.")
                return
            
            # Generate formatted response
            final_response = self.response_handler.format_comprehensive_recipients_response(recipients_data)
            
            # Send the complete results as second message
            await send_follow_up_callback(user_id, final_response)
            logger.info(f"✅ Background recipients list processing completed for user {user_id}")
            
        except Exception as e:
            logger.error(f"Background recipients list processing failed: {e}")
            await send_follow_up_callback(user_id, "Something went wrong while getting your recipients. Please try again.")
    
    async def handle_account_resolution(self, user_id: str, entities: Dict) -> str:
        """Handle account resolution requests."""
        
        account_number = entities.get('account_number')
        bank_code = entities.get('bank_code')
        
        if not account_number or not bank_code:
            return "❌ I need both account number and bank name to resolve the account."
        
        try:
            # Resolve the account
            account_info = await self.paystack.resolve_account(account_number, bank_code)
            
            if account_info and account_info.get('account_name'):
                account_name = account_info['account_name']
                bank_name = entities.get('bank_name', 'Unknown Bank')
                
                return f"""✅ **Account Resolved Successfully**

👤 **Account Name**: {account_name}
💳 **Account Number**: {account_number}
🏦 **Bank**: {bank_name.title()}

Would you like to:
• Send money to this account?
• Save this contact for future use?
• Just wanted to verify the account? ✅ Done!
"""
            else:
                return f"""❌ **Account Resolution Failed**

Could not resolve account **{account_number}** at **{entities.get('bank_name', 'the specified bank')}**.

Please verify:
• Account number is correct (10 digits)
• Bank name is correct
• Account is active

Try again with the correct details."""
                
        except Exception as e:
            logger.error(f"Account resolution failed: {e}")
            return f"❌ Error resolving account. Please check the account number and bank name."
    
    async def handle_beneficiary_mention(self, user_id: str, message: str) -> str:
        """Handle when user mentions beneficiaries in general."""
        
        message_lower = message.lower()
        
        # Check if they want to see saved beneficiaries
        if any(phrase in message_lower for phrase in ["show", "list", "my beneficiaries", "contacts"]):
            return await self.handle_list_beneficiaries(user_id)
        
        # Generic beneficiary response
        return """💼 **Beneficiary Management**

Here's what I can help you with:
• **List** your saved beneficiaries
• **Add** new beneficiaries
• **Send money** to saved contacts
• **Remove** beneficiaries

**Examples:**
• "Show my beneficiaries"
• "Add 0123456789 access bank to my contacts"
• "Send 5k to John"
• "Remove Sarah from my contacts"

What would you like to do?"""
    
    async def _handle_add_beneficiary_traditional(self, user_id: str, message: str) -> str:
        """Traditional method for adding beneficiaries."""
        
        account_number = self._extract_account_number(message)
        bank_name = self._extract_bank_name(message)
        
        if not account_number or not bank_name:
            return """To add a beneficiary, I need:
• Account number (10 digits)
• Bank name

**Examples:**
• "Add 0123456789 access bank to my contacts"
• "Save 0123456789 kuda as John"
• "Remember 0123456789 gtb to my beneficiaries"
"""
        
        try:
            # Resolve the account first
            bank_code = BankResolver.resolve_bank_code(bank_name)
            
            if not bank_code:
                return f"❌ I don't recognize the bank '{bank_name}'. Please use a supported bank name."
            
            account_info = await self.paystack.resolve_account(account_number, bank_code)
            
            if not account_info or not account_info.get('account_name'):
                return f"❌ Could not resolve account {account_number} at {bank_name}. Please verify the details."
            
            account_name = account_info['account_name']
            
            # Check if already saved using centralized cache
            duplicate_check = await self.recipient_cache.check_recipient_duplicates(user_id, account_number, bank_code)
            
            if duplicate_check['is_duplicate']:
                return f"""✅ **Already Saved!**

**{account_name}** ({account_number} - {bank_name.title()}) is already in your contacts.

You can send money by saying:
• "Send 5k to {account_name.split()[0]}"
• "Transfer money to {account_name.split()[0]}"
"""
            
            # Save the beneficiary
            recipient_data = {
                'account_number': account_number,
                'bank_code': bank_code,
                'bank_name': bank_name,
                'account_name': account_name,
                'name': account_name,  # Use account name as display name
                'recipient_type': 'nuban',
                'currency': 'NGN'
            }
            
            saved_recipient = await self.recipient_manager.save_recipient_with_nickname(
                user_id, 
                account_name,  # Use account name as nickname
                account_name,
                account_number,
                bank_name,
                bank_code
            )
            
            if saved_recipient:
                return f"""✅ **Beneficiary Added Successfully!**

**Contact Details:**
👤 **Name**: {account_name}
💳 **Account**: {account_number}
🏦 **Bank**: {bank_name.title()}

**Quick Transfer:**
Now you can easily send money by saying:
• "Send 5k to {account_name.split()[0]}"
• "Transfer 2000 to {account_name.split()[0]}"
"""
            else:
                return "❌ Failed to save beneficiary. Please try again."
                
        except Exception as e:
            logger.error(f"Add beneficiary failed: {e}")
            return f"❌ Error adding beneficiary: {str(e)}"
    
    async def handle_beneficiary_transfer(self, user_id: str, message: str, entities: Dict, memory_manager, balance_checker) -> str:
        """Handle transfers to saved beneficiaries."""
        
        amount = entities.get('amount')
        
        # Extract recipient name from message
        recipient_name = self._extract_recipient_name(message)
        
        if not recipient_name:
            return "I couldn't identify who you want to send money to. Please specify the recipient name."
        
        # Find the recipient using comprehensive search
        recipient = await self.recipient_cache.find_recipient_by_name(user_id, recipient_name)
        
        if not recipient:
            return f"""❌ **Recipient Not Found**

I couldn't find '{recipient_name}' in your saved beneficiaries.

**Options:**
• "Show my beneficiaries" - See all saved contacts
• "Add 0123456789 access bank as {recipient_name}" - Add new contact
• "Send 5k to 0123456789 access" - Transfer to account directly"""
        
        if not amount:
            # Ask for amount
            await memory_manager.set_conversation_state(user_id, {
                'type': 'beneficiary_transfer_pending_amount',
                'recipient_name': recipient_name,
                'recipient_code': recipient.get('recipient_code'),
                'account_name': recipient.get('account_name'),
                'account_number': recipient.get('account_number'),
                'bank_code': recipient.get('bank_code'),
                'bank_name': recipient.get('bank_name'),
                'source': recipient.get('source', 'mongodb')
            })
            
            return f"How much would you like to send to **{recipient.get('account_name', recipient_name)}**?"
        
        # Check balance
        balance_check = await balance_checker.check_sufficient_balance(amount)
        if not balance_check['sufficient']:
            return f"❌ **Insufficient Balance**\n\nYou're trying to send ₦{amount:,.2f} but your balance is {balance_check['formatted_balance']}."
        
        # Set state for confirmation
        await memory_manager.set_conversation_state(user_id, {
            'type': 'beneficiary_transfer_pending_confirmation',
            'amount': amount,
            'recipient_name': recipient_name,
            'recipient_code': recipient.get('recipient_code'),
            'account_name': recipient.get('account_name'),
            'account_number': recipient.get('account_number'),
            'bank_code': recipient.get('bank_code'),
            'bank_name': recipient.get('bank_name'),
            'source': recipient.get('source', 'mongodb')
        })
        
        formatted_amount = f"₦{amount:,.2f}"
        account_name = recipient.get('account_name', recipient_name)
        
        return f"""💰 **Transfer Confirmation**

Send {formatted_amount} to **{account_name}**?"""
    

    
    def _extract_recipient_name(self, message: str) -> Optional[str]:
        """Extract recipient name from transfer message."""
        
        import re
        
        message_lower = message.lower()
        
        # Patterns to extract names from transfer messages
        patterns = [
            # Custom nickname patterns with "my" (extract everything after "my")
            r'(?:to|for|send(?:\s+money)?\s+to)\s+my\s+([a-zA-Z]+(?:\s+[a-zA-Z]+)*)',
            r'give\s+my\s+([a-zA-Z]+(?:\s+[a-zA-Z]+)*)',
            r'pay\s+my\s+([a-zA-Z]+(?:\s+[a-zA-Z]+)*)',
            r'transfer.*to\s+my\s+([a-zA-Z]+(?:\s+[a-zA-Z]+)*)',
            # Regular name patterns
            r'(?:to|for|send(?:\s+money)?\s+to)\s+([a-zA-Z]+(?:\s+[a-zA-Z]+)?)(?:\s+(?:at|$)|\s+\d|$)',
            r'give\s+([a-zA-Z]+(?:\s+[a-zA-Z]+)?)\s+',
            r'pay\s+([a-zA-Z]+(?:\s+[a-zA-Z]+)?)\s+',
            r'transfer.*to\s+([a-zA-Z]+(?:\s+[a-zA-Z]+)?)\s*$',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, message_lower)
            if match:
                name = match.group(1).strip()
                # Filter out common words that aren't names
                stop_words = ['money', 'cash', 'naira', 'the', 'this', 'that', 'some', 'him', 'her', 'them']
                if name not in stop_words and len(name) >= 2:
                    # Return as-is for custom nickname matching (case preserved)
                    return name
        
        return None
    
    def _extract_account_number(self, message: str) -> Optional[str]:
        """Extract account number from a message."""
        import re
        message_lower = message.lower()
        match = re.search(r'\d{10}', message_lower)
        return match.group(0) if match else None

    def _extract_bank_name(self, message: str) -> Optional[str]:
        """Extract bank name from a message."""
        import re
        message_lower = message.lower()
        # Try to find common bank names or patterns
        bank_names = [
            r'access bank', r'gtbank', r'gtb', r'guarantee trust', r'first bank', r'firstbank', r'zenith',
            r'uba', r'united bank', r'fidelity', r'sterling', r'union', r'wema', r'fcmb', r'kuda', r'opay',
            r'palmpay', r'moniepoint', r'carbon', r'providus', r'keystone', r'polaris'
        ]
        for pattern in bank_names:
            match = re.search(pattern, message_lower)
            if match:
                return match.group(0).title()
        return None

    def _extract_account_details_from_message(self, message: str) -> Optional[Dict]:
        """Extract account number and bank details from user message."""
        try:
            import re
            
            # Look for 10-digit account number
            account_match = re.search(r'\b(\d{10})\b', message)
            if not account_match:
                return None
            
            account_number = account_match.group(1)
            
            # Extract bank name/code from message
            message_lower = message.lower()
            bank_mappings = BankResolver.get_all_bank_mappings()
            
            # Check for bank names in message
            for bank_name, bank_code in bank_mappings.items():
                if bank_name in message_lower:
                    return {
                        'account_number': account_number,
                        'bank_name': bank_name,
                        'bank_code': bank_code,
                    }
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to extract account details from message: {e}")
            return None
    
    async def _check_recipient_duplicates(self, user_id: str, account_details: Dict) -> Dict:
        """Check if recipient already exists using centralized cache."""
        try:
            account_number = account_details['account_number']
            bank_code = account_details['bank_code']
            
            logger.info(f"Checking for duplicates: {account_number} at {bank_code}")
            duplicate_check = await self.recipient_cache.check_recipient_duplicates(user_id, account_number, bank_code)
            
            return duplicate_check
            
        except Exception as e:
            logger.error(f"Failed to check recipient duplicates: {e}")
            return {'is_duplicate': False, 'has_similar': False}
    
    async def _resolve_and_create_recipient(self, user_id: str, account_details: Dict) -> Dict:
        """Resolve account details and create Paystack recipient."""
        try:
            account_number = account_details['account_number']
            bank_code = account_details['bank_code']
            bank_name = account_details['bank_name']
            
            # First, resolve the account to get the account name
            logger.info(f"Resolving account {account_number} at {bank_name}")
            resolved_account = await self.paystack.resolve_account(account_number, bank_code)
            
            if not resolved_account or not resolved_account.get('account_name'):
                return {'success': False, 'error': 'Account resolution failed'}
            
            account_name = resolved_account['account_name']
            
            # Create transfer recipient in Paystack
            logger.info(f"Creating Paystack recipient for {account_name}")
            recipient_response = await self.paystack.create_transfer_recipient(
                recipient_type="nuban",
                name=account_name,
                account_number=account_number,
                bank_code=bank_code,
                currency="NGN",
                description=f"Added by {user_id}"
            )
            
            if recipient_response.get('recipient_code'):
                return {
                    'success': True,
                    'data': {
                        'account_name': account_name,
                        'account_number': account_number,
                        'bank_name': bank_name,
                        'bank_code': bank_code,
                        'recipient_code': recipient_response['recipient_code'],
                        'paystack_id': recipient_response.get('id'),
                        'source': 'paystack_created'
                    }
                }
            else:
                return {'success': False, 'error': 'Failed to create Paystack recipient'}
                
        except Exception as e:
            logger.error(f"Failed to resolve and create recipient: {e}")
            return {'success': False, 'error': str(e)}
    
    async def _save_recipient_locally(self, user_id: str, recipient_data: Dict) -> Dict:
        """Save recipient to local MongoDB for faster access."""
        try:
            save_result = await self.recipient_manager.save_recipient_with_nickname(
                user_id=user_id,
                nickname=recipient_data['account_name'],
                account_name=recipient_data['account_name'],
                account_number=recipient_data['account_number'],
                bank_name=recipient_data['bank_name'],
                bank_code=recipient_data['bank_code']
            )
            return {'success': save_result, 'saved_locally': True}
        except Exception as e:
            logger.error(f"Failed to save recipient locally: {e}")
            return {'success': False, 'saved_locally': False, 'error': str(e)}
    

    

    
    async def _fetch_comprehensive_recipients_data(self, user_id: str) -> Dict:
        """Fetch comprehensive recipients data using centralized cache."""
        try:
            logger.info(f"Fetching comprehensive recipients data for user {user_id}")
            recipients_data = await self.recipient_cache.get_comprehensive_recipients(user_id)
            
            return recipients_data
            
        except Exception as e:
            logger.error(f"Failed to fetch comprehensive recipients data: {e}")
            return {'error': str(e)}
    

    
    async def _handle_list_beneficiaries_traditional(self, user_id: str) -> str:
        """Traditional recipients listing (fallback method)."""
        try:
            recipients_data = await self.recipient_cache.get_comprehensive_recipients(user_id)
            local_recipients = recipients_data.get('local_recipients', [])
            
            if not local_recipients:
                # Use response formatter for LLM refinement
                template_response = """You don't have any saved recipients yet! 

To save contacts:
• Send money with their details: "Send 5k to 0123456789 access bank"  
• I'll ask if you want to save them as a contact
• Or give me their details: "Send to John at 1234567890 kuda"

Next time just say: "Send money to John" 💰"""
            
                # Refine with LLM if available
                context = {'user_id': user_id, 'recipients_count': 0}
                return await self.response_handler.refine_with_llm(template_response, context, 'list_beneficiaries')
            
            # Use the unified response formatter
            return self.response_handler.format_recipients_list(local_recipients, [])
            
        except Exception as e:
            logger.error(f"Traditional recipients listing failed: {e}")
            return "Sorry, I couldn't retrieve your recipients. Please try again later."



    
    async def save_recipient(self, recipient_data: Dict) -> bool:
        """Save recipient to memory/database."""
        try:
            # TODO: Implement proper recipient storage
            # This is a stub implementation to fix the missing method error
            logger.info(f"Saving recipient: {recipient_data.get('recipient_code', 'unknown')}")
            
            # For now, just log the recipient data
            # In a full implementation, this would save to database
            return True
            
        except Exception as e:
            logger.error(f"Failed to save recipient: {e}")
            return False 