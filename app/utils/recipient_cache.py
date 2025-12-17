"""
Centralized recipient cache manager for PayStack CLI application.
Eliminates duplicate API calls and provides unified recipient management.
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from app.utils.logger import logger
from app.services.paystack_service import PaystackService
from app.utils.recipient_manager import RecipientManager


class RecipientCache:
    """Centralized recipient cache with intelligent caching and deduplication."""
    
    def __init__(self, paystack_service: PaystackService, recipient_manager: RecipientManager):
        self.paystack = paystack_service
        self.recipient_manager = recipient_manager
        self._cache: Dict[str, Any] = {}
        self._cache_timestamps: Dict[str, datetime] = {}
        self._cache_expiry = timedelta(minutes=15)  # Cache expires after 15 minutes
        self._lock = asyncio.Lock()
    
    async def get_comprehensive_recipients(self, user_id: str, force_refresh: bool = False) -> Dict[str, Any]:
        """Get comprehensive recipients data with caching."""
        try:
            cache_key = f"recipients_{user_id}"
            
            # Check cache first
            if not force_refresh and await self._is_cache_valid(cache_key):
                logger.info(f"Returning cached recipients for user {user_id}")
                return self._cache[cache_key]
            
            async with self._lock:
                # Double-check cache after acquiring lock
                if not force_refresh and await self._is_cache_valid(cache_key):
                    return self._cache[cache_key]
                
                # Fetch fresh data
                logger.info(f"Fetching fresh recipients data for user {user_id}")
                recipients_data = await self._fetch_comprehensive_recipients(user_id)
                
                # Cache the results
                self._cache[cache_key] = recipients_data
                self._cache_timestamps[cache_key] = datetime.now()
                
                return recipients_data
                
        except Exception as e:
            logger.error(f"Failed to get comprehensive recipients: {e}")
            return {
                'local_recipients': [],
                'paystack_recipients': [],
                'local_count': 0,
                'paystack_count': 0,
                'total_count': 0,
                'error': str(e)
            }
    
    async def find_recipient_by_name(self, user_id: str, recipient_name: str) -> Optional[Dict]:
        """Find recipient by name using cached data."""
        try:
            recipients_data = await self.get_comprehensive_recipients(user_id)
            
            # Search in local recipients first
            for recipient in recipients_data.get('local_recipients', []):
                stored_name = recipient.get('name', '').lower()
                search_name = recipient_name.lower()
                
                # Check regular name match
                if (stored_name == search_name or 
                    stored_name.startswith(search_name) or 
                    search_name in stored_name):
                    
                    logger.info(f"Found recipient '{recipient_name}' in local cache: {stored_name}")
                    recipient['source'] = 'local'
                    return recipient
                
                # Check custom nicknames
                custom_nicknames = recipient.get('custom_nicknames', [])
                for custom_nickname in custom_nicknames:
                    if search_name == custom_nickname.lower():
                        logger.info(f"✅ Found recipient by custom nickname '{recipient_name}' -> {recipient.get('name', 'Unknown')}")
                        recipient['source'] = 'local'
                        recipient['matched_custom_nickname'] = recipient_name
                        return recipient
            
            # Search in Paystack recipients
            for recipient in recipients_data.get('paystack_recipients', []):
                stored_name = recipient.get('name', '').lower()
                search_name = recipient_name.lower()
                
                if (stored_name == search_name or 
                    stored_name.startswith(search_name) or 
                    search_name in stored_name):
                    
                    logger.info(f"Found recipient '{recipient_name}' in Paystack cache: {stored_name}")
                    
                    # Convert to consistent format
                    details = recipient.get('details', {})
                    return {
                        'account_name': recipient.get('name'),
                        'account_number': details.get('account_number'),
                        'bank_code': details.get('bank_code'),
                        'bank_name': details.get('bank_name'),
                        'recipient_code': recipient.get('recipient_code'),
                        'source': 'paystack'
                    }
            
            logger.info(f"Recipient '{recipient_name}' not found in cache")
            return None
            
        except Exception as e:
            logger.error(f"Failed to find recipient by name: {e}")
            return None
    
    async def find_recipient_by_account(self, account_number: str, bank_code: str) -> Optional[Dict]:
        """Find recipient by account number using cached data."""
        try:
            # Get all recipients from cache
            recipients_data = await self.get_comprehensive_recipients("system")  # Use system for account lookups
            
            # Search in local recipients
            for recipient in recipients_data.get('local_recipients', []):
                if (recipient.get('account_number') == account_number and 
                    recipient.get('bank_code') == bank_code):
                    logger.info(f"Found recipient by account in local cache: {account_number}")
                    recipient['source'] = 'local'
                    return recipient
            
            # Search in Paystack recipients
            for recipient in recipients_data.get('paystack_recipients', []):
                details = recipient.get('details', {})
                if (details.get('account_number') == account_number and 
                    details.get('bank_code') == bank_code):
                    logger.info(f"Found recipient by account in Paystack cache: {account_number}")
                    recipient['source'] = 'paystack'
                    return recipient
            
            logger.info(f"Recipient with account {account_number} not found in cache")
            return None
            
        except Exception as e:
            logger.error(f"Failed to find recipient by account: {e}")
            return None
    
    async def check_recipient_duplicates(self, user_id: str, account_number: str, bank_code: str) -> Dict:
        """Check for duplicate recipients using cached data."""
        try:
            recipients_data = await self.get_comprehensive_recipients(user_id)
            
            # Check local recipients
            for recipient in recipients_data.get('local_recipients', []):
                if (recipient.get('account_number') == account_number and 
                    recipient.get('bank_code') == bank_code):
                    return {
                        'is_duplicate': True,
                        'source': 'local',
                        'recipient': recipient
                    }
            
            # Check Paystack recipients
            for recipient in recipients_data.get('paystack_recipients', []):
                details = recipient.get('details', {})
                if (details.get('account_number') == account_number and 
                    details.get('bank_code') == bank_code):
                    return {
                        'is_duplicate': True,
                        'source': 'paystack',
                        'recipient': recipient
                    }
            
            return {'is_duplicate': False, 'has_similar': False}
            
        except Exception as e:
            logger.error(f"Failed to check recipient duplicates: {e}")
            return {'is_duplicate': False, 'has_similar': False}
    
    async def invalidate_cache(self, user_id: Optional[str] = None):
        """Invalidate cache for specific user or all users."""
        try:
            if user_id:
                cache_key = f"recipients_{user_id}"
                if cache_key in self._cache:
                    del self._cache[cache_key]
                    del self._cache_timestamps[cache_key]
                    logger.info(f"Invalidated cache for user {user_id}")
            else:
                self._cache.clear()
                self._cache_timestamps.clear()
                logger.info("Invalidated all recipient caches")
                
        except Exception as e:
            logger.error(f"Failed to invalidate cache: {e}")
    
    async def _is_cache_valid(self, cache_key: str) -> bool:
        """Check if cache is still valid."""
        if cache_key not in self._cache or cache_key not in self._cache_timestamps:
            return False
        
        cache_age = datetime.now() - self._cache_timestamps[cache_key]
        return cache_age < self._cache_expiry
    
    async def _fetch_comprehensive_recipients(self, user_id: str) -> Dict[str, Any]:
        """Fetch comprehensive recipients from both sources."""
        try:
            # Get local recipients
            local_recipients = []
            try:
                local_recipients = await self.recipient_manager.list_recipients(user_id)
            except Exception as e:
                logger.warning(f"Failed to get local recipients: {e}")
            
            # Get Paystack recipients
            paystack_recipients: List[Dict] = []
            try:
                paystack_response = await self.paystack.list_transfer_recipients(per_page=100)
                paystack_recipients = paystack_response.get('data', []) if paystack_response else []
            except Exception as e:
                logger.warning(f"Failed to get Paystack recipients: {e}")
            
            return {
                'user_id': user_id,
                'local_recipients': local_recipients,
                'paystack_recipients': paystack_recipients,
                'local_count': len(local_recipients),
                'paystack_count': len(paystack_recipients),
                'total_count': len(local_recipients) + len(paystack_recipients),
                'fetched_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to fetch comprehensive recipients: {e}")
            return {
                'user_id': user_id,
                'local_recipients': [],
                'paystack_recipients': [],
                'local_count': 0,
                'paystack_count': 0,
                'total_count': 0,
                'error': str(e)
            }
    
    async def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        try:
            active_caches = len(self._cache)
            expired_caches = 0
            
            for cache_key, timestamp in self._cache_timestamps.items():
                cache_age = datetime.now() - timestamp
                if cache_age >= self._cache_expiry:
                    expired_caches += 1
            
            return {
                'active_caches': active_caches,
                'expired_caches': expired_caches,
                'cache_expiry_minutes': self._cache_expiry.total_seconds() / 60,
                'cache_keys': list(self._cache.keys())
            }
            
        except Exception as e:
            logger.error(f"Failed to get cache stats: {e}")
            return {'error': str(e)} 