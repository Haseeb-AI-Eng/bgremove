"""
Enhanced difference detection module for better clothes replacement validation
"""
import numpy as np
import cv2
from PIL import Image
from scipy import ndimage
from skimage.metrics import structural_similarity as ssim
from skimage.feature import canny
from skimage.filters import gabor
import torch
import torch.nn.functional as F


def enhanced_difference_detection(original_img, result_img, garment_mask=None, 
                                threshold=25, perceptual_weight=0.6):
    """
    Enhanced difference detection considering both pixel-level and perceptual differences
    """
    if isinstance(original_img, Image.Image):
        original_np = np.array(original_img).astype(np.float32)
    else:
        original_np = original_img.astype(np.float32)
        
    if isinstance(result_img, Image.Image):
        result_np = np.array(result_img).astype(np.float32)
    else:
        result_np = result_img.astype(np.float32)
    
    # Ensure both images have the same shape
    if original_np.shape != result_np.shape:
        result_np = cv2.resize(result_np, (original_np.shape[1], original_np.shape[0]))
    
    # 1. Calculate pixel-wise difference (L1 norm)
    pixel_diff = np.mean(np.abs(result_np - original_np))
    
    # 2. Calculate perceptual difference using SSIM
    # Convert to grayscale for SSIM calculation
    orig_gray = cv2.cvtColor(original_np.astype(np.uint8), cv2.COLOR_RGB2GRAY).astype(np.float32)
    result_gray = cv2.cvtColor(result_np.astype(np.uint8), cv2.COLOR_RGB2GRAY).astype(np.float32)
    
    # Calculate SSIM
    ssim_val = ssim(orig_gray, result_gray, data_range=255)
    ssim_diff = 1 - ssim_val  # Invert so higher values mean more difference
    
    # 3. Calculate gradient-based difference (captures edge changes)
    orig_grad_x = np.abs(cv2.Sobel(orig_gray, cv2.CV_64F, 1, 0, ksize=3))
    orig_grad_y = np.abs(cv2.Sobel(orig_gray, cv2.CV_64F, 0, 1, ksize=3))
    orig_gradient = np.sqrt(orig_grad_x**2 + orig_grad_y**2)
    
    result_grad_x = np.abs(cv2.Sobel(result_gray, cv2.CV_64F, 1, 0, ksize=3))
    result_grad_y = np.abs(cv2.Sobel(result_gray, cv2.CV_64F, 0, 1, ksize=3))
    result_gradient = np.sqrt(result_grad_x**2 + result_grad_y**2)
    
    # Compare gradients
    gradient_diff = np.mean(np.abs(result_gradient - orig_gradient))
    
    # 4. Calculate frequency domain difference
    orig_fft = np.fft.fft2(cv2.cvtColor(original_np.astype(np.uint8), cv2.COLOR_RGB2GRAY))
    result_fft = np.fft.fft2(cv2.cvtColor(result_np.astype(np.uint8), cv2.COLOR_RGB2GRAY))
    
    fft_diff = np.mean(np.abs(np.log(np.abs(orig_fft) + 1) - np.log(np.abs(result_fft) + 1)))
    
    # 5. Weighted combination of all metrics
    weighted_diff = (
        pixel_diff * (1 - perceptual_weight) * 0.4 +
        ssim_diff * 255 * perceptual_weight * 0.3 +
        gradient_diff * 0.2 +
        fft_diff * 0.1
    )
    
    # 6. If garment mask provided, focus on the masked area
    if garment_mask is not None:
        # Resize mask if needed
        if garment_mask.shape[:2] != original_np.shape[:2]:
            garment_mask_resized = cv2.resize(garment_mask, (original_np.shape[1], original_np.shape[0]))
            if len(garment_mask_resized.shape) == 2:
                garment_mask_3d = np.stack([garment_mask_resized] * 3, axis=-1)
            else:
                garment_mask_3d = garment_mask_resized
        else:
            if len(garment_mask.shape) == 2:
                garment_mask_3d = np.stack([garment_mask] * 3, axis=-1)
            else:
                garment_mask_3d = garment_mask
        
        # Calculate difference only in the masked area
        masked_orig = original_np * garment_mask_3d
        masked_result = result_np * garment_mask_3d
        
        # Focus on the masked area difference
        masked_pixel_diff = np.mean(np.abs(masked_result - masked_orig))
        
        # Weight the masked difference higher since it's more relevant
        weighted_diff = masked_pixel_diff * 0.6 + weighted_diff * 0.4
    
    return weighted_diff > threshold, weighted_diff


def validate_clothes_replacement_effectiveness(original_img, result_img, garment_mask=None):
    """
    Comprehensive validation of clothes replacement effectiveness
    Returns boolean and numeric score
    """
    is_different, diff_score = enhanced_difference_detection(
        original_img, result_img, garment_mask, threshold=15
    )

    # Additional checks to ensure the change is meaningful
    if is_different:
        # Check if the difference is concentrated in the garment area
        if garment_mask is not None:
            if isinstance(original_img, Image.Image):
                original_np = np.array(original_img).astype(np.float32)
                result_np = np.array(result_img).astype(np.float32)
            else:
                original_np = original_img.astype(np.float32)
                result_np = result_img.astype(np.float32)

            # Calculate difference inside and outside garment area
            mask_area = garment_mask > 0.5
            background_area = garment_mask <= 0.5

            if mask_area.any():
                garment_diff = np.mean(
                    np.abs(result_np[mask_area] - original_np[mask_area])
                )
            else:
                garment_diff = 0

            if background_area.any():
                background_diff = np.mean(
                    np.abs(result_np[background_area] - original_np[background_area])
                )
            else:
                background_diff = 0

            # The garment area should have significantly more difference than background
            if garment_diff > background_diff * 1.5:
                return True, diff_score  # Return numeric score instead of string
            else:
                # Return adjusted score based on effectiveness
                effectiveness_score = diff_score * 0.5  # Reduce score if not focused on garment area
                return False, effectiveness_score
        else:
            return True, diff_score  # Return numeric score instead of string
    else:
        return False, 0.0  # Return numeric score instead of string


def improved_similarity_check(original_img, result_img, method='combined'):
    """
    Improved similarity checking using multiple approaches
    """
    if isinstance(original_img, Image.Image):
        orig_np = np.array(original_img)
        result_np = np.array(result_img)
    else:
        orig_np = original_img
        result_np = result_img
    
    # Resize result to match original if needed
    if orig_np.shape != result_np.shape:
        result_np = cv2.resize(result_np, (orig_np.shape[1], orig_np.shape[0]))
    
    if method == 'combined':
        # Combine multiple similarity metrics
        ssim_score = ssim(
            cv2.cvtColor(orig_np, cv2.COLOR_RGB2GRAY),
            cv2.cvtColor(result_np, cv2.COLOR_RGB2GRAY),
            data_range=255
        )
        
        # Calculate PSNR
        mse = np.mean((orig_np - result_np) ** 2)
        if mse == 0:
            psnr = float('inf')
        else:
            psnr = 20 * np.log10(255.0 / np.sqrt(mse))
        
        # Calculate histogram similarity
        hist_sim = histogram_similarity(orig_np, result_np)
        
        # Combined score (0 = identical, higher = more different)
        combined_score = (1 - ssim_score) * 0.5 + (1 / (psnr + 1)) * 0.3 + (1 - hist_sim) * 0.2
        
        return combined_score > 0.1, combined_score
        
    elif method == 'perceptual':
        # Use more perceptually-aware metrics
        return perceptual_difference_score(orig_np, result_np)
    else:
        # Default to simple pixel difference
        diff = np.mean(np.abs(result_np.astype(float) - orig_np.astype(float)))
        return diff > 15, diff


def histogram_similarity(img1, img2):
    """
    Calculate histogram similarity between two images
    """
    # Convert to HSV for better color comparison
    hsv1 = cv2.cvtColor(img1, cv2.COLOR_RGB2HSV)
    hsv2 = cv2.cvtColor(img2, cv2.COLOR_RGB2HSV)
    
    # Calculate histograms for each channel
    hist_h1 = cv2.calcHist([hsv1], [0], None, [50], [0, 180])
    hist_s1 = cv2.calcHist([hsv1], [1], None, [50], [0, 256])
    hist_v1 = cv2.calcHist([hsv1], [2], None, [50], [0, 256])
    
    hist_h2 = cv2.calcHist([hsv2], [0], None, [50], [0, 180])
    hist_s2 = cv2.calcHist([hsv2], [1], None, [50], [0, 256])
    hist_v2 = cv2.calcHist([hsv2], [2], None, [50], [0, 256])
    
    # Compare histograms using correlation
    h_corr = cv2.compareHist(hist_h1, hist_h2, cv2.HISTCMP_CORREL)
    s_corr = cv2.compareHist(hist_s1, hist_s2, cv2.HISTCMP_CORREL)
    v_corr = cv2.compareHist(hist_v1, hist_v2, cv2.HISTCMP_CORREL)
    
    # Weighted average (hue is most important for color)
    similarity = h_corr * 0.5 + s_corr * 0.3 + v_corr * 0.2
    
    return max(0, similarity)  # Ensure non-negative


def perceptual_difference_score(img1, img2):
    """
    Calculate perceptual difference using edge and texture analysis
    """
    gray1 = cv2.cvtColor(img1, cv2.COLOR_RGB2GRAY)
    gray2 = cv2.cvtColor(img2, cv2.COLOR_RGB2GRAY)
    
    # Calculate edges
    edges1 = cv2.Canny(gray1, 50, 150)
    edges2 = cv2.Canny(gray2, 50, 150)
    
    # Calculate edge difference
    edge_diff = np.mean(np.abs(edges1.astype(float) - edges2.astype(float)))
    
    # Calculate texture difference using local binary patterns (simplified)
    texture_diff = np.mean(np.abs(gray1.astype(float) - gray2.astype(float)))
    
    # Combine scores
    perceptual_diff = (edge_diff * 0.6) + (texture_diff * 0.4)
    
    # Normalize to meaningful range
    normalized_score = perceptual_diff / 255.0
    
    return normalized_score > 0.1, normalized_score


def detect_replacement_quality(original_img, result_img, garment_mask=None, 
                             confidence_threshold=0.3):
    """
    Detect the quality of clothes replacement with confidence scoring
    """
    # Calculate multiple difference measures
    is_different_basic, basic_score = enhanced_difference_detection(
        original_img, result_img, garment_mask, threshold=10
    )
    
    is_different_perceptual, perceptual_score = validate_clothes_replacement_effectiveness(
        original_img, result_img, garment_mask
    )
    
    is_different_combined, combined_score = improved_similarity_check(
        original_img, result_img, 'combined'
    )
    
    # Calculate an overall confidence score
    scores = [basic_score, perceptual_score, combined_score]
    avg_score = np.mean(scores)
    
    # Normalized confidence (0 to 1)
    confidence = min(1.0, avg_score / 100.0)  # Adjust normalization factor as needed
    
    # Determine quality level
    if confidence > confidence_threshold:
        quality = "high"
        message = f"Clothes replacement successful with confidence {confidence:.2f}"
    elif confidence > confidence_threshold * 0.5:
        quality = "medium"
        message = f"Clothes replacement partially successful with confidence {confidence:.2f}"
    else:
        quality = "low"
        message = f"Clothes replacement not effective with confidence {confidence:.2f}"
    
    return {
        'is_successful': bool(confidence > confidence_threshold),  # Convert numpy bool to Python bool
        'confidence': float(confidence),  # Convert numpy float to Python float
        'quality': quality,
        'message': message,
        'basic_score': float(basic_score) if not isinstance(basic_score, str) else basic_score,
        'perceptual_score': float(perceptual_score) if not isinstance(perceptual_score, str) else perceptual_score,
        'combined_score': float(combined_score) if not isinstance(combined_score, str) else combined_score
    }


if __name__ == "__main__":
    print("Enhanced Difference Detection module ready!")