#!/usr/bin/env python3
"""
Test script to verify the background change logic
"""
from PIL import Image
import numpy as np

def create_test_transparent_image():
    """Create a test image with a semi-transparent background"""
    # Create a 100x100 image
    img = Image.new('RGBA', (100, 100), (255, 255, 255, 0))  # Transparent white background
    
    # Draw a red square in the center (the "subject")
    pixels = img.load()
    for x in range(30, 70):
        for y in range(30, 70):
            # Red subject with full opacity (alpha=255)
            pixels[x, y] = (255, 0, 0, 255)  # Red, fully opaque
    
    # Create some partially transparent edges
    for x in [29, 70]:
        for y in range(30, 70):
            pixels[x, y] = (255, 0, 0, 128)  # Red, half transparent
    for y in [29, 70]:
        for x in range(30, 70):
            pixels[x, y] = (255, 0, 0, 128)  # Red, half transparent
    
    return img

def test_background_change():
    """Test the background change logic"""
    print("Testing background change logic...")
    
    # Create a test transparent image
    transparent_img = create_test_transparent_image()
    print(f"Created transparent image with mode: {transparent_img.mode}")
    
    # Extract alpha channel (this is what will be used as mask)
    alpha_channel = transparent_img.split()[-1]
    print(f"Alpha channel mode: {alpha_channel.mode}")
    
    # Create a colored background (let's use blue)
    bg_color = (0, 0, 255)  # Blue
    background_img = Image.new("RGB", transparent_img.size, bg_color)
    print(f"Created background with color: {bg_color}")
    
    # Paste transparent image onto colored background using alpha as mask
    background_img.paste(transparent_img, mask=alpha_channel)
    
    print("Background change logic executed successfully!")
    
    # Save the result to check
    background_img.save("test_result.png")
    print("Test result saved as test_result.png")
    
    # Also save the original for comparison
    transparent_img.save("test_original.png")
    print("Original test image saved as test_original.png")

if __name__ == "__main__":
    test_background_change()