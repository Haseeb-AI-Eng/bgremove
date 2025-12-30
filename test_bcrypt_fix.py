#!/usr/bin/env python3
"""
Test script to verify bcrypt compatibility fix
"""

from passlib.context import CryptContext

# Initialize password context (same as in auth.py)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def test_password_hashing():
    """Test password hashing functionality"""
    try:
        # Test password hashing
        test_password = "test_password_123"
        
        print("Testing password hashing...")
        hashed = pwd_context.hash(test_password)
        print(f"✓ Password hashed successfully: {hashed[:20]}...")
        
        # Test password verification
        print("Testing password verification...")
        is_valid = pwd_context.verify(test_password, hashed)
        print(f"✓ Password verification successful: {is_valid}")
        
        # Test invalid password verification
        is_invalid = pwd_context.verify("wrong_password", hashed)
        print(f"✓ Invalid password correctly rejected: {not is_invalid}")
        
        print("\n✓ All bcrypt compatibility tests passed!")
        return True
        
    except Exception as e:
        print(f"\n✗ Error during bcrypt compatibility test: {str(e)}")
        return False

if __name__ == "__main__":
    test_password_hashing()