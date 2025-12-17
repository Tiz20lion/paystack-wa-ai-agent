"""
Conversation State Management Module
Handles state persistence and retrieval for ongoing conversations.
"""

import json
import re
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from app.utils.logger import get_logger

logger = get_logger("conversation_state")


class ConversationState:
    """Manages conversation state for multi-turn interactions."""
    
    def __init__(self, memory_manager=None):
        self.memory = memory_manager
        self.active_states: Dict[str, Dict[str, Any]] = {}  # In-memory cache for active conversations
    
    async def save_state(self, user_id: str, state_type: str, state_data: Dict[str, Any]) -> bool:
        """Save conversation state for a user."""
        try:
            state_key = f"{user_id}_{state_type}"
            
            # Enhanced state data with metadata
            enhanced_state = {
                'user_id': user_id,
                'state_type': state_type,
                'data': state_data,
                'timestamp': datetime.utcnow().isoformat(),
                'version': '1.0'
            }
            
            # Save to memory cache
            self.active_states[state_key] = enhanced_state
            
            # Save to persistent storage if memory manager available
            if self.memory:
                await self.memory.save_conversation_state(user_id, state_type, enhanced_state)
            
            logger.debug(f"Saved conversation state for user {user_id}, type: {state_type}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save conversation state: {e}")
            return False
    
    async def get_state(self, user_id: str, state_type: str) -> Dict[str, Any]:
        """Get conversation state for a user."""
        try:
            state_key = f"{user_id}_{state_type}"
            
            # Check memory cache first
            if state_key in self.active_states:
                return self.active_states[state_key]
            
            # Check persistent storage
            if self.memory:
                state = await self.memory.get_conversation_state(user_id, state_type)
                if state:
                    # Cache in memory for faster access
                    self.active_states[state_key] = state
                    return dict(state) if state else {}
            
            # Return empty dict if no state found
            return {}
            
        except Exception as e:
            logger.error(f"Failed to get conversation state: {e}")
            return {}
    
    async def clear_state(self, user_id: str, state_type: Optional[str] = None) -> bool:
        """Clear conversation state for a user."""
        try:
            if state_type:
                # Clear specific state type
                state_key = f"{user_id}_{state_type}"
                self.active_states.pop(state_key, None)
                
                if self.memory:
                    await self.memory.clear_conversation_state(user_id, state_type)
            else:
                # Clear all states for user
                keys_to_remove = [key for key in self.active_states.keys() if key.startswith(f"{user_id}_")]
                for key in keys_to_remove:
                    del self.active_states[key]
                
                if self.memory:
                    await self.memory.clear_conversation_state(user_id)
            
            logger.debug(f"Cleared conversation state for user {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to clear conversation state: {e}")
            return False
    
    async def get_all_states(self, user_id: str) -> Dict[str, Any]:
        """Get all conversation states for a user."""
        try:
            user_states = {}
            
            # Get from memory cache
            for key, state in self.active_states.items():
                if key.startswith(f"{user_id}_"):
                    state_type = key.replace(f"{user_id}_", "", 1)
                    user_states[state_type] = state
            
            # Get from persistent storage if memory manager available
            if self.memory:
                persistent_states = await self.memory.get_all_conversation_states(user_id)
                if persistent_states:
                    user_states.update(persistent_states)
            
            return user_states
            
        except Exception as e:
            logger.error(f"Failed to get all conversation states: {e}")
            return {}
    
    def has_active_state(self, user_id: str, state_type: str) -> bool:
        """Check if user has an active conversation state."""
        state_key = f"{user_id}_{state_type}"
        return state_key in self.active_states
    
    async def update_state(self, user_id: str, state_type: str, updates: Dict[str, Any]) -> bool:
        """Update existing conversation state."""
        try:
            current_state = await self.get_state(user_id, state_type)
            
            if current_state:
                # Update the data section
                if 'data' in current_state:
                    current_state['data'].update(updates)
                else:
                    current_state['data'] = updates
                
                # Update timestamp
                current_state['timestamp'] = datetime.utcnow().isoformat()
                
                # Save updated state
                return await self.save_state(user_id, state_type, current_state['data'])
            else:
                # Create new state if doesn't exist
                return await self.save_state(user_id, state_type, updates)
                
        except Exception as e:
            logger.error(f"Failed to update conversation state: {e}")
            return False
    
    def get_state_summary(self, user_id: str) -> Dict[str, Any]:
        """Get a summary of all active states for a user."""
        try:
            active_states_list: List[Dict[str, Any]] = []
            
            summary = {
                'user_id': user_id,
                'active_states': active_states_list,
                'total_states': 0,
                'last_activity': None
            }
            
            user_prefix = f"{user_id}_"
            latest_timestamp = None
            
            for key, state in self.active_states.items():
                if key.startswith(user_prefix):
                    state_type = key.replace(user_prefix, "", 1)
                    timestamp = state.get('timestamp')
                    
                    active_states_list.append({
                        'type': state_type,
                        'timestamp': timestamp,
                        'has_data': bool(state.get('data'))
                    })
                    
                    # Track latest activity
                    if timestamp and (not latest_timestamp or timestamp > latest_timestamp):
                        latest_timestamp = timestamp
            
            summary['total_states'] = len(active_states_list)
            summary['last_activity'] = latest_timestamp
            
            return summary
            
        except Exception as e:
            logger.error(f"Failed to get state summary: {e}")
            return {
                'user_id': user_id,
                'active_states': [],
                'total_states': 0,
                'last_activity': None,
                'error': str(e)
            }

    def is_state_expired(self, state: Dict[str, Any], expiry_minutes: int = 30) -> bool:
        """Check if a conversation state has expired."""
        try:
            # Check both timestamp and expires_at fields
            timestamp_str = state.get('timestamp')
            expires_at = state.get('expires_at')
            
            if not timestamp_str:
                return True
            
            # Parse timestamp - handle different formats
            if isinstance(timestamp_str, str):
                timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
            elif isinstance(timestamp_str, datetime):
                timestamp = timestamp_str
            else:
                return True
            
            # Check against expires_at if provided
            if expires_at:
                if isinstance(expires_at, str):
                    expires_datetime = datetime.fromisoformat(expires_at.replace('Z', '+00:00'))
                elif isinstance(expires_at, datetime):
                    expires_datetime = expires_at
                elif isinstance(expires_at, (int, float)):
                    # Handle Unix timestamp
                    expires_datetime = datetime.fromtimestamp(expires_at)
                else:
                    # Fall back to timestamp + expiry_minutes
                    expires_datetime = timestamp + timedelta(minutes=expiry_minutes)
                
                now = datetime.utcnow()
                return now > expires_datetime
            
            # Default behavior - check timestamp + expiry_minutes
            now = datetime.utcnow()
            time_diff = now - timestamp
            return time_diff > timedelta(minutes=expiry_minutes)
            
        except Exception as e:
            logger.error(f"Error checking state expiry: {e}")
            return True  # Consider expired if we can't parse
    
    def should_clear_state(self, state: Dict[str, Any], message: str) -> bool:
        """Check if user wants to clear/cancel the current state."""
        try:
            message_lower = message.lower().strip()
            
            # Clear state commands
            clear_commands = [
                'cancel', 'stop', 'quit', 'exit', 'abort', 'clear', 'reset',
                'start over', 'new', 'fresh', 'begin again', 'restart'
            ]
            
            # Check for exact matches
            if message_lower in clear_commands:
                return True
            
            # Check for phrases that indicate wanting to start fresh
            clear_phrases = [
                'i want to', 'let me', 'can i', 'how do i', 'help me',
                'what is', 'what are', 'tell me', 'show me', 'explain'
            ]
            
            for phrase in clear_phrases:
                if message_lower.startswith(phrase):
                    return True
            
            # Check if the message is a completely different intent
            # (e.g., asking about balance while in transfer state)
            if any(word in message_lower for word in ['balance', 'history', 'banks', 'help']):
                state_type = state.get('type', '')
                if 'transfer' in state_type and 'balance' in message_lower:
                    return True
                if 'beneficiary' in state_type and 'history' in message_lower:
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error checking if should clear state: {e}")
            return False
    
    def extract_amount_from_message(self, message: str) -> Optional[float]:
        """Extract amount from user message."""
        try:
            message_lower = message.lower().strip()
            
            # Pattern for amounts with 'm' suffix (e.g., "2.5m", "1m" for millions)
            m_pattern = r'(\d+(?:\.\d+)?)\s*m\b'
            m_match = re.search(m_pattern, message_lower)
            if m_match:
                return float(m_match.group(1)) * 1000000
            
            # Pattern for amounts with 'k' suffix (e.g., "5k", "10k")
            k_pattern = r'(\d+(?:\.\d+)?)\s*k\b'
            k_match = re.search(k_pattern, message_lower)
            if k_match:
                return float(k_match.group(1)) * 1000
            
            # Pattern for amounts with naira symbol or currency
            currency_pattern = r'[₦ngn]?\s*(\d+(?:,\d{3})*(?:\.\d{2})?)'
            currency_match = re.search(currency_pattern, message_lower)
            if currency_match:
                amount_str = currency_match.group(1).replace(',', '')
                return float(amount_str)
            
            # Pattern for standalone numbers (be careful not to match account numbers)
            number_pattern = r'\b(\d{1,7})\b'
            number_matches = re.findall(number_pattern, message)
            
            for match in number_matches:
                amount = float(match)
                # Only consider as amount if it's a reasonable transfer amount
                if 10 <= amount <= 1000000:  # Between ₦10 and ₦1M
                    return amount
            
            return None
            
        except Exception as e:
            logger.error(f"Error extracting amount: {e}")
            return None
    
    def extract_confirmation_from_message(self, message: str) -> Optional[str]:
        """Extract confirmation (yes/no) from user message."""
        try:
            message_lower = message.lower().strip()
            
            # Positive confirmations
            positive_patterns = [
                r'\byes\b', r'\byeah\b', r'\byh\b', r'\byep\b', r'\byup\b', r'\by\b',
                r'\bok\b', r'\bokay\b', r'\bconfirm\b', r'\bproceed\b',
                r'\bcontinue\b', r'\bgo\s+ahead\b', r'\bdo\s+it\b',
                r'\bsend\s+it\b', r'\bapprove\b', r'\baccept\b',
                r'\bagree\b', r'\bsure\b', r'\bcorrect\b', r'\bright\b'
            ]
            
            for pattern in positive_patterns:
                if re.search(pattern, message_lower):
                    return 'yes'
            
            # Negative confirmations
            negative_patterns = [
                r'\bno\b', r'\bnope\b', r'\bnah\b', r'\bn\b',
                r'\bcancel\b', r'\bstop\b', r'\babort\b', r'\bquit\b',
                r'\bdon\'?t\b', r'\bwrong\b', r'\bincorrect\b',
                r'\bnot\s+right\b', r'\bnot\s+correct\b'
            ]
            
            for pattern in negative_patterns:
                if re.search(pattern, message_lower):
                    return 'no'
            
            return None
            
        except Exception as e:
            logger.error(f"Error extracting confirmation: {e}")
            return None 