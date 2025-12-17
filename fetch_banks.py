#!/usr/bin/env python3
"""
Bank Fetcher Script for Paystack WhatsApp AI Agent
Fetches all Nigerian banks from Paystack API and saves them to MongoDB.
"""

import asyncio
import sys
import os

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.services.paystack_service import PaystackService
from app.utils.mongodb_manager import MongoDBManager
from app.utils.logger import get_logger

logger = get_logger("bank_fetcher")


async def fetch_and_save_banks():
    """Fetch all Nigerian banks from Paystack and save to MongoDB."""
    try:
        logger.info("🏦 Starting Nigerian banks fetch and save process...")
        
        # Initialize services
        paystack = PaystackService()
        mongodb = MongoDBManager()
        
        # Check MongoDB connection
        if not mongodb.is_connected():
            logger.error("❌ MongoDB is not connected. Please check your connection.")
            return False
        
        # Fetch banks from Paystack API
        logger.info("📡 Fetching banks from Paystack API...")
        banks_data = await paystack.list_banks(currency="NGN")
        
        if not banks_data:
            logger.error("❌ No banks data received from Paystack API")
            return False
        
        logger.info(f"📊 Received {len(banks_data)} banks from Paystack API")
        
        # Save banks to MongoDB
        logger.info("💾 Saving banks to MongoDB...")
        success = await mongodb.save_banks(banks_data)
        
        if success:
            logger.info("✅ Successfully saved all Nigerian banks to database!")
            
            # Display summary
            logger.info("📋 Bank fetch summary:")
            logger.info(f"   • Total banks: {len(banks_data)}")
            
            # Show some example banks
            logger.info("📌 Sample banks saved:")
            for i, bank in enumerate(banks_data[:5]):
                logger.info(f"   {i+1}. {bank['name']} (Code: {bank['code']})")
            
            if len(banks_data) > 5:
                logger.info(f"   ... and {len(banks_data) - 5} more banks")
            
            return True
        else:
            logger.error("❌ Failed to save banks to database")
            return False
            
    except Exception as e:
        logger.error(f"❌ Error in fetch_and_save_banks: {e}")
        return False


async def verify_banks_in_database():
    """Verify that banks were saved correctly in database."""
    try:
        logger.info("🔍 Verifying banks in database...")
        
        mongodb = MongoDBManager()
        
        if not mongodb.is_connected():
            logger.error("❌ MongoDB is not connected for verification")
            return False
        
        # Get all banks from database
        banks = await mongodb.list_all_banks()
        
        if not banks:
            logger.error("❌ No banks found in database")
            return False
        
        logger.info(f"✅ Found {len(banks)} banks in database")
        
        # Test some common bank lookups
        test_codes = ["058", "044", "011", "057", "033"]  # GTBank, Access, First Bank, Zenith, UBA
        test_names = ["GTBank", "Access Bank", "First Bank", "Zenith", "UBA"]
        
        logger.info("🧪 Testing bank lookups:")
        
        for code in test_codes:
            bank = await mongodb.get_bank_by_code(code)
            if bank:
                logger.info(f"   ✅ Code {code}: {bank['name']}")
            else:
                logger.warning(f"   ⚠️ Code {code}: Not found")
        
        for name in test_names:
            bank = await mongodb.get_bank_by_name(name)
            if bank:
                logger.info(f"   ✅ Name '{name}': {bank['name']} (Code: {bank['code']})")
            else:
                logger.warning(f"   ⚠️ Name '{name}': Not found")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Error in verify_banks_in_database: {e}")
        return False


async def main():
    """Main function to run the bank fetcher."""
    try:
        logger.info("🚀 Nigerian Banks Fetcher Starting...")
        logger.info("=" * 50)
        
        # Step 1: Fetch and save banks
        success = await fetch_and_save_banks()
        if not success:
            logger.error("❌ Failed to fetch and save banks")
            return
        
        logger.info("=" * 50)
        
        # Step 2: Verify banks in database
        await verify_banks_in_database()
        
        logger.info("=" * 50)
        logger.info("✅ Nigerian Banks Fetcher Completed Successfully!")
        logger.info("🎉 Your AI agent now has access to all Nigerian banks!")
        
    except Exception as e:
        logger.error(f"❌ Error in main: {e}")


if __name__ == "__main__":
    # Run the async main function
    asyncio.run(main()) 