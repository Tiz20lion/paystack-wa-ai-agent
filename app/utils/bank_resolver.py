#!/usr/bin/env python3
"""
Bank Resolver Utility
Centralized bank name to code resolution and vice versa.
This eliminates duplication across multiple handlers.
"""

from typing import Optional, Dict
from app.utils.logger import get_logger

logger = get_logger("bank_resolver")


class BankResolver:
    """
    Centralized bank resolution utility.
    Single source of truth for all bank mappings.
    """
    
    # Comprehensive bank name to code mapping
    # Consolidated from all handlers to ensure consistency
    BANK_MAPPINGS: Dict[str, str] = {
        # GTBank variations
        "gtbank": "058", "gtb": "058", "guarantee trust": "058", "gt bank": "058", 
        "gt": "058", "guaranty trust": "058", "guaranty": "058",
        
        # Access Bank variations
        "access": "044", "access bank": "044", "access bank plc": "044",
        
        # First Bank variations
        "first bank": "011", "firstbank": "011", "first": "011", "fbn": "011",
        
        # Zenith Bank variations
        "zenith": "057", "zenith bank": "057", "zenith bank plc": "057",
        
        # UBA variations
        "uba": "033", "united bank": "033", "united bank for africa": "033",
        
        # Fidelity Bank variations
        "fidelity": "070", "fidelity bank": "070", "fidelity bank plc": "070",
        
        # Sterling Bank variations
        "sterling": "232", "sterling bank": "232", "sterling bank plc": "232",
        
        # Union Bank variations
        "union": "032", "union bank": "032", "union bank of nigeria": "032",
        
        # Wema Bank variations
        "wema": "035", "wema bank": "035", "wema bank plc": "035",
        
        # FCMB variations
        "fcmb": "214", "fcmb bank": "214", "first city": "214", 
        "first city monument bank": "214", "fcmb group": "214",
        
        # Ecobank variations
        "ecobank": "050", "ecobank nigeria": "050", "eco bank": "050",
        
        # Keystone Bank variations
        "keystone": "082", "keystone bank": "082",
        
        # Stanbic IBTC variations
        "stanbic": "221", "stanbic ibtc": "221", "stanbic ibtc bank": "221",
        
        # Heritage Bank variations
        "heritage": "030", "heritage bank": "030",
        
        # Unity Bank variations
        "unity": "215", "unity bank": "215",
        
        # Providus Bank variations
        "providus": "101", "providus bank": "101",
        
        # Suntrust Bank variations
        "suntrust": "100", "suntrust bank": "100",
        
        # Polaris Bank variations
        "polaris": "076", "polaris bank": "076",
        
        # Kuda Bank variations
        "kuda": "50211", "kuda bank": "50211", "kuda microfinance bank": "50211", 
        "kooda": "50211",
        
        # OPay variations
        "opay": "999992", "o-pay": "999992", "opal": "999992", "opera": "999992", 
        "opay bank": "999992", "o pay": "999992",
        
        # Moniepoint variations
        "moniepoint": "50515", "monie point": "50515", "money point": "50515", 
        "moneypoint": "50515", "moniepoint mfb": "50515", 
        "moniepoint microfinance bank": "50515", "monie": "50515", "mp": "50515",
        
        # PalmPay variations
        "palmpay": "999991", "palm pay": "999991", "palm-pay": "999991", 
        "palmpay bank": "999991", "palm": "999991",
        
        # Carbon variations
        "carbon": "565", "carbon bank": "565", "carbon micro": "565",
        
        # Rubies variations
        "rubies": "125", "rubies bank": "125", "rubies mfb": "125",
        
        # VFD variations
        "vfd": "566", "vfd bank": "566", "vfd microfinance bank": "566",
        
        # Mint variations
        "mint": "50304", "mint bank": "50304", "fintech mint": "50304",
        
        # Globus variations
        "globus": "103", "globus bank": "103",
        
        # Parallex variations
        "parallex": "104", "parallex bank": "104",
        
        # Coronation variations
        "coronation": "559", "coronation bank": "559",
        
        # Citi variations
        "citi": "023", "citibank": "023", "citi bank": "023",
        
        # Standard Chartered variations
        "standard chartered": "068", "standard": "068", "scb": "068",
    }
    
    # Bank code to display name mapping
    BANK_CODE_TO_NAME: Dict[str, str] = {
        "044": "Access Bank",
        "058": "GTBank",
        "011": "First Bank",
        "057": "Zenith Bank",
        "033": "UBA",
        "070": "Fidelity Bank",
        "232": "Sterling Bank",
        "032": "Union Bank",
        "035": "Wema Bank",
        "214": "FCMB",
        "50211": "Kuda Bank",
        "999992": "OPay",
        "999991": "PalmPay",
        "50515": "Moniepoint",
        "565": "Carbon",
        "101": "Providus Bank",
        "082": "Keystone Bank",
        "076": "Polaris Bank",
        "050": "Ecobank",
        "221": "Stanbic IBTC",
        "030": "Heritage Bank",
        "215": "Unity Bank",
        "100": "Suntrust Bank",
        "125": "Rubies Bank",
        "566": "VFD Bank",
        "50304": "Mint Bank",
        "103": "Globus Bank",
        "104": "Parallex Bank",
        "559": "Coronation Bank",
        "023": "Citibank",
        "068": "Standard Chartered",
    }
    
    @classmethod
    def resolve_bank_code(cls, bank_name: str) -> Optional[str]:
        """
        Resolve bank code from bank name.
        
        Args:
            bank_name: Bank name (case-insensitive)
            
        Returns:
            Bank code if found, None otherwise
        """
        if not bank_name:
            return None
        
        bank_name_lower = bank_name.lower().strip()
        
        # Direct mapping lookup
        if bank_name_lower in cls.BANK_MAPPINGS:
            return cls.BANK_MAPPINGS[bank_name_lower]
        
        # Fuzzy matching - check if bank name contains any mapped name
        for mapped_name, code in cls.BANK_MAPPINGS.items():
            if mapped_name in bank_name_lower or bank_name_lower in mapped_name:
                logger.debug(f"Fuzzy matched '{bank_name}' to '{mapped_name}' -> {code}")
                return code
        
        logger.warning(f"Could not resolve bank code for: {bank_name}")
        return None
    
    @classmethod
    def get_bank_name(cls, bank_code: str) -> Optional[str]:
        """
        Get display name for bank code.
        
        Args:
            bank_code: Bank code
            
        Returns:
            Bank display name if found, None otherwise
        """
        if not bank_code:
            return None
        
        return cls.BANK_CODE_TO_NAME.get(str(bank_code))
    
    @classmethod
    def get_all_bank_mappings(cls) -> Dict[str, str]:
        """
        Get all bank name to code mappings.
        
        Returns:
            Dictionary of bank name to code mappings
        """
        return cls.BANK_MAPPINGS.copy()
    
    @classmethod
    def get_all_bank_names(cls) -> Dict[str, str]:
        """
        Get all bank code to name mappings.
        
        Returns:
            Dictionary of bank code to name mappings
        """
        return cls.BANK_CODE_TO_NAME.copy()
    
    @classmethod
    def is_valid_bank_code(cls, bank_code: str) -> bool:
        """
        Check if bank code is valid.
        
        Args:
            bank_code: Bank code to validate
            
        Returns:
            True if valid, False otherwise
        """
        return str(bank_code) in cls.BANK_CODE_TO_NAME
    
    @classmethod
    def clean_bank_name(cls, bank_name: str) -> str:
        """
        Clean and normalize bank name for display.
        
        Args:
            bank_name: Raw bank name
            
        Returns:
            Cleaned bank name
        """
        if not bank_name or bank_name.lower() in ['unknown bank', 'unknown', 'none', '']:
            return 'Unknown Bank'
        
        bank_name = bank_name.strip()
        
        # Try to get standardized name from code
        bank_code = cls.resolve_bank_code(bank_name)
        if bank_code:
            display_name = cls.get_bank_name(bank_code)
            if display_name:
                return display_name
        
        # Fallback to title case
        return bank_name.title()

