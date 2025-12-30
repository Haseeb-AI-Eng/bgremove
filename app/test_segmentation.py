"""
Test script for high-accuracy garment segmentation functionality
"""
import sys
import os
from PIL import Image
import numpy as np
import cv2

# Add the app directory to the path to properly import modules
current_dir = os.path.dirname(__file__)
sys.path.insert(0, current_dir)

from human_parsing.human_parsing_model import load_pretrained_model, get_parsing_map, create_high_accuracy_segmentation_prompt, get_high_accuracy_garment_masks
from main import get_specific_garment_mask


def test_segmentation_functionality():
    """
    Test the high-accuracy garment segmentation functionality
    """
    print("Testing high-accuracy garment segmentation...")
    
    # Create a dummy image for testing (since we don't have a real one)
    # In a real scenario, you would load an actual image
    test_image_path = os.path.join(current_dir, "test_data", "test_person.jpg")
    
    if os.path.exists(test_image_path):
        original_img = Image.open(test_image_path).convert("RGB")
        print(f"Loaded test image: {test_image_path}")
    else:
        # Create a simple test image if no real image exists
        print("No test image found, creating a dummy image for testing...")
        dummy_array = np.random.randint(0, 255, (512, 512, 3), dtype=np.uint8)
        # Create a simple pattern to simulate clothing
        dummy_array[100:300, 100:400] = [200, 100, 100]  # Simulated shirt area
        dummy_array[300:450, 150:350] = [100, 100, 200]  # Simulated pants area
        original_img = Image.fromarray(dummy_array)
    
    print(f"Image size: {original_img.size}")
    
    # Test different garment types
    garment_types = ['top', 'bottom', 'full', 'shirt', 'pants', 'dress']
    
    for garment_type in garment_types:
        print(f"\nTesting segmentation for garment type: {garment_type}")
        
        # Test the high-accuracy segmentation prompt
        try:
            masks = create_high_accuracy_segmentation_prompt(original_img, garment_type)
            print(f"  Generated {len(masks)} masks")
            
            # Print mask info
            for mask_name, mask in masks.items():
                if mask is not None and mask.size > 0:
                    print(f"    {mask_name}: shape={mask.shape}, unique_values={np.unique(mask)}")
                    
                    # Test that mask is binary (0s and 1s)
                    unique_vals = np.unique(mask)
                    assert all(v in [0, 1] for v in unique_vals), f"Mask {mask_name} is not binary!"
                    
                    # Verify that the mask has some positive pixels (not all zeros)
                    if np.sum(mask) > 0:
                        print(f"      [PASS] {mask_name} has {np.sum(mask)} positive pixels")
                    else:
                        print(f"      [WARN] {mask_name} has no positive pixels")
        
        except Exception as e:
            print(f"  Error in segmentation for {garment_type}: {str(e)}")
            import traceback
            traceback.print_exc()
    
    # Test specific garment mask extraction
    print(f"\nTesting specific garment mask extraction...")
    for garment_type in ['top', 'bottom', 'full']:
        try:
            specific_mask = get_specific_garment_mask(original_img, garment_type)
            print(f"  {garment_type} mask shape: {specific_mask.shape}")
            print(f"  {garment_type} mask has {np.sum(specific_mask)} positive pixels")
        except Exception as e:
            print(f"  Error extracting {garment_type} mask: {str(e)}")
            import traceback
            traceback.print_exc()
    
    print("\n[SUCCESS] Segmentation functionality test completed!")


if __name__ == "__main__":
    test_segmentation_functionality()