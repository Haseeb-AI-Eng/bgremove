"""
Enhanced blending module with advanced techniques for realistic clothes replacement
"""
import numpy as np
import cv2
from PIL import Image
import torch
import torch.nn as nn
import torch.nn.functional as F
from scipy import ndimage
from skimage.restoration import inpaint
from skimage import filters


def enhanced_blend_images(person_image, warped_cloth, composition_mask, garment_type='top'):
    """
    Enhanced blending function using multiple advanced techniques
    """
    # Convert to numpy arrays
    person_np = np.array(person_image).astype(np.float32)
    cloth_np = np.array(warped_cloth).astype(np.float32)

    # Ensure mask has same dimensions as images
    h, w = person_np.shape[:2]
    if composition_mask.shape[:2] != (h, w):
        if len(composition_mask.shape) == 2:
            composition_mask = cv2.resize(composition_mask, (w, h))
        else:
            composition_mask = cv2.resize(composition_mask, (w, h))

    # Ensure mask is 3-channel to match image
    if len(composition_mask.shape) == 2:
        mask_3ch = np.stack([composition_mask] * 3, axis=-1)
    else:
        mask_3ch = composition_mask

    # Clamp mask values to [0, 1]
    mask_3ch = np.clip(mask_3ch, 0, 1)

    # Apply enhanced blending techniques
    result = apply_advanced_blending(person_np, cloth_np, mask_3ch, garment_type)
    
    # Ensure result is in correct range and format
    result = np.clip(result, 0, 255).astype(np.uint8)
    result_image = Image.fromarray(result, 'RGB')

    return result_image


def apply_advanced_blending(person_img, cloth_img, mask, garment_type='top'):
    """
    Apply multiple advanced blending techniques for realistic results
    """
    # Step 1: Poisson blending (seamless cloning)
    poisson_result = poisson_blending(person_img, cloth_img, mask)
    
    # Step 2: Color matching to make the new clothes blend with skin/shadow tones
    color_matched_result = color_matching(poisson_result, person_img, mask)
    
    # Step 3: Apply feathering at edges for smoother transitions
    feathered_result = feather_mask_edges(color_matched_result, person_img, mask, feather_radius=8)
    
    # Step 4: Apply shadow adjustment to make clothes look more integrated
    shadow_adjusted_result = adjust_shadows(feathered_result, person_img, mask, garment_type)
    
    # Step 5: Final refinement with bilateral filtering
    final_result = bilateral_refinement(shadow_adjusted_result, person_img, mask)
    
    return final_result


def poisson_blending(person_img, cloth_img, mask):
    """
    Implement Poisson blending for seamless integration
    """
    if len(mask.shape) == 3:
        mask_binary = (mask[:, :, 0] > 0.5).astype(np.uint8)
    else:
        mask_binary = (mask > 0.5).astype(np.uint8)

    # Find the bounding box of the mask
    coords = np.where(mask_binary > 0)
    if len(coords[0]) == 0:
        return person_img  # Return original if no mask area found

    y_min, y_max = coords[0].min(), coords[0].max()
    x_min, x_max = coords[1].min(), coords[1].max()

    # Expand the bounding box slightly for better blending
    margin = 15
    y_min = max(0, y_min - margin)
    y_max = min(person_img.shape[0], y_max + margin)
    x_min = max(0, x_min - margin)
    x_max = min(person_img.shape[1], x_max + margin)

    # Crop images and mask
    crop_person = person_img[y_min:y_max, x_min:x_max].astype(np.float32)
    crop_cloth = cloth_img[y_min:y_max, x_min:x_max].astype(np.float32)
    crop_mask = mask_binary[y_min:y_max, x_min:x_max]

    # Calculate center of the mask area for the seeding point
    mask_coords = np.where(crop_mask > 0)
    if len(mask_coords[0]) > 0:
        center_y = int(np.mean(mask_coords[0]))
        center_x = int(np.mean(mask_coords[1]))

        # Ensure center is within bounds
        center_y = max(0, min(center_y, crop_person.shape[0] - 1))
        center_x = max(0, min(center_x, crop_person.shape[1] - 1))

        # Use OpenCV seamless cloning
        try:
            center = (center_x, center_y)
            source_mask = (crop_mask * 255).astype(np.uint8)
            source_mask = np.stack([source_mask] * 3, axis=-1)  # Make 3-channel

            result_crop = cv2.seamlessClone(
                crop_cloth.astype(np.uint8), 
                crop_person.astype(np.uint8),
                (crop_mask * 255).astype(np.uint8),
                center, 
                cv2.NORMAL_CLONE
            )
            
            # Create result image
            result = person_img.copy().astype(np.float32)
            result[y_min:y_max, x_min:x_max] = result_crop.astype(np.float32)
            return result
        except:
            # If seamless cloning fails, fall back to multi-band blending
            return multi_band_blending(person_img, cloth_img, mask)
    else:
        return person_img


def multi_band_blending(person_img, cloth_img, mask):
    """
    Multi-band blending for smooth transitions
    """
    # Convert mask to float and ensure 3-channel
    if len(mask.shape) == 2:
        mask = np.stack([mask] * 3, axis=-1)
    
    # Number of Gaussian pyramids
    n_levels = 5
    
    # Build Gaussian pyramid for the mask
    gaussian_pyramid = [mask]
    for i in range(n_levels - 1):
        gaussian_pyramid.append(cv2.pyrDown(gaussian_pyramid[i]))
    
    # Build Laplacian pyramids for the images
    laplacian_person = [person_img]
    laplacian_cloth = [cloth_img]
    
    for i in range(n_levels - 1):
        next_person = cv2.pyrDown(laplacian_person[i])
        next_cloth = cv2.pyrDown(laplacian_cloth[i])
        
        person_diff = cv2.pyrUp(next_person, dstsize=(laplacian_person[i].shape[1], laplacian_person[i].shape[0]))
        cloth_diff = cv2.pyrUp(next_cloth, dstsize=(laplacian_cloth[i].shape[1], laplacian_cloth[i].shape[0]))
        
        laplacian_person.append(laplacian_person[i] - person_diff)
        laplacian_cloth.append(laplacian_cloth[i] - cloth_diff)
    
    # Blend pyramids
    blended_pyramid = []
    for i in range(n_levels):
        level_mask = gaussian_pyramid[i]
        level_person = laplacian_person[i]
        level_cloth = laplacian_cloth[i]
        
        blended_level = level_mask * level_cloth + (1 - level_mask) * level_person
        blended_pyramid.append(blended_level)
    
    # Reconstruct the image
    result = blended_pyramid[-1]
    for i in range(n_levels - 2, -1, -1):
        result = cv2.pyrUp(result, dstsize=(blended_pyramid[i].shape[1], blended_pyramid[i].shape[0]))
        result = result + blended_pyramid[i]
    
    return result


def color_matching(result_img, person_img, mask):
    """
    Match colors between the new clothes and the person image
    """
    # Ensure mask is 3-channel
    if len(mask.shape) == 2:
        mask_3ch = np.stack([mask] * 3, axis=-1)
    else:
        mask_3ch = mask

    # Create a region of interest where the mask is active
    roi = mask_3ch > 0.1  # Use 0.1 threshold to include feathering area
    
    # Calculate color statistics in the region
    if np.any(roi):
        # Get the pixels in the masked area
        person_pixels = person_img[roi]
        result_pixels = result_img[roi]
        
        # Calculate mean and std for color correction
        person_mean = np.mean(person_pixels, axis=0)
        person_std = np.std(person_pixels, axis=0)
        
        result_mean = np.mean(result_pixels, axis=0)
        result_std = np.std(result_pixels, axis=0)
        
        # Avoid division by zero
        result_std = np.where(result_std == 0, 1, result_std)
        
        # Apply color transfer formula: ((pixel - mean_target) * (std_source/std_target)) + mean_source
        corrected_pixels = ((result_pixels - result_mean) * (person_std / result_std)) + person_mean
        
        # Clip values to valid range
        corrected_pixels = np.clip(corrected_pixels, 0, 255)
        
        # Create a copy of result image to modify
        corrected_img = result_img.copy()
        corrected_img[roi] = corrected_pixels
        
        return corrected_img
    else:
        return result_img


def feather_mask_edges(result_img, person_img, mask, feather_radius=8):
    """
    Create smooth transitions at mask edges using feathering
    """
    # Ensure mask is 2D for morphological operations
    if len(mask.shape) == 3:
        mask_2d = mask[:, :, 0]
    else:
        mask_2d = mask

    # Create a smooth mask using distance transform
    dt = cv2.distanceTransform((mask_2d * 255).astype(np.uint8), cv2.DIST_L2, 3)
    dt = dt / dt.max()  # Normalize to [0, 1]
    
    # Create feathered mask
    feathered_mask = np.zeros_like(mask_2d)
    # Use a sigmoid-like transition for smooth feathering
    distance_threshold = feather_radius
    transition_width = feather_radius / 2
    
    # Create transition zone
    transition_mask = np.zeros_like(dt)
    transition_mask[dt > distance_threshold] = 1.0
    
    # Create smooth transition
    transition_range = (dt > (distance_threshold - transition_width)) & (dt <= distance_threshold)
    transition_mask[transition_range] = (dt[transition_range] - (distance_threshold - transition_width)) / transition_width
    
    # Combine original mask with transition
    feathered_mask = np.where(dt > distance_threshold, 0, 1)
    feathered_mask = np.where(transition_range, transition_mask, feathered_mask)
    
    # Ensure proper size
    if feathered_mask.shape != mask_2d.shape:
        feathered_mask = cv2.resize(feathered_mask, (mask_2d.shape[1], mask_2d.shape[0]))
    
    # Convert to 3-channel if needed
    if len(mask.shape) == 3:
        feathered_mask_3ch = np.stack([feathered_mask] * 3, axis=-1)
    else:
        feathered_mask_3ch = feathered_mask
    
    # Apply blending
    blended = result_img * feathered_mask_3ch + person_img * (1 - feathered_mask_3ch)
    
    return blended


def adjust_shadows(result_img, person_img, mask, garment_type='top'):
    """
    Adjust shadows to make the new garment look more realistic
    """
    # Calculate luminance of the original image
    person_gray = cv2.cvtColor(person_img.astype(np.uint8), cv2.COLOR_RGB2GRAY).astype(np.float32)
    
    # Get mask for shadow adjustment area
    if len(mask.shape) == 3:
        mask_2d = mask[:, :, 0]
    else:
        mask_2d = mask
    
    # Create a mask of the area around the garment to analyze shadows
    kernel = np.ones((25, 25), np.uint8)
    dilated_mask = cv2.dilate((mask_2d * 255).astype(np.uint8), kernel, iterations=1)
    dilated_mask = dilated_mask.astype(np.float32) / 255.0
    
    # Calculate average luminance inside and outside the garment area
    masked_region = person_gray * mask_2d
    background_region = person_gray * (1 - dilated_mask)
    
    # Calculate mean luminance
    avg_masked_lum = np.mean(masked_region[mask_2d > 0.1]) if np.any(mask_2d > 0.1) else 128
    avg_background_lum = np.mean(background_region[background_region > 0]) if np.any(background_region > 0) else 128
    
    # Adjust luminance based on the difference
    lum_diff = avg_background_lum - avg_masked_lum
    
    # Apply luminance adjustment to the garment area
    result_copy = result_img.copy()
    
    # Convert to HSV for luminance adjustment
    for c in range(3):  # Process each color channel
        channel = result_copy[:, :, c].astype(np.float32)
        
        # Apply luminance adjustment only in the mask area
        adjustment = (channel * 0.1) + (lum_diff * 0.1)  # Subtle adjustment
        channel_adjusted = np.where(mask_2d > 0.1, channel + adjustment, channel)
        
        # Ensure values stay in valid range
        channel_adjusted = np.clip(channel_adjusted, 0, 255)
        result_copy[:, :, c] = channel_adjusted
    
    return result_copy


def bilateral_refinement(result_img, person_img, mask):
    """
    Apply bilateral filtering for final refinement
    """
    # Convert to uint8 for bilateral filtering
    result_uint8 = result_img.astype(np.uint8)
    
    # Apply bilateral filter to reduce noise while preserving edges
    refined = cv2.bilateralFilter(result_uint8, d=9, sigmaColor=75, sigmaSpace=75)
    
    # Blend with original based on mask for targeted refinement
    if len(mask.shape) == 3:
        mask_2d = mask[:, :, 0]
    else:
        mask_2d = mask
    
    # Use the mask to determine how much refinement to apply
    refined_result = result_img * (1 - mask_2d[:, :, np.newaxis]) + refined * mask_2d[:, :, np.newaxis]
    
    return refined_result.astype(np.float32)


def enhanced_difference_detection(original_img, result_img, threshold=30):
    """
    Enhanced difference detection that considers perceptual differences
    """
    original_np = np.array(original_img).astype(np.float32)
    result_np = np.array(result_img).astype(np.float32)
    
    # Calculate standard pixel-wise difference
    pixel_diff = np.mean(np.abs(result_np - original_np))
    
    # Calculate difference in the masked area only
    # This focuses on the garment region
    if hasattr(original_img, 'mask') and original_img.mask is not None:
        masked_diff = np.mean(np.abs(result_np[original_img.mask > 0.5] - 
                                   original_np[original_img.mask > 0.5]))
    else:
        # If no specific mask, use overall difference but weighted
        masked_diff = pixel_diff
    
    # Calculate SSIM-like measure (simplified)
    # This measures structural similarity which is more perceptually meaningful
    original_gray = cv2.cvtColor(original_np.astype(np.uint8), cv2.COLOR_RGB2GRAY).astype(np.float32)
    result_gray = cv2.cvtColor(result_np.astype(np.uint8), cv2.COLOR_RGB2GRAY).astype(np.float32)
    
    # Calculate mean and std of both images
    orig_mean = cv2.GaussianBlur(original_gray, (11, 11), 1.5)
    result_mean = cv2.GaussianBlur(result_gray, (11, 11), 1.5)
    
    orig_var = cv2.GaussianBlur(original_gray ** 2, (11, 11), 1.5) - orig_mean ** 2
    result_var = cv2.GaussianBlur(result_gray ** 2, (11, 11), 1.5) - result_mean ** 2
    cross_covar = cv2.GaussianBlur(original_gray * result_gray, (11, 11), 1.5) - orig_mean * result_mean
    
    # Simplified SSIM calculation
    c1 = (0.01 * 255) ** 2
    c2 = (0.03 * 255) ** 2
    
    numerator = (2 * orig_mean * result_mean + c1) * (2 * cross_covar + c2)
    denominator = (orig_mean ** 2 + result_mean ** 2 + c1) * (orig_var + result_var + c2)
    ssim_map = numerator / (denominator + 1e-8)
    
    # Average SSIM (lower values indicate more difference)
    avg_ssim = np.mean(ssim_map)
    
    # Combine measures for a comprehensive difference score
    # Lower SSIM = higher difference, so we invert
    ssim_diff = 1 - avg_ssim
    combined_diff = (pixel_diff * 0.6) + (ssim_diff * 255 * 0.4)  # Weighted combination
    
    return combined_diff > threshold, combined_diff


def create_enhanced_composition_mask(person_image, parsing_masks, keypoints=None, garment_type='top', 
                                   mask_refinement=True):
    """
    Create enhanced composition mask with better garment-specific focus
    """
    person_np = np.array(person_image)
    h, w = person_np.shape[:2]
    
    # Create base mask based on garment type
    if garment_type == 'top':
        if 'upper' in parsing_masks:
            base_mask = parsing_masks['upper']
        else:
            # Create default torso mask
            base_mask = create_default_torso_mask(person_np)
    elif garment_type == 'bottom':
        if 'lower' in parsing_masks:
            base_mask = parsing_masks['lower']
        else:
            # Create default lower body mask
            base_mask = create_default_lower_body_mask(person_np)
    elif garment_type == 'full':
        # Combine upper and lower
        upper_mask = parsing_masks.get('upper', create_default_torso_mask(person_np))
        lower_mask = parsing_masks.get('lower', create_default_lower_body_mask(person_np))
        base_mask = np.maximum(upper_mask, lower_mask)
    else:
        # Default to upper
        base_mask = parsing_masks.get('upper', create_default_torso_mask(person_np))
    
    # Refine the mask using pose information if available
    if keypoints is not None:
        base_mask = refine_mask_with_pose(base_mask, keypoints, garment_type, h, w)
    
    # Apply advanced refinement if requested
    if mask_refinement:
        base_mask = advanced_garment_mask_refinement(base_mask, person_np)
    
    # Ensure mask has 3 channels to match image
    if len(base_mask.shape) == 2:
        mask_3ch = np.stack([base_mask] * 3, axis=-1)
    else:
        mask_3ch = base_mask
    
    return mask_3ch


def create_default_torso_mask(person_np):
    """Create a default torso mask based on image dimensions"""
    h, w = person_np.shape[:2]
    mask = np.zeros((h, w), dtype=np.float32)
    
    # Create torso area (between shoulders and hips)
    torso_h_start = int(h * 0.25)  # Start from 25% height (neck area)
    torso_h_end = int(h * 0.65)    # End at 65% height (waist area)
    torso_w_start = int(w * 0.3)   # Start at 30% width
    torso_w_end = int(w * 0.7)     # End at 70% width
    mask[torso_h_start:torso_h_end, torso_w_start:torso_w_end] = 1
    
    return mask


def create_default_lower_body_mask(person_np):
    """Create a default lower body mask based on image dimensions"""
    h, w = person_np.shape[:2]
    mask = np.zeros((h, w), dtype=np.float32)
    
    # Create lower body area (hips to feet)
    lower_h_start = int(h * 0.4)   # Start from 40% height (hip area)
    lower_h_end = int(h * 0.9)     # End at 90% height (above feet)
    lower_w_start = int(w * 0.2)   # Start at 20% width
    lower_w_end = int(w * 0.8)     # End at 80% width
    mask[lower_h_start:lower_h_end, lower_w_start:lower_w_end] = 1
    
    return mask


def refine_mask_with_pose(base_mask, keypoints, garment_type, h, w):
    """Refine mask using pose keypoints"""
    # Extract relevant keypoints based on garment type
    if garment_type == 'top':
        # Use neck, shoulders, and upper body keypoints
        keypoint_indices = [1, 2, 5, 8, 11]  # neck, r_shoulder, l_shoulder, r_hip, l_hip
    elif garment_type == 'bottom':
        # Use hip, knee, and ankle keypoints for lower body
        keypoint_indices = [8, 9, 10, 11, 12, 13]  # hips, knees, ankles
    else:  # full body
        keypoint_indices = list(range(len(keypoints)))
    
    # Create mask based on keypoints
    refined_mask = np.zeros((h, w), dtype=np.float32)
    
    valid_keypoints = []
    for idx in keypoint_indices:
        if idx < len(keypoints) and keypoints[idx][2] > 0.1:  # confidence threshold
            valid_keypoints.append(keypoints[idx][:2])
    
    if len(valid_keypoints) >= 3:
        # Create polygon mask using valid keypoints
        pts = np.array(valid_keypoints, dtype=np.int32)
        
        # Ensure points are within image bounds
        pts[:, 0] = np.clip(pts[:, 0], 0, w-1)
        pts[:, 1] = np.clip(pts[:, 1], 0, h-1)
        
        # Draw filled polygon on mask
        cv2.fillPoly(refined_mask, [pts], 1)
        
        # Combine with base mask to preserve detailed segmentation
        refined_mask = np.maximum(refined_mask, base_mask)
    
    # If not enough valid keypoints, return base mask
    if np.sum(refined_mask) == 0:
        refined_mask = base_mask
    
    return refined_mask


def advanced_garment_mask_refinement(mask, image=None):
    """
    Advanced mask refinement using image features
    """
    if mask is None or mask.size == 0:
        return mask

    # Apply morphological operations to smooth the mask
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)

    # Apply Gaussian smoothing for soft edges
    mask = cv2.GaussianBlur(mask, (9, 9), 0)

    # If image is provided, use it to refine the mask boundaries
    if image is not None:
        # Convert mask to uint8 for processing
        mask_uint8 = (mask * 255).astype(np.uint8)
        
        # Find contours to identify main components
        contours, _ = cv2.findContours(mask_uint8, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        if contours:
            # Keep only the largest contour to remove noise
            largest_contour = max(contours, key=cv2.contourArea)
            
            # Create new mask with only the largest contour
            refined_mask = np.zeros_like(mask_uint8)
            cv2.fillPoly(refined_mask, [largest_contour], 255)
            refined_mask = refined_mask.astype(np.float32) / 255.0
            
            return refined_mask

    return mask


if __name__ == "__main__":
    print("Enhanced Blending module ready!")