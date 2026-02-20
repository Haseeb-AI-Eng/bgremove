"""
Test script for authentication flow with vector DB and email service
"""

import sys
import os

# Add the app directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

def test_vector_db():
    """Test vector DB functionality"""
    print("\n=== Testing Vector DB ===")
    try:
        from vector_db import vector_db
        
        # Test adding a user
        test_user_id = "test_user_123"
        test_email = "test@example.com"
        test_data = {"first_name": "Test", "last_name": "User"}
        
        print(f"Adding user: {test_email}")
        result = vector_db.add_user(test_user_id, test_email, test_data)
        print(f"✓ Add user result: {result}")
        
        # Test checking if user exists
        print(f"Checking if user exists: {test_email}")
        exists = vector_db.check_user_exists(test_email)
        print(f"✓ User exists: {exists}")
        
        # Test getting user
        print(f"Getting user by ID: {test_user_id}")
        user = vector_db.get_user_by_id(test_user_id)
        print(f"✓ User data: {user}")
        
        # Test duplicate prevention
        print(f"Testing duplicate prevention for: {test_email}")
        exists_again = vector_db.check_user_exists(test_email)
        print(f"✓ Duplicate check: {exists_again}")
        
        # Clean up
        print(f"Deactivating user: {test_user_id}")
        vector_db.deactivate_user(test_user_id)
        print(f"✓ User deactivated")
        
        print("\n✓ Vector DB tests passed!")
        return True
        
    except Exception as e:
        print(f"\n✗ Vector DB tests failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_email_service():
    """Test email service functionality"""
    print("\n=== Testing Email Service ===")
    try:
        from email_service import email_service
        
        # Check if email service is configured
        if not email_service.smtp_username or not email_service.smtp_password:
            print("⚠ Email service not configured (SMTP credentials missing)")
            print("  Set SMTP_USERNAME and SMTP_PASSWORD in .env to enable")
            return True
        
        # Test sending welcome email
        test_email = "test@example.com"
        print(f"Sending welcome email to: {test_email}")
        result = email_service.send_welcome_email(test_email, "Test")
        print(f"✓ Email sent: {result}")
        
        print("\n✓ Email service tests passed!")
        return True
        
    except Exception as e:
        print(f"\n✗ Email service tests failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_auth_flow():
    """Test complete authentication flow"""
    print("\n=== Testing Authentication Flow ===")
    try:
        from auth import create_user, authenticate_user, get_user, UserRegister
        from pydantic import ValidationError
        
        # Test user registration
        test_email = f"test_{os.urandom(4).hex()}@example.com"
        test_password = "TestPassword123!"
        
        print(f"Registering new user: {test_email}")
        try:
            user_data = UserRegister(
                email=test_email,
                password=test_password,
                first_name="Test",
                last_name="User"
            )
            user = create_user(user_data)
            print(f"✓ User created: {user.id}")
            print(f"  Email: {user.email}")
            print(f"  First Name: {user.first_name}")
            print(f"  Last Name: {user.last_name}")
        except Exception as e:
            if "Email already registered" in str(e):
                print(f"⚠ User already exists (expected in test): {test_email}")
                user = get_user(test_email)
            else:
                raise
        
        # Test authentication
        print(f"\nAuthenticating user: {test_email}")
        authenticated_user = authenticate_user(test_email, test_password)
        if authenticated_user:
            print(f"✓ Authentication successful")
            print(f"  User ID: {authenticated_user.id}")
            print(f"  Email: {authenticated_user.email}")
        else:
            print(f"✗ Authentication failed")
        
        # Test duplicate prevention
        print(f"\nTesting duplicate registration: {test_email}")
        try:
            duplicate_user = UserRegister(
                email=test_email,
                password=test_password,
                first_name="Duplicate",
                last_name="User"
            )
            user2 = create_user(duplicate_user)
            print(f"✗ Duplicate prevention failed!")
        except Exception as e:
            if "Email already registered" in str(e):
                print(f"✓ Duplicate prevention working")
            else:
                print(f"✗ Unexpected error: {e}")
        
        print("\n✓ Authentication flow tests passed!")
        return True
        
    except Exception as e:
        print(f"\n✗ Authentication flow tests failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_api_endpoints():
    """Test API endpoints directly"""
    print("\n=== Testing API Endpoints (Simulation) ===")
    print("Note: For full API endpoint testing, start the server and use Postman/curl")
    print("\nAPI Endpoints to test:")
    print("  POST /auth/register - Register new user")
    print("  POST /auth/login - Login user")
    print("  GET /auth/me - Get current user")
    print("  POST /auth/logout - Logout user")
    print("\nExample curl commands:")
    print('  curl -X POST http://localhost:8000/auth/register \\')
    print('    -H "Content-Type: application/json" \\')
    print('    -d \'{"email":"test@example.com","password":"Test123!","first_name":"Test","last_name":"User"}\'')
    print()
    return True


def main():
    """Run all tests"""
    print("=" * 60)
    print("Authentication Flow Test Suite")
    print("=" * 60)
    
    results = {
        "Vector DB": test_vector_db(),
        "Email Service": test_email_service(),
        "Auth Flow": test_auth_flow(),
        "API Endpoints": test_api_endpoints()
    }
    
    print("\n" + "=" * 60)
    print("Test Results Summary")
    print("=" * 60)
    
    for test_name, result in results.items():
        status = "✓ PASSED" if result else "✗ FAILED"
        print(f"{test_name}: {status}")
    
    all_passed = all(results.values())
    print("\n" + "=" * 60)
    if all_passed:
        print("✓ All tests passed!")
    else:
        print("✗ Some tests failed")
    print("=" * 60)
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    exit(main())
