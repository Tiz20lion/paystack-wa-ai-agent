#!/usr/bin/env python3
"""
Amount Converter Utility
Centralized amount conversion between Naira and Kobo.
Uses existing config methods but provides easier interface.
"""

from typing import Union
from app.utils.config import settings
from app.utils.logger import get_logger

logger = get_logger("amount_converter")


class AmountConverter:
    """
    Centralized amount conversion utility.
    Eliminates magic number 100 scattered throughout codebase.
    """
    
    # Constants
    KOBO_PER_NAIRA = 100
    
    @classmethod
    def to_kobo(cls, amount: Union[int, float]) -> int:
        """
        Convert Naira amount to Kobo.
        
        Args:
            amount: Amount in Naira
            
        Returns:
            Amount in Kobo
        """
        return int(amount * cls.KOBO_PER_NAIRA)
    
    @classmethod
    def to_ngn(cls, amount: Union[int, float]) -> float:
        """
        Convert Kobo amount to Naira.
        
        Args:
            amount: Amount in Kobo
            
        Returns:
            Amount in Naira
        """
        return float(amount) / cls.KOBO_PER_NAIRA
    
    @classmethod
    def format_amount(cls, amount: Union[int, float], currency: str = "NGN") -> str:
        """
        Format amount for display.
        
        Args:
            amount: Amount (in Naira if > 10000, otherwise assumed to be in correct unit)
            currency: Currency code (default: NGN)
            
        Returns:
            Formatted amount string
        """
        # If amount is large integer, assume it's in kobo
        if isinstance(amount, int) and amount > 10000:
            amount = cls.to_ngn(amount)
        
        # Use existing config method
        if currency == "NGN":
            return f"₦{amount:,.2f}"
        else:
            return settings.format_amount(cls.to_kobo(amount) if amount < 1000 else int(amount), currency)
    
    @classmethod
    def format_ngn(cls, amount: Union[int, float]) -> str:
        """
        Format Naira amount for display.
        Convenience method for NGN currency.
        
        Args:
            amount: Amount (auto-detects if in kobo or naira)
            
        Returns:
            Formatted amount string with ₦ symbol
        """
        # If amount is large integer, assume it's in kobo
        if isinstance(amount, int) and amount > 10000:
            amount = cls.to_ngn(amount)
        
        return f"₦{amount:,.2f}"

