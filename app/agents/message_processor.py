#!/usr/bin/env python3
"""
Message Processor Module
Handles message parsing, intent detection, and entity extraction for the Financial Agent.
"""

import re
import logging
from typing import Dict, List, Optional, Any, Tuple
from app.utils.logger import get_logger
from app.utils.bank_resolver import BankResolver

logger = get_logger("message_processor")


class MessageProcessor:
    """Handles message parsing, intent detection, and entity extraction."""
    
    def __init__(self):
        # Enhanced intent patterns for better conversational understanding
        self.intent_patterns = {
            "balance": [r"balance", r"how much.*have(?!.*sent)", r"account balance", r"check balance", r"my money(?!.*sent)", r"wetin dey my account", r"how much money"],
            "transfer": [r"transfer.*to", r"send.*to", r"pay.*to", r"payment.*to", r"\d+k?\s+to", r"send \d+", r"give.*money"],
            "account_resolve": [r"\d{10}\s+\w+", r"resolve", r"check account", r"account.*bank"],
            # Enhanced account + bank + amount patterns (these should be detected first)
            "account_bank_amount_transfer": [
                # Nigerian common formats from chat logs - SPACED ACCOUNT NUMBERS
                r"\b\d{3}\s+\d{3}\s+\d{4}\s+\w+\s+send\s+\d+[km]?\b",          # "818 164 8623 opay send 1190"
                r"\b\w+\s+\d{3}\s+\d{3}\s+\d{4}\s+send\s+\d+[km]?\b",          # "opay 818 164 8623 send 1190"
                r"\b\d{3}\s+\d{3}\s+\d{4}\s+\w+\s+\d+[km]?\b",                 # "818 164 8623 opay 1190"
                r"\b\w+\s+\d{3}\s+\d{3}\s+\d{4}\s+\d+[km]?\b",                 # "opay 818 164 8623 1190"
                r"\bsend\s+\d+[km]?\s+to\s+\d{3}\s+\d{3}\s+\d{4}\s+\w+\b",     # "send 1190 to 818 164 8623 opay"
                r"\btransfer\s+\d+[km]?\s+to\s+\d{3}\s+\d{3}\s+\d{4}\s+\w+\b", # "transfer 1k to 818 164 8623 kuda"
                r"\b\d{3}\s+\d{3}\s+\d{4}\s+\w+\s+transfer\s+\d+[km]?\b",      # "818 164 8623 kuda transfer 1k"
                r"\b\w+\s+\d{3}\s+\d{3}\s+\d{4}\s+transfer\s+\d+[km]?\b",      # "kuda 818 164 8623 transfer 1k"
                r"\bpay\s+\d+[km]?\s+to\s+\d{3}\s+\d{3}\s+\d{4}\s+\w+\b",      # "pay 1k to 818 164 8623 kuda"
                r"\b\d{3}\s+\d{3}\s+\d{4}\s+\w+\s+pay\s+\d+[km]?\b",           # "818 164 8623 kuda pay 1k"
                # Nigerian common formats from chat logs - CONSECUTIVE ACCOUNT NUMBERS
                r"\b\w+\s+\d{10}\s+send\s+\d+[km]?\b",          # "opay 8181648623 send 1190"
                r"\b\d{10}\s+\w+\s+send\s+\d+[km]?\b",          # "8181648623 opay send 1190"
                r"\b\d{10}\s+\w+\s+\d+[km]?\b",                 # "8181648623 opay 1190"
                r"\b\w+\s+\d{10}\s+\d+[km]?\b",                 # "opay 8181648623 1190"
                r"\bsend\s+\d+[km]?\s+to\s+\d{10}\s+\w+\b",     # "send 1190 to 8181648623 opay"
                r"\btransfer\s+\d+[km]?\s+to\s+\d{10}\s+\w+\b", # "transfer 1k to 2014216288 kuda"
                r"\b\d{10}\s+\w+\s+transfer\s+\d+[km]?\b",      # "2014216288 kuda transfer 1k"
                r"\b\w+\s+\d{10}\s+transfer\s+\d+[km]?\b",      # "kuda 2014216288 transfer 1k"
                r"\bpay\s+\d+[km]?\s+to\s+\d{10}\s+\w+\b",      # "pay 1k to 2014216288 kuda"
                r"\b\d{10}\s+\w+\s+pay\s+\d+[km]?\b",           # "2014216288 kuda pay 1k"
                # With currency symbols - SPACED ACCOUNT NUMBERS
                r"\b\w+\s+\d{3}\s+\d{3}\s+\d{4}\s+send\s+₦\d+[km]?\b",         # "opay 818 164 8623 send ₦1190"
                r"\b\d{3}\s+\d{3}\s+\d{4}\s+\w+\s+send\s+₦\d+[km]?\b",         # "818 164 8623 opay send ₦1190"
                r"\bsend\s+₦\d+[km]?\s+to\s+\d{3}\s+\d{3}\s+\d{4}\s+\w+\b",    # "send ₦1190 to 818 164 8623 opay"
                # With currency symbols - CONSECUTIVE ACCOUNT NUMBERS
                r"\b\w+\s+\d{10}\s+send\s+₦\d+[km]?\b",         # "opay 8181648623 send ₦1190"
                r"\b\d{10}\s+\w+\s+send\s+₦\d+[km]?\b",         # "8181648623 opay send ₦1190"
                r"\bsend\s+₦\d+[km]?\s+to\s+\d{10}\s+\w+\b",    # "send ₦1190 to 8181648623 opay"
                # More flexible patterns with spaces - SPACED ACCOUNT NUMBERS
                r"\b\w+\s+\d{3}\s+\d{3}\s+\d{4}\s+send\s+\d+\.\d+[km]?\b",     # "opay 818 164 8623 send 1.5k"
                r"\b\d{3}\s+\d{3}\s+\d{4}\s+\w+\s+send\s+\d+\.\d+[km]?\b",     # "818 164 8623 opay send 1.5k"
                # More flexible patterns with spaces - CONSECUTIVE ACCOUNT NUMBERS
                r"\b\w+\s+\d{10}\s+send\s+\d+\.\d+[km]?\b",     # "opay 8181648623 send 1.5k"
                r"\b\d{10}\s+\w+\s+send\s+\d+\.\d+[km]?\b",     # "8181648623 opay send 1.5k"
            ],
            "confirmation": [
                r"\byes\b", r"\byeah\b", r"\byh\b", r"\byep\b", r"\byup\b", r"\by\b", r"\bconfirm\b", r"\bproceed\b", r"\bcontinue\b", 
                r"\bok\b", r"\bokay\b", r"\bcorrect\b", r"\bsharp\b", r"\bsend\s+it\b",
                r"\bsend\s+the\s+money\b", r"\bdo\s+it\b", r"\bgo\s+ahead\b", r"\bapprove\b",
                r"\baccept\b", r"\bagree\b", r"\bsure\b", r"\bperfect\b", r"\bexact\b"
            ],
            "denial": [r"^no$", r"^cancel$", r"^stop$", r"^abort$", r"don't", r"not.*want", r"not.*looking"],
            "amount_only": [r"^\d+k?$", r"^\d+\s*(naira|₦)?$"],
            "help": [r"help", r"what can you do", r"commands", r"assistance", r"talk.*normal", r"normal.*conversation"],
            "greeting": [
                r"\bhi\b", r"\bhello\b", r"\bhey\b", r"\byo\b", r"\byoo\b", r"\bwassup\b", r"\bwhat's up\b",
                r"^hi there$", r"^hello there$", r"^hey there$", r"^hi$", r"^hello$", r"^hey$", r"^yo$",
                r"good morning", r"good afternoon", r"good evening", r"good day", r"morning", r"afternoon", r"evening",
                r"howdy", r"sup", r"what's good", r"what's happening", r"greetings", r"salutations"
            ],
            "greeting_question": [r"how.*are.*you", r"how.*you.*doing", r"how.*things", r"how.*life", r"how.*your.*day", r"what.*up", r"how are you doing"],
            "greeting_response": [r"good.*morning", r"good.*afternoon", r"good.*evening", r"have.*good.*day", r"nice.*day"],
            "conversational_response": [r"i dey ask you", r"you nko", r"and you", r"you.*dey"],
            "repetition_complaint": [r"already.*told", r"told.*you.*already", r"keep.*asking", r"again.*again", r"stop.*asking"],
            "history": [r"history", r"transactions", r"what.*did", r"what.*happened", r"recent.*activity", r"my.*activity", r"show.*transactions", r"payment.*history"],
            "transfers_sent": [r"transfer.*list", r"money.*sent", r"transfers.*made", r"sent.*money", r"outgoing", r"money.*i.*sent", r"how much.*sent", r"sent.*this.*week", r"sent.*today", r"transfers.*week", r"how much.*transfer", r"transactions.*sent", r"transaction.*sent", r"transactions.*i.*sent", r"sent.*out", r"transactions.*out", r"money.*out", r"transfers.*out", r"what.*sent", r"money.*transfer", r"transfer.*history", r"about.*transactions.*sent", r"how.*about.*transactions", r"how.*about.*my.*transaction.*sent", r"about.*my.*transaction.*sent", r"my.*transaction.*sent", r"transactions.*sent.*out", r"money.*i.*transfer", r"what.*about.*transaction.*sent", r"how.*about.*sent", r"about.*sent", r"transaction.*i.*sent"],
            "people_sent_money": [
                r"who\s+are\s+the\s+people\s+i\s+sent\s+money\s+to",  # Exact match first
                r"who\s+are\s+the\s+people\s+i\s+sent\s+money",      # Without "to"
                r"who.*are.*the.*people.*i.*sent.*money.*to", 
                r"who.*are.*the.*people.*i.*sent.*money",            # Without "to"
                r"who.*did.*i.*send.*money.*to",
                r"people.*i.*sent.*money.*to", 
                r"people.*i.*sent.*money",                           # Without "to"
                r"who.*i.*sent.*money.*to", 
                r"who.*i.*sent.*money",                              # Without "to"
                r"recipients.*i.*sent.*money.*to",
                r"recipients.*i.*sent.*money",                       # Without "to"
                r"who.*received.*money.*from.*me",
                r"list.*people.*i.*sent.*money.*to",
                r"list.*people.*i.*sent.*money",                     # Without "to"
                r"show.*people.*i.*sent.*money.*to",
                r"show.*people.*i.*sent.*money",                     # Without "to"
                r"people.*i.*transferred.*money.*to",
                r"people.*i.*transferred.*money",                    # Without "to"
                r"who.*are.*the.*people.*i.*sent", 
                r"list.*people.*sent", 
                r"show.*people.*sent", 
                r"who.*received.*money", 
                r"money.*to.*who"
            ],
            "nickname_creation": [
                r"remember.*is my.*",
                r".*is my.*plug",
                r".*is my.*guy", 
                r".*is my.*person",
                r".*is my.*friend",
                r".*is my.*contact",
                r".*is my.*babe",
                r".*is my.*sis",
                r".*is my.*bro",
                r"save.*as my.*",
                r"call.*my.*",
                r".*is my.*dealer",
                r".*is my.*supplier",
                r"please remember.*is.*",
                r"remember that.*is.*"
            ],
            "correction": [r"that's not right", r"not correct", r"wrong", r"incorrect", r"that's wrong", r"not right", r"but i.*sent.*money", r"but i.*made.*transfer", r"actually i.*sent", r"i already.*sent", r"i did.*send"],
            "casual_response": [r"^okay$", r"^ok$", r"^alright$", r"^sure$", r"^cool$", r"^nice$", r"^good$", r"^correct$", r"^sharp$"],
            "conversation": [r"talk", r"chat", r"conversation", r"normal", r"casual", r"im.*good", r"i.*am.*good", r"doing.*great", r"im.*fine", r"how.*are.*you.*doing"],
            "complaint": [r"that.*not", r"this.*wrong", r"incorrect", r"missing", r"where.*my", r"i.*did.*but", r"should.*show"],
            "thanks": [r"thank", r"thanks", r"appreciate", r"grateful", r"dalu", r"e se"],
            "beneficiary_mention": [r"saved.*beneficiary", r"saved.*contact", r"i.*have.*saved", r"beneficiary", r"saved.*recipient"],
            "list_beneficiaries": [r"list.*beneficiar", r"show.*beneficiar", r"my.*beneficiar", r"get.*beneficiar", r"beneficiar.*list", r"my.*contacts", r"saved.*contacts", r"who.*saved", r"show.*contacts", r"show.*recipients", r"my.*recipients", r"list.*recipients", r"get.*recipients", r"recipients.*list", r"saved.*recipients", r"show.*me.*recipients", r"show.*me.*my.*recipients"],
            "add_beneficiary": [r"save.*contact", r"add.*beneficiary", r"save.*beneficiary", r"remember.*contact", r"add.*\d{10}.*bank", r"save.*\d{10}.*bank", r"want.*to.*add.*\d{10}", r"add.*to.*saved", r"save.*to.*beneficiary", r"add.*to.*my.*saved", r"want.*add.*to.*saved.*beneficiary", r"add.*\d{10}.*to.*saved", r"save.*\d{10}.*to.*beneficiary", r"i.*want.*to.*add.*\d{10}.*bank.*to.*saved.*beneficiary"],
            "named_transfer_with_account": [r"send.*to\s+[a-zA-Z]+\s+at\s+\d{10}", r"transfer.*to\s+[a-zA-Z]+\s+at\s+\d{10}", r"send.*to\s+[a-zA-Z]+\s+\d{10}"],
            # Make beneficiary_transfer more strict - only match when there's a clear person name and no account numbers
            "beneficiary_transfer": [
                # Custom nickname patterns with "my"
                r"send.*to\s+my\s+[a-zA-Z]+(?:\s+[a-zA-Z]+)*(?!\s*\d)(?!\s+(?:opay|kuda|access|gtb|zenith|uba|first|bank))",
                r"transfer.*to\s+my\s+[a-zA-Z]+(?:\s+[a-zA-Z]+)*(?!\s*\d)(?!\s+(?:opay|kuda|access|gtb|zenith|uba|first|bank))",
                r"pay\s+my\s+[a-zA-Z]+(?:\s+[a-zA-Z]+)*(?!\s*\d)(?!\s+(?:opay|kuda|access|gtb|zenith|uba|first|bank))",
                # Regular name patterns
                r"send.*to\s+[a-zA-Z]{3,}(?!\s*\d)(?!\s+(?:opay|kuda|access|gtb|zenith|uba|first|bank))", 
                r"transfer.*to\s+[a-zA-Z]{3,}(?!\s*\d)(?!\s+(?:opay|kuda|access|gtb|zenith|uba|first|bank))", 
                r"pay\s+[a-zA-Z]{3,}(?!\s*\d)(?!\s+(?:opay|kuda|access|gtb|zenith|uba|first|bank))"
            ]
        }
        
        # Bank mappings now use BankResolver utility (no local storage needed)
    
    def parse_message(self, message: str) -> Tuple[str, Dict[str, Any]]:
        """Enhanced message parsing with better context understanding."""
        logger.info(f"Parsing message: {message}")
        
        message_lower = message.lower().strip()
        entities = {}
        
        # Extract entities first
        entities = self.extract_entities(message)
        
        # Context-aware intent detection
        detected_intents = []
        
        # Check each intent pattern
        for intent, patterns in self.intent_patterns.items():
            for pattern in patterns:
                if re.search(pattern, message_lower, re.IGNORECASE):
                    detected_intents.append(intent)
                    logger.debug(f"✅ Pattern '{pattern}' matched for intent '{intent}' in message: '{message_lower}'")
        
        # Smart intent resolution based on context and priority
        if detected_intents:
            # Priority-based intent selection  
            intent_priority = [
                "repetition_complaint", "denial", "amount_only", 
                "conversational_response", "greeting_response", "greeting_question", "greeting",
                "nickname_creation", "add_beneficiary", "list_beneficiaries", "beneficiary_mention", 
                "named_transfer_with_account", "account_bank_amount_transfer", "account_resolve",
                "people_sent_money", "transfers_sent", "beneficiary_transfer",
                "balance", "history", "transfer", "help", "conversation", 
                "correction", "complaint", "casual_response", "confirmation", "thanks"
            ]
            
            for priority_intent in intent_priority:
                if priority_intent in detected_intents:
                    # Special handling for ambiguous cases
                    if priority_intent == "transfer" and any(denial in detected_intents for denial in ["denial", "conversation"]):
                        return "conversation", entities
                    
                    if priority_intent == "casual_response" and len(message.split()) <= 2:
                        return "casual_response", entities
                    
                    if priority_intent == "confirmation" and any(word in message_lower for word in ["talk", "normal", "conversation"]):
                        return "conversation", entities
                    
                    # Enhanced entity extraction for account_bank_amount_transfer intent
                    if priority_intent == "account_bank_amount_transfer":
                        # Extract all entities: account, bank, and amount
                        account_match = re.search(r'\b(\d{10})\b', message)
                        if account_match:
                            entities['account_number'] = account_match.group(1)
                        
                        # Extract bank name with improved logic
                        bank_mappings = BankResolver.get_all_bank_mappings()
                        for bank_name, bank_code in bank_mappings.items():
                            if bank_name in message.lower():
                                entities['bank_name'] = bank_name
                                entities['bank_code'] = bank_code
                                break
                        
                        # Extract amount with comprehensive patterns
                        amount_value = None
                        amount_patterns = [
                            r'send\s+(\d+(?:\.\d+)?)\s*k\b',   # "send 1k", "send 1.5k"
                            r'send\s+(\d+(?:\.\d+)?)\b',       # "send 1190"
                            r'transfer\s+(\d+(?:\.\d+)?)\s*k\b', # "transfer 1k"
                            r'transfer\s+(\d+(?:\.\d+)?)\b',     # "transfer 1190"
                            r'pay\s+(\d+(?:\.\d+)?)\s*k\b',     # "pay 1k"
                            r'pay\s+(\d+(?:\.\d+)?)\b',         # "pay 1190"
                            r'(\d+(?:\.\d+)?)\s*k\b',           # "1k", "1.5k" 
                            r'₦(\d+(?:\.\d+)?)\s*k\b',          # "₦1k"
                            r'₦(\d+(?:\.\d+)?)\b',              # "₦1190"
                            r'\b(\d{3,7})\b(?!\d)',             # 1190, 1500, etc (not account numbers)
                        ]
                        
                        for pattern in amount_patterns:
                            match = re.search(pattern, message.lower())
                            if match:
                                amount_str = match.group(1)
                                try:
                                    amount_num = float(amount_str)
                                    
                                    # Convert k to thousands
                                    if 'k' in pattern:
                                        amount_num *= 1000
                                    
                                    # Skip if this looks like an account number
                                    if len(amount_str) >= 10:
                                        continue
                                        
                                    # Valid amount range check
                                    if 1 <= amount_num <= 10000000:  # ₦1 to ₦10M
                                        amount_value = int(amount_num)
                                        break
                                except (ValueError, TypeError):
                                    continue
                        
                        if amount_value:
                            entities['amount'] = amount_value
                    
                    logger.info(f"Detected intent: {priority_intent}, entities: {entities}")
                    return priority_intent, entities
        
        # Enhanced context-aware detection for follow-up messages
        time_indicators = ["this", "for", "last", "week", "month", "year", "today", "yesterday", "day", "time"]
        if any(word in message_lower.split() for word in time_indicators):
            logger.info(f"Context-aware detection: treating '{message}' as history request due to time indicators")
            return "history", entities
        
        # If no specific intent found, check if it's a complex query that needs AI
        if any(word in message_lower for word in ["can you", "could you", "please", "summary", "api", "check using"]):
            return "conversation", entities
        
        # Default to conversation for everything else
        logger.info(f"No specific intent detected, falling back to conversation mode")
        return "conversation", entities
    
    def extract_entities(self, message: str) -> Dict[str, Any]:
        """Extract banking entities from message."""
        entities = {}
        message_lower = message.lower()
        
        # Enhanced account number extraction - handle both spaced and non-spaced formats
        # Pattern 1: Standard 10 consecutive digits
        account_match = re.search(r'\b(\d{10})\b', message)
        if account_match:
            entities['account_number'] = account_match.group(1)
        else:
            # Pattern 2: Spaced account numbers (3-3-4 or 4-3-3 format)
            spaced_account_patterns = [
                r'\b(\d{3})\s+(\d{3})\s+(\d{4})\b',  # 818 164 8623
                r'\b(\d{4})\s+(\d{3})\s+(\d{3})\b',  # 8181 648 623
                r'\b(\d{2})\s+(\d{4})\s+(\d{4})\b',  # 81 8164 8623
                r'\b(\d{5})\s+(\d{5})\b',            # 81816 48623
            ]
            
            for pattern in spaced_account_patterns:
                spaced_match = re.search(pattern, message)
                if spaced_match:
                    # Combine all groups to form the account number
                    account_parts = [group for group in spaced_match.groups() if group]
                    full_account = ''.join(account_parts)
                    if len(full_account) == 10:
                        entities['account_number'] = full_account
                        break
        
        # Amount extraction (supports k suffix for thousands and m suffix for millions)
        amount_patterns = [
            r'send\s+(\d+)\b',  # "send 1190" - specific pattern for send commands
            r'transfer\s+(\d+)\b',  # "transfer 1190" - specific pattern for transfer commands
            r'pay\s+(\d+)\b',  # "pay 1190" - specific pattern for pay commands
            r'(\d+(?:\.\d+)?)\s*m\b',  # 2.5m, 1m, etc. (millions)
            r'(\d+(?:\.\d+)?)\s*k\b',  # 5k, 10k, etc. (thousands)
            r'(\d{1,10}(?:,\d{3})*(?:\.\d{2})?)\s*(?:naira|₦)',  # 5000 naira, ₦5000
            r'₦(\d{1,10}(?:,\d{3})*(?:\.\d{2})?)',  # ₦5000
            r'\b(\d{1,7})\b',  # Any 1-7 digit number (but not 10-digit account numbers)
        ]
        
        # Only extract amount if there's clear money context AND it's not conflicting with account number
        money_context = any(word in message_lower for word in ['send', 'transfer', 'pay', 'money', 'naira', '₦', 'k ', 'm ', 'thousand', 'million'])
        beneficiary_context = any(word in message_lower for word in ['add', 'save', 'beneficiary', 'contact', 'recipient'])
        
        if money_context and not beneficiary_context:
            for pattern in amount_patterns:
                amount_match = re.search(pattern, message)
                if amount_match:
                    amount_str = amount_match.group(1).replace(',', '')
                    
                    # Convert to integer for validation
                    try:
                        amount_num = int(float(amount_str))
                    except (ValueError, TypeError):
                        continue
                    
                    # Skip if this looks like an account number (10 digits)
                    if len(amount_str) == 10:
                        continue
                    
                    # Skip if this number is the same as the account number we found
                    if entities.get('account_number') and amount_str in entities['account_number']:
                        continue
                    
                    # For the generic number pattern, be more careful about conflicts
                    if pattern == r'\b(\d{1,7})\b':
                        # Skip if this could be part of an account number or phone number
                        if len(amount_str) >= 6 and entities.get('account_number'):
                            continue
                        # Skip very small amounts that might be typos or codes
                        if amount_num < 10:
                            continue
                    
                    # Check which pattern matched based on the matched string
                    matched_text = amount_match.group(0)
                    
                    # Handle millions (m/M) - check if the matched text contains 'm'
                    if 'm' in matched_text.lower():
                        entities['amount'] = int(float(amount_str) * 1000000)
                    # Handle thousands (k/K) - check if the matched text contains 'k'
                    elif 'k' in matched_text.lower():
                        entities['amount'] = int(float(amount_str) * 1000)
                    else:
                        entities['amount'] = amount_num
                    break
        
        # Bank name extraction
        bank_mappings = BankResolver.get_all_bank_mappings()
        for bank_name, bank_code in bank_mappings.items():
            if bank_name in message_lower:
                entities['bank_name'] = bank_name
                entities['bank_code'] = bank_code
                break
        
        # Generic bank word detection if no specific bank found
        bank_words = re.findall(r'\b(?:bank|gtb|access|first|zenith|uba|fidelity|sterling|union|wema|fcmb|kuda|opay|palmpay|moniepoint|carbon|providus|keystone|polaris)\b', message_lower)
        if bank_words and 'bank_name' not in entities:
            entities['bank_name'] = bank_words[0]
        
        return entities
    
    def extract_nickname_mapping(self, message: str) -> Optional[Dict[str, str]]:
        """Extract nickname mapping from messages like 'remember yinka is my igbo plug'."""
        message_lower = message.lower().strip()
        
        # Patterns to extract nickname mappings
        patterns = [
            # Start-of-message patterns (more specific) - Changed *? to * for greedy matching
            r'^([a-zA-Z]+(?:\s+[a-zA-Z]+)?)\s+is\s+my\s+([a-zA-Z]+(?:\s+[a-zA-Z]+)*)$',
            r'^remember\s+([a-zA-Z]+(?:\s+[a-zA-Z]+)?)\s+is\s+my\s+([a-zA-Z]+(?:\s+[a-zA-Z]+)*)$',
            r'^please\s+remember\s+([a-zA-Z]+(?:\s+[a-zA-Z]+)?)\s+is\s+my\s+([a-zA-Z]+(?:\s+[a-zA-Z]+)*)$',
            r'^save\s+([a-zA-Z]+(?:\s+[a-zA-Z]+)?)\s+as\s+my\s+([a-zA-Z]+(?:\s+[a-zA-Z]+)*)$',
            r'^call\s+([a-zA-Z]+(?:\s+[a-zA-Z]+)?)\s+my\s+([a-zA-Z]+(?:\s+[a-zA-Z]+)*)$',
            # Fallback patterns with stop words
            r'([a-zA-Z]+(?:\s+[a-zA-Z]+)?)\s+is\s+my\s+([a-zA-Z]+(?:\s+[a-zA-Z]+)*)(?:\s+(?:so|and|but|please|now)\b|$)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, message_lower)
            if match:
                recipient_name = match.group(1).strip()  # Preserve original case
                custom_nickname = match.group(2).strip().lower()
                
                # Filter out very generic words
                generic_words = ['person', 'friend', 'contact']
                if custom_nickname not in generic_words and len(recipient_name) >= 2:
                    return {
                        'recipient_name': recipient_name,
                        'custom_nickname': custom_nickname
                    }
        
        return None
    
    def extract_name_from_message(self, message: str) -> Optional[str]:
        """Extract name from transfer message for more natural conversation."""
        message_lower = message.lower()
        
        # Patterns that suggest a name follows
        name_patterns = [
            # Custom nickname patterns (handle "my [nickname]" phrases)
            r'(?:to|for|send(?:\s+money)?\s+to)\s+my\s+([a-zA-Z]+(?:\s+[a-zA-Z]+)*)',
            r'give\s+my\s+([a-zA-Z]+(?:\s+[a-zA-Z]+)*)',
            r'pay\s+my\s+([a-zA-Z]+(?:\s+[a-zA-Z]+)*)',
            # Regular name patterns
            r'(?:to|for|send(?:\s+money)?\s+to)\s+([a-zA-Z]+(?:\s+[a-zA-Z]+)?)(?:\s+at|\s+\d|$)',
            r'give\s+([a-zA-Z]+(?:\s+[a-zA-Z]+)?)\s+',
            r'pay\s+([a-zA-Z]+(?:\s+[a-zA-Z]+)?)\s+',
        ]
        
        for pattern in name_patterns:
            match = re.search(pattern, message_lower)
            if match:
                name = match.group(1).strip()
                # Filter out common words that aren't names
                stop_words = ['money', 'cash', 'naira', 'the', 'this', 'that', 'some', 'him', 'her']
                if name not in stop_words and len(name) >= 2:
                    # Return as-is to preserve custom nickname case
                    return name
        
        return None
    
    def extract_account_details_from_message(self, message: str) -> Optional[Dict]:
        """Extract account number and bank details from user message."""
        try:
            # Look for 10-digit account number
            account_match = re.search(r'\b(\d{10})\b', message)
            if not account_match:
                return None
            
            account_number = account_match.group(1)
            
            # Extract bank name/code from message
            message_lower = message.lower()
            bank_info = None
            
            # Check for bank names/codes in message
            for entity in self.extract_entities(message).get('bank_names', []):
                bank_info = entity
                break
            
            # If no bank detected by entity extraction, try manual detection
            if not bank_info:
                bank_keywords = {
                    'access': {'name': 'Access Bank', 'code': '044'},
                    'gtbank': {'name': 'Guaranty Trust Bank', 'code': '058'},
                    'gtb': {'name': 'Guaranty Trust Bank', 'code': '058'},
                    'uba': {'name': 'United Bank For Africa', 'code': '033'},
                    'zenith': {'name': 'Zenith Bank', 'code': '057'},
                    'first bank': {'name': 'First Bank of Nigeria', 'code': '011'},
                    'fcmb': {'name': 'First City Monument Bank', 'code': '214'},
                    'kuda': {'name': 'Kuda Bank', 'code': '50211'},
                    'opay': {'name': 'Opay', 'code': '999992'},
                }
                
                for keyword, info in bank_keywords.items():
                    if keyword in message_lower:
                        bank_info = info
                        break
            
            if not bank_info:
                return None
            
            return {
                'account_number': account_number,
                'bank_name': bank_info.get('name', 'Unknown Bank'),
                'bank_code': bank_info.get('code', ''),
            }
            
        except Exception as e:
            logger.error(f"Failed to extract account details from message: {e}")
            return None
    
    def _extract_transfer_details(self, message: str) -> Optional[Dict]:
        """Extract transfer details from message (from original financial_agent.py)."""
        try:
            message_lower = message.lower()
            
            # Extract amount
            amount = None
            amount_patterns = [
                r'(\d+(?:\.\d+)?)\s*m\b',  # 2.5m, 1m, etc. (millions)
                r'(\d+(?:\.\d+)?)\s*k\b',  # 5k, 10k, etc. (thousands)
                r'(\d{1,10}(?:,\d{3})*(?:\.\d{2})?)\s*(?:naira|₦)?',  # 5000, 5,000, 5000.00
                r'₦(\d{1,10}(?:,\d{3})*(?:\.\d{2})?)',  # ₦5000
            ]
            
            for pattern in amount_patterns:
                match = re.search(pattern, message)
                if match:
                    amount_str = match.group(1).replace(',', '')
                    # Check which pattern matched based on the matched string
                    matched_text = match.group(0)
                    
                    # Handle millions (m/M) - check if the matched text contains 'm'
                    if 'm' in matched_text.lower():
                        amount = int(float(amount_str) * 1000000)
                    # Handle thousands (k/K) - check if the matched text contains 'k'
                    elif 'k' in matched_text.lower():
                        amount = int(float(amount_str) * 1000)
                    else:
                        amount = int(float(amount_str))
                    break
            
            # Extract account number
            account_match = re.search(r'\b(\d{10})\b', message)
            account_number = account_match.group(1) if account_match else None
            
            # Extract bank name
            bank_name = None
            bank_code = None
            bank_mappings = BankResolver.get_all_bank_mappings()
            for bank, code in bank_mappings.items():
                if bank in message_lower:
                    bank_name = bank
                    bank_code = code
                    break
            
            # Extract recipient name (if present)
            recipient_name = self.extract_name_from_message(message)
            
            if amount and account_number and bank_name:
                return {
                    'amount': amount,
                    'account_number': account_number,
                    'bank_name': bank_name,
                    'bank_code': bank_code,
                    'recipient_name': recipient_name
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to extract transfer details: {e}")
            return None
    
    def _extract_amount_only(self, message: str) -> Optional[float]:
        """Extract amount from message that only contains amount."""
        try:
            message_lower = message.lower().strip()
            
            # Patterns for amount only
            amount_patterns = [
                r'^(\d+(?:\.\d+)?)\s*m\s*$',  # 2.5m, 1m, etc. (millions)
                r'^(\d+(?:\.\d+)?)\s*k\s*$',  # 5k, 10k, etc. (thousands)
                r'^(\d{1,10}(?:,\d{3})*(?:\.\d{2})?)$',  # 5000, 5,000.00
                r'^₦(\d{1,10}(?:,\d{3})*(?:\.\d{2})?)$',  # ₦5000
            ]
            
            for pattern in amount_patterns:
                match = re.search(pattern, message_lower)
                if match:
                    amount_str = match.group(1).replace(',', '')
                    # Check which pattern matched based on the matched string
                    matched_text = match.group(0)
                    
                    # Handle millions (m/M) - check if the matched text contains 'm'
                    if 'm' in matched_text.lower():
                        return float(amount_str) * 1000000
                    # Handle thousands (k/K) - check if the matched text contains 'k'
                    elif 'k' in matched_text.lower():
                        return float(amount_str) * 1000
                    else:
                        return float(amount_str)
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to extract amount: {e}")
            return None
    
    def parse_time_filter(self, message: str) -> tuple:
        """Parse time filter from message (from original financial_agent.py)."""
        try:
            from datetime import datetime, timedelta
            
            message_lower = message.lower()
            today = datetime.now().date()
            
            # Time filter patterns
            if any(word in message_lower for word in ['today', 'today\'s']):
                return today.strftime('%Y-%m-%d'), today.strftime('%Y-%m-%d'), 'today'
            
            elif any(word in message_lower for word in ['yesterday', 'yesterday\'s']):
                yesterday = today - timedelta(days=1)
                return yesterday.strftime('%Y-%m-%d'), yesterday.strftime('%Y-%m-%d'), 'yesterday'
            
            elif any(word in message_lower for word in ['this week', 'week', 'weekly']):
                # Start of week (Monday)
                start_of_week = today - timedelta(days=today.weekday())
                return start_of_week.strftime('%Y-%m-%d'), today.strftime('%Y-%m-%d'), 'this week'
            
            elif any(word in message_lower for word in ['last week', 'previous week']):
                # Last week
                start_of_last_week = today - timedelta(days=today.weekday() + 7)
                end_of_last_week = start_of_last_week + timedelta(days=6)
                return start_of_last_week.strftime('%Y-%m-%d'), end_of_last_week.strftime('%Y-%m-%d'), 'last week'
            
            elif any(word in message_lower for word in ['this month', 'month', 'monthly']):
                # Start of month
                start_of_month = today.replace(day=1)
                return start_of_month.strftime('%Y-%m-%d'), today.strftime('%Y-%m-%d'), 'this month'
            
            elif any(word in message_lower for word in ['last month', 'previous month']):
                # Last month
                first_day_this_month = today.replace(day=1)
                last_day_last_month = first_day_this_month - timedelta(days=1)
                first_day_last_month = last_day_last_month.replace(day=1)
                return first_day_last_month.strftime('%Y-%m-%d'), last_day_last_month.strftime('%Y-%m-%d'), 'last month'
            
            elif any(word in message_lower for word in ['this year', 'year', 'yearly']):
                # Start of year
                start_of_year = today.replace(month=1, day=1)
                return start_of_year.strftime('%Y-%m-%d'), today.strftime('%Y-%m-%d'), 'this year'
            
            # Default: last 7 days
            seven_days_ago = today - timedelta(days=7)
            return seven_days_ago.strftime('%Y-%m-%d'), today.strftime('%Y-%m-%d'), 'last 7 days'
            
        except Exception as e:
            logger.error(f"Failed to parse time filter: {e}")
            # Default fallback
            return None, None, 'recent'
    
    def is_denial_message(self, message: str) -> bool:
        """Check if message is a denial/rejection (from original financial_agent.py)."""
        denial_patterns = [
            r'\bno\b', r'\bnot\b', r'\bdon\'t\b', r'\bwont\b', r'\bwon\'t\b',
            r'\bcancel\b', r'\bstop\b', r'\babort\b', r'\bnevermind\b',
            r'\bnope\b', r'\bnah\b', r'\bna\b'
        ]
        
        message_lower = message.lower()
        return any(re.search(pattern, message_lower) for pattern in denial_patterns)
    
    def is_correction_message(self, message: str) -> bool:
        """Check if message is a correction/dispute (from original financial_agent.py)."""
        correction_patterns = [
            r'that\'s not right', r'not correct', r'wrong', r'incorrect',
            r'that\'s wrong', r'not right', r'i sent', r'i made', r'i did',
            r'but i', r'actually', r'correction', r'fix', r'update'
        ]
        
        message_lower = message.lower()
        return any(re.search(pattern, message_lower) for pattern in correction_patterns)
    
    def is_complaint_message(self, message: str) -> bool:
        """Check if message is a complaint (from original financial_agent.py)."""
        complaint_patterns = [
            r'that.*not', r'this.*wrong', r'incorrect', r'missing',
            r'where.*my', r'i.*did.*but', r'should.*show', r'problem',
            r'issue', r'error', r'mistake', r'confused', r'frustrated'
        ]
        
        message_lower = message.lower()
        return any(re.search(pattern, message_lower) for pattern in complaint_patterns)
    
    def is_repetition_complaint(self, message: str) -> bool:
        """Check if user is complaining about repetition (from original financial_agent.py)."""
        repetition_patterns = [
            r'why.*ask.*again', r'already.*answer', r'i.*told.*you',
            r'you.*ask.*before', r'stop.*repeat', r'don.*answer',
            r'you.*already.*told.*me', r'already.*told.*me',
            r'you.*said.*that.*already', r'just.*told.*me',
            r'you.*just.*said', r'stop.*repeating', r'i.*know.*that',
            r'you.*mentioned.*that', r'duplicate.*message'
        ]
        
        message_lower = message.lower()
        return any(re.search(pattern, message_lower) for pattern in repetition_patterns)
    
    def extract_recipient_name_for_search(self, message: str) -> Optional[str]:
        """Extract recipient name for beneficiary search (from original financial_agent.py)."""
        try:
            message_lower = message.lower()
            
            # Patterns for extracting names after "to" or "for"
            name_patterns = [
                r'(?:to|for)\s+([a-zA-Z]+(?:\s+[a-zA-Z]+)?)',
                r'send\s+(?:money\s+)?to\s+([a-zA-Z]+(?:\s+[a-zA-Z]+)?)',
                r'transfer\s+(?:money\s+)?to\s+([a-zA-Z]+(?:\s+[a-zA-Z]+)?)',
                r'pay\s+([a-zA-Z]+(?:\s+[a-zA-Z]+)?)',
                r'give\s+([a-zA-Z]+(?:\s+[a-zA-Z]+)?)'
            ]
            
            for pattern in name_patterns:
                match = re.search(pattern, message_lower)
                if match:
                    name = match.group(1).strip()
                    # Filter out common words
                    stop_words = ['money', 'cash', 'naira', 'the', 'this', 'that', 'some', 'him', 'her', 'me', 'you']
                    if name not in stop_words and len(name) >= 2:
                        # Return as-is to preserve custom nickname case
                        return name
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to extract recipient name: {e}")
            return None
    
    def is_beneficiary_context(self, message: str) -> bool:
        """Check if message is in beneficiary context (from original financial_agent.py)."""
        beneficiary_keywords = [
            'beneficiary', 'beneficiaries', 'contact', 'contacts',
            'recipient', 'recipients', 'saved', 'list', 'show',
            'add', 'save', 'remember', 'manage'
        ]
        
        message_lower = message.lower()
        return any(keyword in message_lower for keyword in beneficiary_keywords)
    
    def extract_confirmation_type(self, message: str) -> str:
        """Extract type of confirmation from message (from original financial_agent.py)."""
        message_lower = message.lower().strip()
        
        # Strong positive confirmations
        if any(word in message_lower for word in ['yes', 'yeah', 'yep', 'confirm', 'proceed', 'go ahead', 'do it', 'send it']):
            return 'positive'
        
        # Strong negative confirmations
        elif any(word in message_lower for word in ['no', 'nope', 'cancel', 'stop', 'abort', 'don\'t', 'won\'t']):
            return 'negative'
        
        # Neutral/unclear
        else:
            return 'unclear' 