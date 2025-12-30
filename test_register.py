#!/usr/bin/env python3
"""
Test script to debug registration issue
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from auth import create_user, UserRegister, create_auth_response

try:
    user_data = UserRegister(email='test@example.com', password='testpass')
    user = create_user(user_data)
    print('User created:', user.email, user.id)
    auth_response = create_auth_response(user)
    print('Auth response created successfully')
    print('Access token:', auth_response.access_token[:20] + '...')
except Exception as e:
    print(f'Error: {e}')
    import traceback
    traceback.print_exc()