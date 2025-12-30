"""
Post-Processing Module
Handles color matching, shadow addition, edge matting, and final blending
"""
import numpy as np
import cv2
from PIL import Image, ImageFilter, ImageEnhance
from scipy import ndimage
from skimage import filters, segmentation, morphology
from skimage.morphology import disk
from skimage.restoration import inpaint
import math


def color_transfer(source_image, target_image, mask=None):
    """
    Transfer color characteristics from source to target image
    """
    # Convert images to numpy arrays
    source = np.array(source_image).astype(np.float32)
    target = np.array(target_image).astype(np.float32)
    
    # If mask is provided, only adjust colors in masked region
    if mask is not None:
        mask = np.array(mask).astype(np.float32)
        if len(mask.shape) == 2:
            mask = np.stack([mask] * 3, axis=-1)
        
        # Calculate statistics only in the masked region
        mask_bool = mask > 0.5
        source_region = source[mask_bool]
        target_region = target[mask_bool]
        
        if len(source_region) > 0 and len(target_region) > 0:
            # Calculate mean and std for both regions
            src_mean = np.mean(source_region, axis=0)
            src_std = np.std(source_region, axis=0) + 1e-6
            tgt_mean = np.mean(target_region, axis=0)
            tgt_std = np.std(target_region, axis=0) + 1e-6
            
            # Normalize target region
            normalized = (target_region - tgt_mean) / tgt_std
            # Match source statistics
            adjusted = normalized * src_std + src_mean
            adjusted = np.clip(adjusted, 0, 255)
            
            # Apply adjustment to target image
            result = target.copy()
            result[mask_bool] = adjusted
        else:
            result = target
    else:
        # Calculate statistics for entire images
        src_mean = np.mean(source, axis=(0, 1))
        src_std = np.std(source, axis=(0, 1)) + 1e-6
        tgt_mean = np.mean(target, axis=(0, 1))
        tgt_std = np.std(target, axis=(0, 1)) + 1e-6
        
        # Normalize target image
        normalized = (target - tgt_mean) / tgt_std
        # Match source statistics
        result = normalized * src_std + src_mean
        result = np.clip(result, 0, 255)
    
    return Image.fromarray(result.astype(np.uint8), 'RGB')


def add_shadows(image, mask, light_direction=(1, 1, 1)):
    """
    Add realistic shadows to the garment based on its shape and position
    """
    # Convert to numpy
    img_np = np.array(image)
    mask_np = np.array(mask).astype(np.float32)
    
    # Ensure mask is single channel
    if len(mask_np.shape) == 3:
        mask_np = mask_np[:, :, 0]
    
    # Normalize mask to [0, 1]
    mask_np = mask_np / 255.0
    
    # Create shadow effect based on mask edges
    # Use morphological operations to create shadow areas
    kernel = np.ones((3, 3), np.uint8)
    eroded_mask = cv2.erode((mask_np * 255).astype(np.uint8), kernel, iterations=1)
    shadow_mask = (mask_np * 255).astype(np.uint8) - eroded_mask
    
    # Blur the shadow to make it softer
    shadow_mask = cv2.GaussianBlur(shadow_mask.astype(np.float32), (5, 5), 0)
    shadow_mask = shadow_mask / 255.0
    
    # Darken the areas where shadows should appear
    shadow_effect = np.zeros_like(img_np, dtype=np.float32)
    shadow_effect[:, :, 0] = img_np[:, :, 0] * 0.7  # Red channel darker
    shadow_effect[:, :, 1] = img_np[:, :, 1] * 0.7  # Green channel darker
    shadow_effect[:, :, 2] = img_np[:, :, 2] * 0.8  # Blue channel slightly less dark
    
    # Apply shadow only in the calculated shadow areas
    result = img_np.astype(np.float32)
    for c in range(3):  # Apply to each channel
        result[:, :, c] = result[:, :, c] * (1 - shadow_mask * 0.3)  # Reduce brightness by 30% in shadow areas
    
    result = np.clip(result, 0, 255).astype(np.uint8)
    
    return Image.fromarray(result, 'RGB')


def edge_matting(image, mask, small_kernel_size=3, large_kernel_size=10):
    """
    Apply edge matting to create smooth transitions at garment edges
    """
    # Convert to numpy arrays
    img_np = np.array(image).astype(np.float32)
    mask_np = np.array(mask).astype(np.float32)
    
    # Ensure mask is single channel
    if len(mask_np.shape) == 3:
        mask_np = mask_np[:, :, 0]
    
    # Normalize mask to [0, 1]
    mask_np = mask_np / 255.0
    
    # Find the unknown region around the edges
    # First, get the binary mask
    binary_mask = (mask_np > 0.5).astype(np.uint8)
    
    # Erode and dilate to find the edge region
    small_kernel = np.ones((small_kernel_size, small_kernel_size), np.uint8)
    large_kernel = np.ones((large_kernel_size, large_kernel_size), np.uint8)
    
    eroded = cv2.erode(binary_mask, small_kernel, iterations=1)
    dilated = cv2.dilate(binary_mask, large_kernel, iterations=1)
    
    # The unknown region is dilated - eroded
    unknown_region = dilated - eroded
    unknown_region = unknown_region.astype(bool)
    
    if not unknown_region.any():
        # If no thin region found, return original
        return image
    
    # Apply matting to find more accurate alpha values
    # This is a simplified approach - in practice, you would use more advanced matting algorithms
    refined_mask = mask_np.copy()
    
    # For unknown regions, compute distance transform to get smooth transitions
    dist_transform = cv2.distanceTransform((~binary_mask * 255).astype(np.uint8), cv2.DIST_L2, 0)
    dist_transform = dist_transform / dist_transform.max()  # Normalize
    
    # Apply the refined alpha values to the unknown region
    refined_mask[unknown_region] = 1 - dist_transform[unknown_region]
    
    # Create result by blending with the original mask
    result = img_np.copy()
    
    return Image.fromarray(result.astype(np.uint8), 'RGB')


def final_blending(original_image, processed_image, mask, blend_strength=0.8):
    """
    Apply final blending between original and processed images
    """
    # Convert to numpy arrays
    orig_np = np.array(original_image).astype(np.float32)
    proc_np = np.array(processed_image).astype(np.float32)
    mask_np = np.array(mask).astype(np.float32)
    
    # Ensure mask is single channel and normalized
    if len(mask_np.shape) == 3:
        mask_np = mask_np[:, :, 0]
    mask_np = mask_np / 255.0
    
    # Apply blending with the specified strength
    mask_blended = mask_np * blend_strength
    
    # Blend the images
    result = proc_np * mask_blended[:, :, np.newaxis] + orig_np * (1 - mask_blended[:, :, np.newaxis])
    result = np.clip(result, 0, 255).astype(np.uint8)
    
    return Image.fromarray(result, 'RGB')


def remove_color_artifacts(image, original_image, mask, threshold=30):
    """
    Remove color artifacts by comparing with original image
    """
    img_np = np.array(image)
    orig_np = np.array(original_image)
    mask_np = np.array(mask)
    
    if len(mask_np.shape) == 3:
        mask_np = mask_np[:, :, 0]
    
    # Create a difference map
    diff = np.abs(img_np.astype(np.float32) - orig_np.astype(np.float32))
    diff_max = np.max(diff, axis=2)  # Max difference across channels
    
    # Create a mask for pixels with high color difference
    artifact_mask = (diff_max > threshold) & (mask_np > 127)
    
    # Apply a small blur to these regions to smooth artifacts
    if np.any(artifact_mask):
        # Create a mask for the artifacts
        artifact_area = np.zeros_like(img_np)
        artifact_area[artifact_mask] = img_np[artifact_mask]
        
        # Apply slight blur to the artifact regions
        blurred = cv2.medianBlur(artifact_area, 3)
        
        # Blend the corrected areas back
        result = img_np.copy()
        result[artifact_mask] = blurred[artifact_mask]
        return Image.fromarray(result, 'RGB')
    
    return image


def post_process_pipeline(result_image, person_image, warped_cloth, parsing_masks, garment_mask, garment_type='top'):
    """
    Complete post-processing pipeline
    """
    # Ensure all images have the same dimensions for consistent processing
    target_size = person_image.size

    # Resize all inputs to match person image size if needed
    if result_image.size != target_size:
        result_image = result_image.resize(target_size, Image.Resampling.LANCZOS)

    if warped_cloth.size != target_size:
        warped_cloth = warped_cloth.resize(target_size, Image.Resampling.LANCZOS)

    # Ensure garment mask has the same dimensions as the target
    if len(garment_mask.shape) == 3:
        mask_h, mask_w = garment_mask.shape[:2]
    else:
        mask_h, mask_w = garment_mask.shape

    if (mask_h, mask_w) != target_size[::-1]:  # target_size is (w, h) but mask is (h, w)
        # Resize mask to match target dimensions
        if len(garment_mask.shape) == 3:
            garment_mask_resized = np.zeros((target_size[1], target_size[0], garment_mask.shape[2]), dtype=garment_mask.dtype)
            for i in range(garment_mask.shape[2]):
                garment_mask_resized[:, :, i] = cv2.resize(garment_mask[:, :, i], target_size)
        else:
            garment_mask_resized = cv2.resize(garment_mask, target_size)
        garment_mask = garment_mask_resized

    # 1. Color matching
    color_matched = color_transfer(warped_cloth, result_image, garment_mask)

    # 2. Add shadows (only to the garment area)
    with_shadow = add_shadows(color_matched, garment_mask)

    # 3. Edge matting for smooth transitions
    matted = edge_matting(with_shadow, garment_mask)

    # 4. Remove color artifacts
    artifact_free = remove_color_artifacts(matted, person_image, garment_mask)

    # 5. Enhance clothes visibility to ensure the new clothes are prominent
    visibility_enhanced = enhance_clothes_visibility(artifact_free, person_image, garment_mask, garment_type)

    # 6. Final blending
    final_result = final_blending(person_image, visibility_enhanced, garment_mask)

    return final_result


def enhance_clothes_visibility(result_image, original_image, composition_mask, garment_type='top'):
    """
    Enhance the visibility and prominence of the replaced clothes
    """
    result_np = np.array(result_image).astype(np.float32)
    orig_np = np.array(original_image).astype(np.float32)

    # Ensure composition mask is in the right format
    if len(composition_mask.shape) == 3:
        mask_2d = composition_mask[:, :, 0]  # Take first channel if multi-channel
    else:
        mask_2d = composition_mask

    # Normalize mask to [0, 1] range
    mask_normalized = mask_2d.astype(np.float32) / 255.0

    # Expand mask to 3 channels if needed
    if len(mask_normalized.shape) == 2:
        mask_3d = np.stack([mask_normalized] * 3, axis=-1)
    else:
        mask_3d = mask_normalized

    # Calculate the difference between result and original in the garment area
    diff = np.abs(result_np - orig_np)
    avg_diff = np.mean(diff, axis=2)  # Average difference across channels

    # If the difference is too small in the garment area, enhance the result
    mask_avg_diff = np.mean(avg_diff * mask_2d)  # Average difference in masked area
    print(f"Average difference in garment area: {mask_avg_diff}")

    if mask_avg_diff < 20:  # If clothes don't seem to be changing much
        print("Enhancing clothes visibility as difference was low")
        # Enhance the contrast in the garment area to make the new clothes more prominent
        # Boost the garment area with more of the new cloth features
        enhanced_result = result_np * 0.8 + orig_np * 0.2  # Slightly more of the result, less of original
        enhanced_result = np.clip(enhanced_result, 0, 255)

        # Apply saturation enhancement to the garment area
        # Convert to HSV for saturation adjustment
        hsv = cv2.cvtColor(enhanced_result.astype(np.uint8), cv2.COLOR_RGB2HSV).astype(np.float32)
        h, s, v = cv2.split(hsv)

        # Increase saturation in the garment area
        s = s + (s * 0.2 * mask_2d)  # Increase saturation by 20% in garment area
        s = np.clip(s, 0, 255)

        enhanced_hsv = cv2.merge([h, s, v])
        enhanced_result = cv2.cvtColor(enhanced_hsv.astype(np.uint8), cv2.COLOR_HSV2RGB).astype(np.float32)

        # Blend with original result
        result_np = enhanced_result * mask_3d + result_np * (1 - mask_3d)

    return Image.fromarray(np.clip(result_np, 0, 255).astype(np.uint8), 'RGB')


def enhance_contrast_brightness(image, contrast_factor=1.1, brightness_factor=1.05):
    """
    Enhance contrast and brightness of the image
    """
    # Apply contrast enhancement
    enhancer = ImageEnhance.Contrast(image)
    contrast_enhanced = enhancer.enhance(contrast_factor)

    # Apply brightness enhancement
    enhancer = ImageEnhance.Brightness(contrast_enhanced)
    result = enhancer.enhance(brightness_factor)

    return result


def sharpen_image(image, amount=1.5):
    """
    Apply unsharp masking to sharpen the image
    """
    # Convert to PIL Image if numpy array
    if isinstance(image, np.ndarray):
        image = Image.fromarray(image.astype(np.uint8))
    
    # Apply unsharp mask
    sharpened = image.filter(ImageFilter.UnsharpMask(radius=2, percent=150, threshold=3))
    
    return sharpened


if __name__ == "__main__":
    print("Post-Processing Module ready!")