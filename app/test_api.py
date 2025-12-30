"""
Test script for Image Processing API
Tests all three endpoints with a sample image
"""

import requests
import sys
from pathlib import Path
from PIL import Image
import io

# API base URL
BASE_URL = "https://hintergrundentfernen.ai"

# Create a simple test image (100x100 red square)
def create_test_image():
    """Create a simple test image"""
    img = Image.new('RGB', (100, 100), color='red')
    img_bytes = io.BytesIO()
    img.save(img_bytes, format='PNG')
    img_bytes.seek(0)
    return img_bytes

def test_health():
    """Test health check endpoint"""
    print("\n=== Testing Health Check ===")
    try:
        response = requests.get(f"{BASE_URL}/health")
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.json()}")
        return response.status_code == 200
    except Exception as e:
        print(f"Error: {e}")
        return False

def test_remove_background():
    """Test remove background endpoint"""
    print("\n=== Testing Remove Background ===")
    try:
        img_bytes = create_test_image()
        files = {'file': ('test.png', img_bytes, 'image/png')}
        response = requests.post(f"{BASE_URL}/api/remove-background", files=files)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            # Save the output
            with open('test_output_remove_bg.png', 'wb') as f:
                f.write(response.content)
            print("Output saved to: test_output_remove_bg.png")
            return True
        else:
            print(f"Error: {response.text}")
            return False
    except Exception as e:
        print(f"Error: {e}")
        return False

def test_change_clothes():
    """Test change clothes endpoint (replaces clothes with new clothes image)"""
    print("\n=== Testing Change Clothes ===")
    try:
        # Create two test images - original person image and new clothes image
        original_img_bytes = create_test_image()
        clothes_img_bytes = io.BytesIO()
        clothes_img = Image.new('RGB', (100, 100), color='blue')
        clothes_img.save(clothes_img_bytes, format='PNG')
        clothes_img_bytes.seek(0)

        files = {
            'original_image': ('original.png', original_img_bytes, 'image/png'),
            'new_clothes_image': ('clothes.png', clothes_img_bytes, 'image/png')
        }

        response = requests.post(f"{BASE_URL}/api/change-clothes", files=files)
        print(f"Status Code: {response.status_code}")

        if response.status_code == 200:
            # Save the output
            with open('test_output_clothes.png', 'wb') as f:
                f.write(response.content)
            print("Output saved to: test_output_clothes.png")
            return True
        else:
            print(f"Error: {response.text}")
            return False
    except Exception as e:
        print(f"Error: {e}")
        return False

def test_change_background():
    """Test change background endpoint"""
    print("\n=== Testing Change Background ===")
    try:
        img_bytes = create_test_image()
        files = {'file': ('test.png', img_bytes, 'image/png')}
        data = {'bg_color': 'FF0000'}
        response = requests.post(f"{BASE_URL}/api/change-background", files=files, data=data)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            # Save the output
            with open('test_output_bg.png', 'wb') as f:
                f.write(response.content)
            print("Output saved to: test_output_bg.png")
            return True
        else:
            print(f"Error: {response.text}")
            return False
    except Exception as e:
        print(f"Error: {e}")
        return False

def main():
    """Run all tests"""
    print("Starting Image Processing API Tests...")
    print(f"API URL: {BASE_URL}")
    
    results = {
        "Health Check": test_health(),
        "Remove Background": test_remove_background(),
        "Change Clothes": test_change_clothes(),
        "Change Background": test_change_background(),
    }
    
    print("\n=== Test Results ===")
    for test_name, passed in results.items():
        status = "✓ PASSED" if passed else "✗ FAILED"
        print(f"{test_name}: {status}")
    
    all_passed = all(results.values())
    print(f"\nOverall: {'All tests passed!' if all_passed else 'Some tests failed'}")
    
    return 0 if all_passed else 1

if __name__ == "__main__":
    sys.exit(main())
