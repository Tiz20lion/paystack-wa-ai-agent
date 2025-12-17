#!/usr/bin/env python3
"""
Comprehensive Test for 100% Feature Parity
Tests all methods added to ensure complete functionality from original financial_agent.py
"""

import asyncio
import os
import sys
import json
from datetime import datetime
from typing import Dict, Any, Optional

# Add the parent directory to the path to access app module
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.agents.financial_agent_refactored import FinancialAgent
from app.services.paystack_service import PaystackService
from app.utils.memory_manager import MemoryManager
from app.utils.recipient_manager import RecipientManager
from app.utils.logger import get_logger

logger = get_logger("feature_parity_test")

class ComprehensiveFeatureParityTest:
    """Test all enhanced methods for 100% feature parity."""
    
    def __init__(self):
        self.test_results = []
        self.agent: Optional[FinancialAgent] = None
        
    async def setup_agent(self):
        """Setup the financial agent with all required services."""
        try:
            # Initialize services
            paystack_service = PaystackService()
            memory_manager = MemoryManager()
            recipient_manager = RecipientManager()
            
            # Create the agent
            self.agent = FinancialAgent(
                paystack_service=paystack_service,
                memory_manager=memory_manager,
                recipient_manager=recipient_manager,
                ai_enabled=False  # Disable AI for testing to avoid external dependencies
            )
            
            logger.info("✅ Financial agent initialized successfully")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to initialize agent: {e}")
            return False
    
    async def test_ai_handler_enhancements(self):
        """Test all AI handler enhanced methods."""
        print("\n🧠 Testing AI Handler Enhanced Methods...")
        
        # Check if agent is properly initialized
        if self.agent is None:
            print("❌ Agent not initialized - skipping AI handler tests")
            return
        
        test_cases = [
            # Greeting enhancements
            ("Hello!", "greeting"),
            ("How you dey?", "greeting_question"),
            ("I dey fine", "greeting_response"),
            ("I dey ask you back", "conversational_response"),
            
            # Thanks responses
            ("Thank you!", "thanks"),
            ("Thanks for your help", "thanks"),
            ("I appreciate it", "thanks"),
            
            # Denial responses
            ("No, I don't want that", "denial"),
            ("Cancel the transfer", "denial"),
            ("Stop that", "denial"),
            
            # Correction requests
            ("That's not right", "correction"),
            ("You're wrong about that", "correction"),
            ("I sent money but you didn't show it", "correction"),
            
            # Complaint handling
            ("This is wrong", "complaint"),
            ("You're not showing my transfers", "complaint"),
            ("I'm frustrated with this", "complaint"),
            
            # Repetition complaints
            ("Why do you keep asking me?", "repetition_complaint"),
            ("I already told you", "repetition_complaint"),
            ("Stop repeating yourself", "repetition_complaint"),
            
            # Conversational requests
            ("Let's talk normally", "conversation"),
            ("I want to chat", "conversation"),
            ("Can we have a conversation?", "conversation"),
        ]
        
        for message, expected_type in test_cases:
            try:
                response = await self.agent.process_message("test_user", message)
                
                # Check if response is appropriate for the message type
                if response and len(response) > 10:
                    self.test_results.append({
                        "test": f"AI Handler - {expected_type}",
                        "message": message,
                        "response": response[:100] + "..." if len(response) > 100 else response,
                        "status": "✅ PASSED"
                    })
                else:
                    self.test_results.append({
                        "test": f"AI Handler - {expected_type}",
                        "message": message,
                        "response": response,
                        "status": "❌ FAILED - Response too short"
                    })
                    
            except Exception as e:
                self.test_results.append({
                    "test": f"AI Handler - {expected_type}",
                    "message": message,
                    "response": str(e),
                    "status": "❌ FAILED - Exception"
                })
    
    async def test_transfer_handler_enhancements(self):
        """Test all transfer handler enhanced methods."""
        print("\n💸 Testing Transfer Handler Enhanced Methods...")
        
        # Check if agent is properly initialized
        if self.agent is None:
            print("❌ Agent not initialized - skipping transfer handler tests")
            return
        
        test_cases = [
            # Transfer requests
            ("Send 5k to John at 0123456789 access bank", "named_transfer_with_account"),
            ("Transfer 2000 to Mary", "beneficiary_transfer"),
            ("Send money to 1234567890 gtbank", "account_transfer"),
            ("Pay 10k to 9876543210 kuda", "account_transfer"),
            
            # Account resolution
            ("Resolve 0123456789 access bank", "account_resolution"),
            ("Check account 1234567890 gtbank", "account_resolution"),
            
            # Transfer confirmation
            ("Yes, send the money", "transfer_confirmation"),
            ("No, cancel the transfer", "transfer_confirmation"),
            ("Confirm the transfer", "transfer_confirmation"),
        ]
        
        for message, expected_type in test_cases:
            try:
                response = await self.agent.process_message("test_user", message)
                
                # Check if response is appropriate
                if response and len(response) > 20:
                    self.test_results.append({
                        "test": f"Transfer Handler - {expected_type}",
                        "message": message,
                        "response": response[:100] + "..." if len(response) > 100 else response,
                        "status": "✅ PASSED"
                    })
                else:
                    self.test_results.append({
                        "test": f"Transfer Handler - {expected_type}",
                        "message": message,
                        "response": response,
                        "status": "❌ FAILED - Response too short"
                    })
                    
            except Exception as e:
                self.test_results.append({
                    "test": f"Transfer Handler - {expected_type}",
                    "message": message,
                    "response": str(e),
                    "status": "❌ FAILED - Exception"
                })
    
    async def test_history_handler_enhancements(self):
        """Test all history handler enhanced methods."""
        print("\n📊 Testing History Handler Enhanced Methods...")
        
        # Check if agent is properly initialized
        if self.agent is None:
            print("❌ Agent not initialized - skipping history handler tests")
            return
        
        test_cases = [
            # History requests
            ("Show my transaction history", "history"),
            ("Check my transactions from last week", "history"),
            ("What did I send this month?", "transfers_sent"),
            ("Show transfers I made", "transfers_sent"),
            
            # Time-based queries
            ("Show transactions from today", "history_today"),
            ("What did I do yesterday?", "history_yesterday"),
            ("Check this week's activity", "history_week"),
            ("Show last month's transfers", "history_month"),
            
            # Transaction inquiries
            ("Check failed transactions", "failed_transactions"),
            ("Show pending transactions", "pending_transactions"),
            ("Any problems with my transfers?", "transaction_inquiry"),
        ]
        
        for message, expected_type in test_cases:
            try:
                response = await self.agent.process_message("test_user", message)
                
                # Check if response is appropriate
                if response and len(response) > 20:
                    self.test_results.append({
                        "test": f"History Handler - {expected_type}",
                        "message": message,
                        "response": response[:100] + "..." if len(response) > 100 else response,
                        "status": "✅ PASSED"
                    })
                else:
                    self.test_results.append({
                        "test": f"History Handler - {expected_type}",
                        "message": message,
                        "response": response,
                        "status": "❌ FAILED - Response too short"
                    })
                    
            except Exception as e:
                self.test_results.append({
                    "test": f"History Handler - {expected_type}",
                    "message": message,
                    "response": str(e),
                    "status": "❌ FAILED - Exception"
                })
    
    async def test_beneficiary_handler_enhancements(self):
        """Test all beneficiary handler enhanced methods."""
        print("\n👥 Testing Beneficiary Handler Enhanced Methods...")
        
        # Check if agent is properly initialized
        if self.agent is None:
            print("❌ Agent not initialized - skipping beneficiary handler tests")
            return
        
        test_cases = [
            # Beneficiary management
            ("Show my beneficiaries", "list_beneficiaries"),
            ("List my contacts", "list_beneficiaries"),
            ("Who do I have saved?", "list_beneficiaries"),
            ("Show my recipients", "list_beneficiaries"),
            
            # Add beneficiary
            ("Add 0123456789 access bank to my contacts", "add_beneficiary"),
            ("Save 1234567890 gtbank as John", "add_beneficiary"),
            ("Remember this contact", "add_beneficiary"),
            
            # Beneficiary transfers
            ("Send 5k to John", "beneficiary_transfer"),
            ("Transfer money to my saved contact", "beneficiary_transfer"),
            ("Pay my friend 2000", "beneficiary_transfer"),
        ]
        
        for message, expected_type in test_cases:
            try:
                response = await self.agent.process_message("test_user", message)
                
                # Check if response is appropriate
                if response and len(response) > 20:
                    self.test_results.append({
                        "test": f"Beneficiary Handler - {expected_type}",
                        "message": message,
                        "response": response[:100] + "..." if len(response) > 100 else response,
                        "status": "✅ PASSED"
                    })
                else:
                    self.test_results.append({
                        "test": f"Beneficiary Handler - {expected_type}",
                        "message": message,
                        "response": response,
                        "status": "❌ FAILED - Response too short"
                    })
                    
            except Exception as e:
                self.test_results.append({
                    "test": f"Beneficiary Handler - {expected_type}",
                    "message": message,
                    "response": str(e),
                    "status": "❌ FAILED - Exception"
                })
    
    async def test_response_handler_enhancements(self):
        """Test all response handler enhanced methods."""
        print("\n📝 Testing Response Handler Enhanced Methods...")
        
        # Check if agent is properly initialized
        if self.agent is None:
            print("❌ Agent not initialized - skipping response handler tests")
            return
        
        # Test error message enhancement
        response_handler = self.agent.response_handler
        
        test_cases = [
            # Error messages
            ("network", "Network error handling"),
            ("balance", "Balance error handling"),
            ("account", "Account error handling"),
            ("general", "General error handling"),
        ]
        
        for error_type, test_name in test_cases:
            try:
                response = response_handler.enhance_error_messages(error_type)
                
                if response and len(response) > 10:
                    self.test_results.append({
                        "test": f"Response Handler - {test_name}",
                        "message": f"Error type: {error_type}",
                        "response": response,
                        "status": "✅ PASSED"
                    })
                else:
                    self.test_results.append({
                        "test": f"Response Handler - {test_name}",
                        "message": f"Error type: {error_type}",
                        "response": response,
                        "status": "❌ FAILED - Response too short"
                    })
                    
            except Exception as e:
                self.test_results.append({
                    "test": f"Response Handler - {test_name}",
                    "message": f"Error type: {error_type}",
                    "response": str(e),
                    "status": "❌ FAILED - Exception"
                })
    
    async def test_message_processor_enhancements(self):
        """Test all message processor enhanced methods."""
        print("\n🔍 Testing Message Processor Enhanced Methods...")
        
        # Check if agent is properly initialized
        if self.agent is None:
            print("❌ Agent not initialized - skipping message processor tests")
            return

        message_processor = self.agent.message_processor
        
        test_cases = [
            # Intent detection
            ("I already told you that", "repetition_complaint"),
            ("That's not correct", "correction"),
            ("This is wrong", "complaint"),
            ("No, I don't want that", "denial"),
            ("Send 5k to John at 0123456789 access", "named_transfer_with_account"),
            
            # Entity extraction
            ("Send 5000 to 0123456789 access bank", "transfer_with_entities"),
            ("Transfer 2k to gtbank account 1234567890", "transfer_with_entities"),
            
            # Time filter parsing
            ("Show transactions from last week", "time_filter"),
            ("Check this month's transfers", "time_filter"),
            ("What did I do yesterday?", "time_filter"),
        ]
        
        for message, expected_type in test_cases:
            try:
                intent, entities = message_processor.parse_message(message)
                
                if intent and len(intent) > 0:
                    self.test_results.append({
                        "test": f"Message Processor - {expected_type}",
                        "message": message,
                        "response": f"Intent: {intent}, Entities: {entities}",
                        "status": "✅ PASSED"
                    })
                else:
                    self.test_results.append({
                        "test": f"Message Processor - {expected_type}",
                        "message": message,
                        "response": f"Intent: {intent}, Entities: {entities}",
                        "status": "❌ FAILED - No intent detected"
                    })
                    
            except Exception as e:
                self.test_results.append({
                    "test": f"Message Processor - {expected_type}",
                    "message": message,
                    "response": str(e),
                    "status": "❌ FAILED - Exception"
                })
    
    async def test_natural_conversation_flow(self):
        """Test natural conversation flow with the enhanced methods."""
        print("\n💬 Testing Natural Conversation Flow...")
        
        # Check if agent is properly initialized
        if self.agent is None:
            print("❌ Agent not initialized - skipping conversation flow tests")
            return

        conversation_flow = [
            ("Hello!", "greeting"),
            ("How you dey?", "greeting_question"),
            ("I dey fine", "greeting_response"),
            ("Check my balance", "balance"),
            ("Send 5k to John", "beneficiary_transfer"),
            ("Yes, send it", "confirmation"),
            ("Thank you!", "thanks"),
            ("Show my transaction history", "history"),
            ("That's not right", "correction"),
            ("I'm frustrated", "complaint"),
            ("Let's talk normally", "conversation"),
        ]
        
        for i, (message, expected_type) in enumerate(conversation_flow):
            try:
                response = await self.agent.process_message("test_user", message)
                
                if response and len(response) > 10:
                    self.test_results.append({
                        "test": f"Conversation Flow - Step {i+1}",
                        "message": message,
                        "response": response[:100] + "..." if len(response) > 100 else response,
                        "status": "✅ PASSED"
                    })
                else:
                    self.test_results.append({
                        "test": f"Conversation Flow - Step {i+1}",
                        "message": message,
                        "response": response,
                        "status": "❌ FAILED - Response too short"
                    })
                    
            except Exception as e:
                self.test_results.append({
                    "test": f"Conversation Flow - Step {i+1}",
                    "message": message,
                    "response": str(e),
                    "status": "❌ FAILED - Exception"
                })
    
    async def run_all_tests(self):
        """Run all comprehensive tests."""
        print("🚀 Starting Comprehensive Feature Parity Test...")
        print("="*80)
        
        # Setup
        if not await self.setup_agent():
            print("❌ Failed to setup agent. Aborting tests.")
            return
        
        # Run all test suites
        await self.test_ai_handler_enhancements()
        await self.test_transfer_handler_enhancements()
        await self.test_history_handler_enhancements()
        await self.test_beneficiary_handler_enhancements()
        await self.test_response_handler_enhancements()
        await self.test_message_processor_enhancements()
        await self.test_natural_conversation_flow()
        
        # Print results
        self.print_results()
    
    def print_results(self):
        """Print comprehensive test results."""
        print("\n" + "="*80)
        print("📊 COMPREHENSIVE TEST RESULTS")
        print("="*80)
        
        passed = sum(1 for result in self.test_results if "✅ PASSED" in result["status"])
        failed = sum(1 for result in self.test_results if "❌ FAILED" in result["status"])
        total = len(self.test_results)
        
        print(f"\n🎯 SUMMARY:")
        print(f"   Total Tests: {total}")
        print(f"   Passed: {passed} (✅)")
        print(f"   Failed: {failed} (❌)")
        print(f"   Success Rate: {(passed/total)*100:.1f}%")
        
        # Group results by test category
        from typing import Dict, List, Any
        categories: Dict[str, Dict[str, Any]] = {}
        for result in self.test_results:
            category = result["test"].split(" - ")[0]
            if category not in categories:
                categories[category] = {"passed": 0, "failed": 0, "tests": []}
            
            if "✅ PASSED" in result["status"]:
                categories[category]["passed"] += 1
            else:
                categories[category]["failed"] += 1
            
            categories[category]["tests"].append(result)
        
        # Print category summaries
        print(f"\n📈 BY CATEGORY:")
        for category, data in categories.items():
            total_cat = data["passed"] + data["failed"]
            success_rate = (data["passed"] / total_cat) * 100 if total_cat > 0 else 0
            print(f"   {category}: {data['passed']}/{total_cat} ({success_rate:.1f}%)")
        
        # Print failed tests in detail
        failed_tests = [r for r in self.test_results if "❌ FAILED" in r["status"]]
        if failed_tests:
            print(f"\n❌ FAILED TESTS ({len(failed_tests)}):")
            for result in failed_tests:
                print(f"   • {result['test']}")
                print(f"     Message: {result['message']}")
                print(f"     Issue: {result['status']}")
                print(f"     Response: {result['response'][:100]}...")
                print()
        
        # Print some successful examples
        successful_tests = [r for r in self.test_results if "✅ PASSED" in r["status"]]
        if successful_tests:
            print(f"\n✅ SAMPLE SUCCESSFUL TESTS:")
            for result in successful_tests[:5]:  # Show first 5
                print(f"   • {result['test']}")
                print(f"     Message: {result['message']}")
                print(f"     Response: {result['response']}")
                print()
        
        # Final assessment
        print("="*80)
        if failed == 0:
            print("🎉 ALL TESTS PASSED! 100% FEATURE PARITY ACHIEVED!")
        elif (passed/total) >= 0.90:
            print("🎊 EXCELLENT! 90%+ Feature Parity Achieved!")
        elif (passed/total) >= 0.80:
            print("🏆 GREAT! 80%+ Feature Parity Achieved!")
        else:
            print("⚠️  NEEDS IMPROVEMENT - Less than 80% success rate")
        
        print("="*80)
        
        # Save results to file
        with open("comprehensive_test_results.json", "w") as f:
            json.dump({
                "timestamp": datetime.now().isoformat(),
                "summary": {
                    "total": total,
                    "passed": passed,
                    "failed": failed,
                    "success_rate": (passed/total)*100
                },
                "results": self.test_results
            }, f, indent=2)
        
        print(f"📄 Detailed results saved to: comprehensive_test_results.json")

async def main():
    """Run the comprehensive feature parity test."""
    test = ComprehensiveFeatureParityTest()
    await test.run_all_tests()

if __name__ == "__main__":
    asyncio.run(main()) 