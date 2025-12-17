#!/usr/bin/env python3
"""
Smart Memory Manager with Advanced Context and AI Integration
Handles conversation history, banking operations, and context-aware memory management.
"""

import asyncio
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, cast
from collections import defaultdict
from app.utils.logger import get_logger
from app.utils.mongodb_manager import mongodb_manager

logger = get_logger("smart_memory_manager")

class SmartMemoryManager:
    """Enhanced memory manager with comprehensive context storage and AI integration."""
    
    def __init__(self):
        self.mongodb = mongodb_manager
        self.local_cache = {}  # Fallback in-memory cache
        self.context_cache = {}  # Cache for quick context access
        self.conversation_memory = {}  # Short-term conversational memory
        self.user_profiles = {}  # User personality and preference profiles
    
    # Enhanced Conversation Storage
    async def save_conversation_with_context(self, user_id: str, message: str, role: str = "user", 
                                           banking_context: Optional[Dict] = None, 
                                           api_data: Optional[Dict] = None,
                                           intent: Optional[str] = None,
                                           entities: Optional[Dict] = None) -> bool:
        """Save conversation with comprehensive banking context."""
        try:
            # Create comprehensive metadata
            metadata = {
                'intent': intent,
                'entities': entities or {},
                'banking_context': banking_context or {},
                'api_data': api_data or {},
                'timestamp': datetime.utcnow().isoformat(),
                'context_type': 'enhanced'
            }
            
            # Save to database
            await self._save_to_database(user_id, message, role, metadata)
            
            # Update context cache for quick access
            await self._update_context_cache(user_id, message, role, metadata)
            
            logger.debug(f"Saved enhanced conversation for user {user_id} with context")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save conversation with context: {e}")
            return False
    
    async def save_banking_operation(self, user_id: str, operation_type: str, 
                                   operation_data: Dict, result: Dict) -> bool:
        """Save banking operation details for future reference."""
        try:
            # Create banking operation record
            banking_record = {
                'operation_type': operation_type,  # 'balance_check', 'transfer', 'history', etc.
                'operation_data': operation_data,
                'result': result,
                'timestamp': datetime.utcnow().isoformat(),
                'success': result.get('success', False)
            }
            
            # Save as system message with banking metadata
            await self.save_conversation_with_context(
                user_id=user_id,
                message=f"[BANKING_OPERATION: {operation_type}]",
                role="system",
                banking_context=banking_record,
                api_data=result
            )
            
            logger.debug(f"Saved banking operation {operation_type} for user {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save banking operation: {e}")
            return False
    
    async def get_smart_conversation_context(self, user_id: str, query: str, limit: int = 10) -> Dict:
        """Get intelligent conversation context based on user query."""
        try:
            # Get recent conversation history
            conversations = await self.get_conversation_history(user_id, limit)
            
            # Get banking operations context
            banking_ops = await self._get_banking_operations_context(user_id, query)
            
            # Get transaction context
            transaction_context = await self._get_transaction_context(user_id, query)
            
            # Analyze query for context needs
            context_analysis = self._analyze_query_context(query)
            
            return {
                'conversations': conversations,
                'banking_operations': banking_ops,
                'transaction_context': transaction_context,
                'query_analysis': context_analysis,
                'user_preferences': await self._get_user_preferences(user_id),
                'recent_patterns': await self._get_conversation_patterns(user_id)
            }
            
        except Exception as e:
            logger.error(f"Failed to get smart context: {e}")
            return {}
    
    async def enhance_ai_prompt_with_context(self, user_id: str, current_message: str, 
                                           base_prompt: str) -> str:
        """Enhance AI prompt with intelligent context."""
        try:
            # Get smart context
            context = await self.get_smart_conversation_context(user_id, current_message)
            
            # Build enhanced prompt
            enhanced_prompt = base_prompt + "\n\n**CONVERSATION CONTEXT:**\n"
            
            # Add recent conversations
            if context.get('conversations'):
                enhanced_prompt += "Recent conversation:\n"
                for msg in context['conversations'][-3:]:
                    role = msg.get('role', 'unknown')
                    content = msg.get('message', '')[:100]
                    if not content.startswith('['):  # Skip system messages
                        enhanced_prompt += f"- {role.capitalize()}: {content}\n"
            
            # Add banking context
            if context.get('banking_operations'):
                enhanced_prompt += f"\nRecent banking operations:\n"
                for op in context['banking_operations'][-2:]:
                    op_type = op.get('operation_type', 'unknown')
                    success = op.get('success', False)
                    enhanced_prompt += f"- {op_type}: {'✅' if success else '❌'}\n"
            
            # Add transaction context
            if context.get('transaction_context'):
                enhanced_prompt += f"\nTransaction context: {context['transaction_context']}\n"
            
            # Add query analysis
            if context.get('query_analysis'):
                analysis = context['query_analysis']
                if analysis.get('is_follow_up'):
                    enhanced_prompt += f"\n**NOTE: This is a follow-up question about: {analysis.get('topic', 'previous topic')}**\n"
            
            enhanced_prompt += "\n**INSTRUCTIONS:** Use the above context to provide specific, helpful answers. Reference previous conversation when relevant.\n"
            
            return enhanced_prompt
            
        except Exception as e:
            logger.error(f"Failed to enhance prompt with context: {e}")
            return base_prompt
    
    # Enhanced Short-term Conversational Memory
    async def update_conversation_memory(self, user_id: str, message: str, role: str, intent: str = None) -> None:
        """Update short-term conversational memory with topics, names, mood tracking."""
        try:
            if user_id not in self.conversation_memory:
                self.conversation_memory[user_id] = {
                    'topics': [],
                    'mentioned_names': [],
                    'mood_indicators': [],
                    'recent_questions': [],
                    'user_preferences': {},
                    'repetition_tracker': {},
                    'session_context': {
                        'greeting_exchanged': False,
                        'last_banking_action': None,
                        'conversation_flow': []
                    }
                }
            
            memory = self.conversation_memory[user_id]
            message_lower = message.lower()
            
            # Track topics
            await self._extract_and_track_topics(message_lower, memory['topics'])
            
            # Extract and track names
            await self._extract_and_track_names(message, memory['mentioned_names'])
            
            # Track mood indicators
            await self._extract_mood_indicators(message_lower, memory['mood_indicators'])
            
            # Track questions for context
            if role == 'user' and ('?' in message or any(word in message_lower for word in ['what', 'how', 'when', 'where', 'why', 'who'])):
                memory['recent_questions'].append({
                    'question': message[:100],
                    'timestamp': datetime.utcnow().isoformat(),
                    'intent': intent
                })
                # Keep only last 5 questions
                memory['recent_questions'] = memory['recent_questions'][-5:]
            
            # Track repetition
            if role == 'assistant':
                await self._track_repetition(message, memory['repetition_tracker'])
            
            # Update session context
            await self._update_session_context(message_lower, role, intent, memory['session_context'])
            
            # Update conversation flow
            memory['session_context']['conversation_flow'].append({
                'role': role,
                'intent': intent,
                'timestamp': datetime.utcnow().isoformat()
            })
            # Keep only last 10 exchanges
            memory['session_context']['conversation_flow'] = memory['session_context']['conversation_flow'][-10:]
            
            logger.debug(f"Updated conversation memory for user {user_id}")
            
        except Exception as e:
            logger.error(f"Failed to update conversation memory: {e}")
    
    async def _extract_and_track_topics(self, message: str, topics: List[Dict]) -> None:
        """Extract and track conversation topics."""
        topic_keywords = {
            'banking': ['balance', 'money', 'transfer', 'send', 'account', 'bank', 'transaction', 'payment'],
            'greetings': ['hello', 'hi', 'hey', 'good morning', 'good afternoon', 'good evening'],
            'questions': ['what', 'how', 'when', 'where', 'why', 'who', 'can you', 'could you'],
            'thanks': ['thank', 'thanks', 'appreciate', 'grateful'],
            'casual': ['how are you', 'what\'s up', 'how you doing', 'nothing much', 'fine', 'good'],
            'complaints': ['problem', 'issue', 'wrong', 'error', 'not working', 'frustrated'],
            'help': ['help', 'assist', 'support', 'guide', 'explain']
        }
        
        for topic_type, keywords in topic_keywords.items():
            if any(keyword in message for keyword in keywords):
                # Update existing topic or add new one
                existing_topic = next((t for t in topics if t['type'] == topic_type), None)
                if existing_topic:
                    existing_topic['count'] += 1
                    existing_topic['last_mentioned'] = datetime.utcnow().isoformat()
                else:
                    topics.append({
                        'type': topic_type,
                        'count': 1,
                        'first_mentioned': datetime.utcnow().isoformat(),
                        'last_mentioned': datetime.utcnow().isoformat()
                    })
                    
        # Keep only last 10 topics
        topics[:] = topics[-10:]
    
    async def _extract_and_track_names(self, message: str, names: List[Dict]) -> None:
        """Extract and track mentioned names."""
        # Common Nigerian names and banking-related names
        name_patterns = [
            r'\b[A-Z][a-z]+\b',  # Capitalized words (potential names)
        ]
        
        # Banking-related names that users might mention
        banking_names = ['temmy', 'john', 'mary', 'david', 'sarah', 'peter', 'grace', 'james', 'joy']
        
        words = message.split()
        for word in words:
            clean_word = word.strip('.,!?').lower()
            if clean_word in banking_names or (len(clean_word) > 2 and clean_word.isalpha() and clean_word[0].isupper()):
                # Track the name
                existing_name = next((n for n in names if n['name'].lower() == clean_word), None)
                if existing_name:
                    existing_name['count'] += 1
                    existing_name['last_mentioned'] = datetime.utcnow().isoformat()
                else:
                    names.append({
                        'name': clean_word,
                        'count': 1,
                        'first_mentioned': datetime.utcnow().isoformat(),
                        'last_mentioned': datetime.utcnow().isoformat()
                    })
        
        # Keep only last 10 names
        names[:] = names[-10:]
    
    async def _extract_mood_indicators(self, message: str, mood_indicators: List[Dict]) -> None:
        """Extract mood indicators from message."""
        mood_patterns = {
            'positive': ['good', 'great', 'awesome', 'excellent', 'happy', 'satisfied', 'pleased', 'thanks', 'thank you'],
            'negative': ['bad', 'terrible', 'awful', 'frustrated', 'angry', 'disappointed', 'annoyed', 'problem', 'issue'],
            'neutral': ['okay', 'fine', 'alright', 'normal', 'nothing much'],
            'confused': ['confused', 'don\'t understand', 'unclear', 'not sure', 'help me'],
            'excited': ['wow', 'amazing', 'fantastic', 'love it', 'perfect', 'brilliant']
        }
        
        for mood_type, keywords in mood_patterns.items():
            if any(keyword in message for keyword in keywords):
                mood_indicators.append({
                    'mood': mood_type,
                    'timestamp': datetime.utcnow().isoformat(),
                    'context': message[:50]  # Store context for reference
                })
        
        # Keep only last 5 mood indicators
        mood_indicators[:] = mood_indicators[-5:]
    
    async def _track_repetition(self, message: str, repetition_tracker: Dict) -> None:
        """Track repetition to avoid sending the same response."""
        message_key = message.lower()[:100]  # Use first 100 chars as key
        
        if message_key in repetition_tracker:
            repetition_tracker[message_key]['count'] += 1
            repetition_tracker[message_key]['last_used'] = datetime.utcnow().isoformat()
        else:
            repetition_tracker[message_key] = {
                'count': 1,
                'first_used': datetime.utcnow().isoformat(),
                'last_used': datetime.utcnow().isoformat()
            }
        
        # Clean up old entries (keep only last 20)
        if len(repetition_tracker) > 20:
            # Sort by last_used and keep most recent
            sorted_items = sorted(repetition_tracker.items(), key=lambda x: x[1]['last_used'])
            repetition_tracker.clear()
            repetition_tracker.update(dict(sorted_items[-20:]))
    
    async def _update_session_context(self, message: str, role: str, intent: str, session_context: Dict) -> None:
        """Update session context information."""
        if role == 'user':
            if intent == 'greeting' and not session_context['greeting_exchanged']:
                session_context['greeting_exchanged'] = True
            
            if intent in ['balance', 'transfer', 'history', 'beneficiary']:
                session_context['last_banking_action'] = intent
    
    async def get_conversation_memory(self, user_id: str) -> Dict:
        """Get comprehensive conversation memory for AI context."""
        try:
            memory = self.conversation_memory.get(user_id, {})
            
            # Add analysis and insights
            analysis = {
                'session_summary': await self._generate_session_summary(memory),
                'user_mood': await self._analyze_current_mood(memory.get('mood_indicators', [])),
                'conversation_stage': await self._analyze_conversation_stage(memory),
                'topics_discussed': memory.get('topics', []),
                'names_mentioned': memory.get('mentioned_names', []),
                'recent_questions': memory.get('recent_questions', []),
                'repetition_warnings': await self._check_repetition_warnings(memory.get('repetition_tracker', {}))
            }
            
            return {
                'memory': memory,
                'analysis': analysis
            }
            
        except Exception as e:
            logger.error(f"Failed to get conversation memory: {e}")
            return {}
    
    async def _generate_session_summary(self, memory: Dict) -> str:
        """Generate a summary of the current conversation session."""
        if not memory:
            return "New conversation session"
        
        session_context = memory.get('session_context', {})
        topics = memory.get('topics', [])
        
        summary_parts = []
        
        if session_context.get('greeting_exchanged'):
            summary_parts.append("Greeting exchanged")
        
        if session_context.get('last_banking_action'):
            summary_parts.append(f"Last banking action: {session_context['last_banking_action']}")
        
        if topics:
            top_topics = sorted(topics, key=lambda x: x['count'], reverse=True)[:3]
            topic_names = [t['type'] for t in top_topics]
            summary_parts.append(f"Main topics: {', '.join(topic_names)}")
        
        return "; ".join(summary_parts) if summary_parts else "Active conversation"
    
    async def _analyze_current_mood(self, mood_indicators: List[Dict]) -> str:
        """Analyze current user mood from recent indicators."""
        if not mood_indicators:
            return "neutral"
        
        # Get most recent mood
        recent_mood = mood_indicators[-1]['mood']
        
        # Check for patterns
        if len(mood_indicators) >= 2:
            last_two = [m['mood'] for m in mood_indicators[-2:]]
            if all(m in ['positive', 'excited'] for m in last_two):
                return "very positive"
            elif all(m in ['negative', 'frustrated'] for m in last_two):
                return "frustrated"
        
        return recent_mood
    
    async def _analyze_conversation_stage(self, memory: Dict) -> str:
        """Analyze what stage the conversation is in."""
        session_context = memory.get('session_context', {})
        conversation_flow = session_context.get('conversation_flow', [])
        
        if not conversation_flow:
            return "starting"
        
        recent_intents = [f['intent'] for f in conversation_flow[-3:] if f['intent']]
        
        if 'greeting' in recent_intents:
            return "greeting_phase"
        elif any(intent in recent_intents for intent in ['balance', 'transfer', 'history']):
            return "banking_phase"
        elif 'conversation' in recent_intents:
            return "casual_chat"
        else:
            return "ongoing"
    
    async def _check_repetition_warnings(self, repetition_tracker: Dict) -> List[str]:
        """Check for repetition warnings."""
        warnings = []
        
        for message, data in repetition_tracker.items():
            if data['count'] >= 3:
                warnings.append(f"Repeated response: {message[:50]}...")
        
        return warnings
    
    async def should_avoid_repetition(self, user_id: str, potential_response: str) -> bool:
        """Check if we should avoid this response due to repetition."""
        memory = self.conversation_memory.get(user_id, {})
        repetition_tracker = memory.get('repetition_tracker', {})
        
        response_key = potential_response.lower()[:100]
        
        # Avoid if used more than 2 times recently
        if response_key in repetition_tracker:
            return repetition_tracker[response_key]['count'] >= 2
        
        return False
    
    # Private helper methods
    async def _save_to_database(self, user_id: str, message: str, role: str, metadata: Dict):
        """Save to MongoDB with enhanced metadata."""
        if self.mongodb.is_connected():
            result = await self.mongodb.save_conversation(user_id, message, role, metadata)
            if result:
                return True
        
        # Fallback to local cache
        await self._save_to_local_cache(user_id, message, role, metadata)
        return True
    
    async def _save_to_local_cache(self, user_id: str, message: str, role: str, metadata: Dict):
        """Save to local cache as fallback."""
        if user_id not in self.local_cache:
            self.local_cache[user_id] = {"conversations": [], "banking_ops": []}
        
        conversation_entry = {
            "message": message,
            "role": role,
            "timestamp": datetime.utcnow(),
            "metadata": metadata
        }
        
        self.local_cache[user_id]["conversations"].append(conversation_entry)
        
        # Keep only last 100 messages
        if len(self.local_cache[user_id]["conversations"]) > 100:
            self.local_cache[user_id]["conversations"] = \
                self.local_cache[user_id]["conversations"][-100:]
    
    async def _update_context_cache(self, user_id: str, message: str, role: str, metadata: Dict):
        """Update context cache for quick access."""
        if user_id not in self.context_cache:
            self.context_cache[user_id] = {
                'last_operation': None,
                'frequent_actions': {},
                'transaction_mentions': []
            }
        
        cache = self.context_cache[user_id]
        
        # Track banking operations
        if metadata.get('banking_context'):
            cache['last_operation'] = metadata['banking_context']
        
        # Track frequent actions
        intent = metadata.get('intent')
        if intent:
            cache['frequent_actions'][intent] = cache['frequent_actions'].get(intent, 0) + 1
        
        # Track transaction mentions
        if any(word in message.lower() for word in ['₦', 'naira', 'transaction', 'transfer', 'send']):
            cache['transaction_mentions'].append({
                'message': message[:50],
                'timestamp': datetime.utcnow().isoformat(),
                'role': role
            })
            # Keep only last 10
            cache['transaction_mentions'] = cache['transaction_mentions'][-10:]
    
    async def _get_banking_operations_context(self, user_id: str, query: str) -> List[Dict]:
        """Get relevant banking operations context."""
        try:
            conversations = await self.get_conversation_history(user_id, 20)
            banking_ops = []
            
            for msg in conversations:
                if (msg.get('role') == 'system' and 
                    msg.get('message', '').startswith('[BANKING_OPERATION')):
                    
                    banking_context = msg.get('metadata', {}).get('banking_context', {})
                    if banking_context:
                        banking_ops.append(banking_context)
            
            return banking_ops[-5:]  # Last 5 operations
            
        except Exception as e:
            logger.error(f"Failed to get banking operations context: {e}")
            return []
    
    async def _get_transaction_context(self, user_id: str, query: str) -> Optional[str]:
        """Get transaction context relevant to query."""
        try:
            # Check context cache first
            if user_id in self.context_cache:
                cache = self.context_cache[user_id]
                
                # Look for amount mentions in query
                query_lower = query.lower()
                for mention in cache.get('transaction_mentions', []):
                    if any(word in query_lower for word in ['4k', '5k', '3k', 'transaction']):
                        if any(word in mention['message'].lower() for word in ['₦', '4', '5', '3']):
                            return f"Referenced: {mention['message']} (from {mention['timestamp'][:10]})"
            
            # Get from conversations
            conversations = await self.get_conversation_history(user_id, 10)
            
            for msg in conversations:
                if (msg.get('role') == 'system' and 
                    '[Transaction Context]' in msg.get('message', '')):
                    
                    context = msg.get('metadata', {}).get('context', {})
                    if context and context.get('recent_transactions'):
                        # Find relevant transaction
                        for tx in context['recent_transactions']:
                            amount = tx.get('amount', 0)
                            if '4k' in query.lower() and abs(amount - 4000) < 500:
                                return f"₦{amount:,.0f} {tx.get('type', 'transfer')} on {tx.get('date', '')[:10]}"
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get transaction context: {e}")
            return None
    
    def _analyze_query_context(self, query: str) -> Dict:
        """Analyze query to understand context needs."""
        query_lower = query.lower()
        
        analysis = {
            'is_follow_up': False,
            'topic': None,
            'needs_history': False,
            'needs_transaction_data': False,
            'sentiment': 'neutral'
        }
        
        # Check for follow-up indicators
        follow_up_words = ['what', 'which', 'that', 'this', 'it', 'explain']
        if any(word in query_lower for word in follow_up_words):
            analysis['is_follow_up'] = True
        
        # Determine topic
        if any(word in query_lower for word in ['transaction', 'transfer', 'send', 'money']):
            analysis['topic'] = 'transactions'
            analysis['needs_transaction_data'] = True
        elif any(word in query_lower for word in ['balance', 'account', 'how much']):
            analysis['topic'] = 'balance'
        elif any(word in query_lower for word in ['history', 'past', 'before', 'ago']):
            analysis['topic'] = 'history'
            analysis['needs_history'] = True
        
        # Check sentiment
        if any(word in query_lower for word in ['wrong', 'error', 'problem', 'issue', 'confused']):
            analysis['sentiment'] = 'negative'
        elif any(word in query_lower for word in ['good', 'great', 'thanks', 'perfect']):
            analysis['sentiment'] = 'positive'
        
        return analysis
    
    async def _get_user_preferences(self, user_id: str) -> Dict:
        """Get user preferences from conversation patterns."""
        try:
            if user_id in self.context_cache:
                cache = self.context_cache[user_id]
                frequent_actions = cache.get('frequent_actions', {})
                
                # Determine preferred communication style
                preferences = {
                    'frequent_actions': frequent_actions,
                    'preferred_style': 'conversational',  # Default
                    'needs_detailed_responses': False
                }
                
                # Analyze patterns
                if frequent_actions.get('history', 0) > 2:
                    preferences['likes_detailed_info'] = True
                
                if frequent_actions.get('balance', 0) > frequent_actions.get('transfer', 0):
                    preferences['primary_use'] = 'monitoring'
                else:
                    preferences['primary_use'] = 'transactions'
                
                return preferences
            
            return {}
            
        except Exception as e:
            logger.error(f"Failed to get user preferences: {e}")
            return {}
    
    async def _get_conversation_patterns(self, user_id: str) -> Dict:
        """Get conversation patterns for context."""
        try:
            conversations = await self.get_conversation_history(user_id, 20)
            
            # Initialize with explicit type annotations
            question_types: List[str] = []
            common_flows: List[str] = []
            
            patterns = {
                'session_length': len(conversations),
                'question_types': question_types,
                'response_satisfaction': 'unknown',
                'common_flows': common_flows
            }
            
            # Analyze conversation patterns
            for i, msg in enumerate(conversations):
                if msg.get('role') == 'user':
                    message = msg.get('message', '').lower()
                    
                    if '?' in message or any(word in message for word in ['what', 'how', 'when', 'where', 'why']):
                        question_types.append('inquiry')
                    elif any(word in message for word in ['send', 'transfer', 'pay']):
                        question_types.append('action')
                    elif any(word in message for word in ['check', 'show', 'balance']):
                        question_types.append('status')
            
            return patterns
            
        except Exception as e:
            logger.error(f"Failed to get conversation patterns: {e}")
            return {}
    
    # Original methods for compatibility
    async def save_message(self, user_id: str, message: str, role: str = "user", 
                          metadata: Optional[Dict] = None) -> bool:
        """Original save_message method for compatibility."""
        return await self.save_conversation_with_context(
            user_id=user_id,
            message=message,
            role=role,
            banking_context=metadata
        )
    
    async def get_conversation_history(self, user_id: str, limit: int = 20) -> List[Dict]:
        """Get conversation history."""
        try:
            # Try MongoDB first
            if self.mongodb.is_connected():
                history = await self.mongodb.get_conversation_history(user_id, limit)
                if history:
                    return cast(List[Dict[Any, Any]], history)
            
            # Fallback to local cache
            if user_id in self.local_cache and "conversations" in self.local_cache[user_id]:
                conversations = self.local_cache[user_id]["conversations"]
                return conversations[-limit:] if len(conversations) > limit else conversations
            
            return []
            
        except Exception as e:
            logger.error(f"Failed to get conversation history: {e}")
            return []
    
    # State management methods
    async def set_conversation_state(self, user_id: str, state: Dict) -> bool:
        """Set conversation state."""
        try:
            if self.mongodb.is_connected():
                result = await self.mongodb.set_conversation_state(user_id, state)
                return bool(result)
            return True
        except Exception as e:
            logger.error(f"Failed to set conversation state: {e}")
            return False
    
    async def get_conversation_state(self, user_id: str) -> Optional[Dict]:
        """Get conversation state."""
        try:
            if self.mongodb.is_connected():
                return await self.mongodb.get_conversation_state(user_id)
            return None
        except Exception as e:
            logger.error(f"Failed to get conversation state: {e}")
            return None
    
    async def clear_conversation_state(self, user_id: str) -> bool:
        """Clear conversation state."""
        try:
            if self.mongodb.is_connected():
                result = await self.mongodb.clear_conversation_state(user_id)
                return bool(result)
            return True
        except Exception as e:
            logger.error(f"Failed to clear conversation state: {e}")
            return False 