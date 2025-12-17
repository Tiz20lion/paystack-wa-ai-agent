#!/usr/bin/env python3
"""
MongoDB Atlas Connection Test
Tests the MongoDB Atlas connection using the provided credentials.
"""

import os
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_mongodb_connection():
    """Test MongoDB Atlas connection."""
    
    # Get MongoDB URI from environment or use default
    mongodb_uri = os.getenv('MONGODB_URL', 'mongodb+srv://tizlion:<db_password>@paystackassistant.uukbfbp.mongodb.net/?retryWrites=true&w=majority&appName=paystackassistant')
    
    print("🔍 Testing MongoDB Atlas connection...")
    print(f"📍 URI: {mongodb_uri.replace('<db_password>', '***')}")
    
    try:
        # Create a new client and connect to the server
        client: MongoClient = MongoClient(mongodb_uri, server_api=ServerApi('1'))
        
        # Send a ping to confirm a successful connection
        client.admin.command('ping')
        print("✅ Pinged your deployment. You successfully connected to MongoDB!")
        
        # Test basic operations
        db = client.paystack_assistant
        
        # Test collections
        print("\n📊 Testing database operations...")
        
        # Test conversation collection
        conversations = db.conversations
        test_doc = {
            "user_id": "test_user",
            "message": "test connection",
            "timestamp": "2025-01-08T14:30:00Z"
        }
        
        # Insert test document
        result = conversations.insert_one(test_doc)
        print(f"✅ Inserted test document with ID: {result.inserted_id}")
        
        # Read test document
        found_doc = conversations.find_one({"_id": result.inserted_id})
        if found_doc:
            print(f"✅ Retrieved test document: {found_doc['message']}")
        
        # Clean up test document
        conversations.delete_one({"_id": result.inserted_id})
        print("✅ Cleaned up test document")
        
        # Test recipient cache collection
        recipients = db.recipients
        test_recipient = {
            "user_id": "test_user",
            "account_name": "Test Account",
            "account_number": "1234567890",
            "bank_name": "Test Bank",
            "bank_code": "123"
        }
        
        # Insert test recipient
        result = recipients.insert_one(test_recipient)
        print(f"✅ Inserted test recipient with ID: {result.inserted_id}")
        
        # Clean up test recipient
        recipients.delete_one({"_id": result.inserted_id})
        print("✅ Cleaned up test recipient")
        
        print(f"\n🎉 MongoDB Atlas setup successful!")
        print(f"📝 Database: {db.name}")
        print(f"📋 Available collections: {db.list_collection_names()}")
        
        return True
        
    except Exception as e:
        print(f"❌ MongoDB connection failed: {e}")
        print("\n🔧 Troubleshooting tips:")
        print("1. Check your database password in the connection string")
        print("2. Ensure your IP address is whitelisted in MongoDB Atlas")
        print("3. Verify the cluster is running and accessible")
        print("4. Check your network connectivity")
        return False
    
    finally:
        try:
            client.close()
            print("🔒 Connection closed")
        except:
            pass

def show_mongodb_setup_instructions():
    """Show instructions for setting up MongoDB."""
    print("\n" + "="*60)
    print("📚 MongoDB Atlas Setup Instructions")
    print("="*60)
    print()
    print("1. 🔑 Update your .env file with the correct password:")
    print("   MONGODB_URL=mongodb+srv://tizlion:YOUR_PASSWORD@paystackassistant.uukbfbp.mongodb.net/?retryWrites=true&w=majority&appName=paystackassistant")
    print()
    print("2. 🌐 In MongoDB Atlas dashboard:")
    print("   - Go to Database Access → Database Users")
    print("   - Set/reset password for user 'tizlion'")
    print("   - Go to Network Access → IP Access List")
    print("   - Add your current IP address or use 0.0.0.0/0 for testing")
    print()
    print("3. 🔄 Run this script again after updating the password")
    print()
    print("="*60)

if __name__ == "__main__":
    print("🚀 MongoDB Atlas Connection Test")
    print("="*50)
    
    success = test_mongodb_connection()
    
    if not success:
        show_mongodb_setup_instructions()
    
    print("\n✨ Test completed!") 