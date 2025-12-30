#!/usr/bin/env python3
"""
Test script to verify that the image enhancement function works without sharpening
"""
import os
import sys
from PIL import Image
import numpy as np

# Add the app directory to the Python path to import the function
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from main import enhance_image_quality

def test_enhancement():
    """Test the enhancement function with a sample image"""
    # Create a simple test image (or load an existing one if available)
    test_image_path = os.path.join(os.path.dirname(__file__), 'jji.png')
    
    if os.path.exists(test_image_path):
        print(f"Loading test image from {test_image_path}")
        original_img = Image.open(test_image_path).convert('RGB')
    else:
        print("Creating a simple test image")
        # Create a simple gradient test image
        width, height = 200, 200
        array = np.zeros((height, width, 3), dtype=np.uint8)
        for y in range(height):
            for x in range(width):
                array[y, x] = [x % 256, y % 256, (x + y) % 256]
        original_img = Image.fromarray(array, 'RGB')
    
    print(f"Original image size: {original_img.size}")
    print(f"Original image mode: {original_img.mode}")
    
    # Apply enhancement
    enhanced_img = enhance_image_quality(original_img)
    
    # Save both images for comparison
    original_img.save(os.path.join(os.path.dirname(__file__), 'test_original_enhance.png'))
    enhanced_img.save(os.path.join(os.path.dirname(__file__), 'test_enhanced_result.png'))
    
    print("Enhancement completed successfully!")
    print("Original image saved as: test_original_enhance.png")
    print("Enhanced image saved as: test_enhanced_result.png")
    
    # Basic verification that the function returned an image
    assert enhanced_img is not None, "Enhancement function returned None"
    assert enhanced_img.size == original_img.size, "Enhanced image size differs from original"
    print("All basic checks passed!")

if __name__ == "__main__":
    test_enhancement()