"""
Enhanced garment segmentation module with improved accuracy and manual correction capability
"""
import numpy as np
import cv2
from PIL import Image
import torch
import torch.nn as nn
import torch.nn.functional as F
from scipy import ndimage
from skimage import measure, morphology
from human_parsing.human_parsing_model import get_parsing_labels


def enhanced_garment_segmentation(image, garment_type="top", parsing_model=None):
    """
    Enhanced garment segmentation with multiple refinement steps
    """
    if parsing_model is None:
        from app.human_parsing.human_parsing_model import load_pretrained_model
        parsing_model = load_pretrained_model()

    # Get the parsing map
    parsing_map = get_parsing_map_with_enhancement(parsing_model, image)

    # Get high accuracy garment masks based on the specified garment type
    masks = get_enhanced_garment_masks(parsing_map, garment_type)

    return masks


def get_parsing_map_with_enhancement(model, image, device='cpu'):
    """
    Enhanced parsing map generation with improved resolution and post-processing
    """
    model.eval()

    # Preprocess image with higher resolution for better detail
    orig_width, orig_height = image.size
    processing_size = (640, 640)  # Higher resolution for better detail

    # Resize image for processing
    processed_image = image.resize(processing_size)

    input_tensor = preprocess_image_enhanced(processed_image, target_size=processing_size)
    input_tensor = input_tensor.to(device)

    # Forward pass
    with torch.no_grad():
        output = model(input_tensor)
        # Resize output to match original image dimensions
        output = F.interpolate(output, size=(orig_height, orig_width), mode='bilinear', align_corners=False)
        
        # Apply softmax to get probability maps
        prob_maps = F.softmax(output, dim=1)
        
        # Apply morphological post-processing to improve segmentation
        prob_maps = apply_morphological_postprocessing(prob_maps)
        
        parsing_map = torch.argmax(prob_maps, dim=1)
        parsing_map = parsing_map.squeeze(0).cpu().numpy()

    return parsing_map


def preprocess_image_enhanced(image, target_size=None):
    """
    Enhanced image preprocessing with better normalization
    """
    if target_size is not None:
        # Resize image to target size
        image = image.resize(target_size)
    else:
        # Use the input image size as target size to maintain dimensions
        target_size = image.size

    # Convert to tensor and normalize
    image_tensor = torch.from_numpy(np.array(image)).float()
    image_tensor = image_tensor.permute(2, 0, 1)  # HWC to CHW
    image_tensor = image_tensor / 255.0  # Normalize to [0, 1]
    
    # Apply histogram equalization to improve contrast in each channel
    for c in range(3):
        channel = image_tensor[c].numpy()
        channel_eq = cv2.equalizeHist((channel * 255).astype(np.uint8))
        image_tensor[c] = torch.from_numpy(channel_eq.astype(np.float32) / 255.0)

    return image_tensor.unsqueeze(0)  # Add batch dimension


def apply_morphological_postprocessing(prob_maps):
    """
    Apply morphological operations to improve segmentation quality
    """
    # Get top-2 predictions for better handling of boundary areas
    top2_probs, top2_indices = torch.topk(prob_maps, 2, dim=1)
    
    # Apply bilateral filtering to preserve boundaries while smoothing
    batch_size, n_classes, h, w = prob_maps.shape
    
    # Process each batch and class separately
    for b in range(batch_size):
        for c in range(n_classes):
            prob_map = prob_maps[b, c].cpu().numpy()
            
            # Apply bilateral filter
            filtered_map = cv2.bilateralFilter((prob_map * 255).astype(np.uint8), 
                                             d=9, sigmaColor=75, sigmaSpace=75)
            prob_maps[b, c] = torch.from_numpy(filtered_map.astype(np.float32) / 255.0)
    
    return prob_maps


def get_enhanced_garment_masks(parsing_map, garment_type="top"):
    """
    Get enhanced garment masks with better boundary refinement
    """
    labels = get_parsing_labels()

    # Define garment classes more specifically for pixel-perfect segmentation
    garment_classes = {
        'shirt_top': [5],      # upperclothes (shirts, tops)
        'dress': [6],          # dress
        'coat_jacket': [7],    # coat/jacket
        'pants': [9],          # pants
        'jumpsuit': [10],      # jumpsuit
        'skirt': [11],         # skirt
        'face': [12],          # face
        'hair': [2],           # hair
        'left_arm': [13],      # leftArm
        'right_arm': [14],     # rightArm
        'left_leg': [15],      # leftLeg
        'right_leg': [16],     # rightLeg
        'neck': [19]           # neck
    }

    masks = {}

    for part, class_ids in garment_classes.items():
        mask = np.zeros_like(parsing_map)
        for class_id in class_ids:
            mask = np.where(parsing_map == class_id, 1, mask)

        # Apply advanced morphological refinement
        mask = advanced_garment_mask_refinement(mask)
        masks[part] = mask

    # Create combined masks for convenience
    masks['upper'] = np.maximum.reduce([
        masks.get('shirt_top', np.zeros_like(parsing_map)),
        masks.get('coat_jacket', np.zeros_like(parsing_map)),
        masks.get('dress', np.zeros_like(parsing_map))  # Dress is both upper and lower
    ])

    masks['lower'] = np.maximum.reduce([
        masks.get('pants', np.zeros_like(parsing_map)),
        masks.get('skirt', np.zeros_like(parsing_map)),
        masks.get('jumpsuit', np.zeros_like(parsing_map)),
        masks.get('dress', np.zeros_like(parsing_map))  # Dress also covers lower part
    ])

    # Apply additional refinement specifically for upper and lower
    masks['upper'] = advanced_garment_mask_refinement(masks['upper'])
    masks['lower'] = advanced_garment_mask_refinement(masks['lower'])

    # Return the mask based on the requested garment type
    if garment_type.lower() == "top":
        return {'top': masks['upper']}
    elif garment_type.lower() == "bottom":
        return {'bottom': masks['lower']}
    elif garment_type.lower() == "full":
        # Combine upper and lower for full body
        full_mask = np.maximum(masks['upper'], masks['lower'])
        return {'full': advanced_garment_mask_refinement(full_mask)}
    elif garment_type.lower() in masks:
        return {garment_type.lower(): masks[garment_type.lower()]}
    else:
        # Default to upper clothes
        return {'top': masks['upper']}


def advanced_garment_mask_refinement(mask):
    """
    Advanced mask refinement using contour analysis and morphological operations
    """
    if mask is None or mask.size == 0:
        return mask

    # Convert to uint8 if needed
    mask_uint8 = (mask * 255).astype(np.uint8)

    # Apply morphological closing to remove small holes
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))
    mask_closed = cv2.morphologyEx(mask_uint8, cv2.MORPH_CLOSE, kernel)

    # Apply morphological opening to remove small noise
    mask_opened = cv2.morphologyEx(mask_closed, cv2.MORPH_OPEN, kernel)

    # Apply Gaussian smoothing for boundary refinement
    mask_smoothed = cv2.GaussianBlur(mask_opened, (5, 5), 0)

    # Threshold to create binary mask (0 or 1)
    refined_mask = (mask_smoothed > 127).astype(np.uint8)

    # Find contours and use only the largest one to ensure clean garment shape
    contours, hierarchy = cv2.findContours(refined_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    if contours:
        # Keep only the largest contour to ensure clean garment segmentation
        largest_contour = max(contours, key=cv2.contourArea)

        # Use contour approximation to smooth the boundary
        epsilon = 0.005 * cv2.arcLength(largest_contour, True)  # Reduced epsilon for more detail
        approx_contour = cv2.approxPolyDP(largest_contour, epsilon, True)

        # Create new mask with only the largest contour
        final_mask = np.zeros_like(refined_mask)
        cv2.fillPoly(final_mask, [approx_contour], 1)

        # Apply distance transform to create a smooth mask
        dt = cv2.distanceTransform(final_mask, cv2.DIST_L2, 3)
        dt = dt / dt.max()  # Normalize to [0, 1]

        # Use the distance transform to create a soft transition
        dt_mask = cv2.GaussianBlur(dt, (5, 5), 0)
        dt_mask = np.clip(dt_mask, 0, 1)

        return dt_mask
    else:
        return refined_mask


def manual_mask_correction(original_image, current_mask, brush_size=20, strength=1.0):
    """
    Manual mask correction functionality
    This is a simplified version - in a real implementation, this would involve
    interactive GUI elements to allow users to modify the mask
    """
    # For now, this function provides enhanced mask refinement based on image features
    # In a real UI system, this would accept user-drawn corrections
    
    # Convert to numpy arrays
    img_np = np.array(original_image)
    
    # Enhance the mask based on image edges and color similarity
    enhanced_mask = enhance_mask_with_image_features(img_np, current_mask, brush_size, strength)
    
    return enhanced_mask


def enhance_mask_with_image_features(image, mask, brush_size=20, strength=1.0):
    """
    Enhance mask using image features like edges and color similarity
    """
    # Convert to grayscale for edge detection
    gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
    
    # Calculate Canny edges
    edges = cv2.Canny(gray, 50, 150)
    
    # Calculate gradients for better boundary detection
    grad_x = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
    grad_y = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=3)
    gradient_magnitude = np.sqrt(grad_x**2 + grad_y**2)
    
    # Enhance mask using distance transform and edge information
    from scipy.ndimage import distance_transform_edt
    
    # Get distance from mask boundary
    mask_inv = 1 - mask
    dt_fg = distance_transform_edt(mask)
    dt_bg = distance_transform_edt(mask_inv)
    
    # Create a combined mask that respects edges
    combined_weights = np.zeros_like(mask, dtype=np.float32)
    
    # Use gradient magnitude to preserve important edges
    normalized_gradient = gradient_magnitude / (gradient_magnitude.max() + 1e-8)
    
    # Create smooth transition based on distance from original mask and gradient
    combined_weights = mask.astype(np.float32) * 0.8
    combined_weights += 0.2 * (dt_fg / (dt_fg + dt_bg + 1e-8))
    
    # Apply edge-based refinement
    edge_influence = normalized_gradient * (1 - mask)
    combined_weights = np.clip(combined_weights + edge_influence * 0.2, 0, 1)
    
    # Apply morphological operations to clean up
    combined_weights_uint8 = (combined_weights * 255).astype(np.uint8)
    
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (brush_size//2, brush_size//2))
    combined_weights_uint8 = cv2.morphologyEx(combined_weights_uint8, cv2.MORPH_CLOSE, kernel)
    combined_weights_uint8 = cv2.morphologyEx(combined_weights_uint8, cv2.MORPH_OPEN, kernel)
    
    # Convert back to float [0, 1]
    final_mask = combined_weights_uint8.astype(np.float32) / 255.0
    
    return final_mask


def validate_mask_accuracy(original_image, mask, garment_type):
    """
    Validate the accuracy of the mask by checking consistency with image features
    """
    if mask is None or mask.size == 0:
        return False, "Empty or invalid mask"

    # Convert to numpy
    img_np = np.array(original_image)

    # Calculate the coverage of the mask
    mask_coverage = np.mean(mask)

    # More reasonable thresholds for garment coverage:
    # - Minimum 0.5% to account for cases where segmentation fails but pose-based fallback is used
    # - Maximum 80% to avoid full-body masks
    min_coverage = 0.005  # 0.5% - much more forgiving
    max_coverage = 0.8    # 80% - upper reasonable limit

    if mask_coverage < min_coverage:
        # If coverage is too low, provide a more reasonable fallback
        # This could happen when segmentation completely fails
        return False, f"Mask coverage is {mask_coverage:.2%}, which is below minimum threshold of {min_coverage:.2%}"
    elif mask_coverage > max_coverage:
        return False, f"Mask coverage is {mask_coverage:.2%}, which exceeds maximum threshold of {max_coverage:.2%}"

    # Check if mask is connected (has single or few connected components)
    labeled_mask, num_components = measure.label(mask > 0.5, return_num=True)

    # For garment types, we expect 1-3 main components (top, sleeves, etc.)
    max_components = 5 if garment_type in ['top', 'shirt', 't-shirt'] else 3
    if num_components > max_components:
        return False, f"Garment has too many disconnected components: {num_components} (max: {max_components})"

    return True, f"Mask passes validation with {num_components} components and {mask_coverage:.2%} coverage"


def refine_mask_boundaries(mask, image, iterations=1):
    """
    Refine mask boundaries using image gradients
    """
    for _ in range(iterations):
        # Compute image gradients
        gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY) if len(image.shape) == 3 else image
        grad_x = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
        grad_y = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=3)
        gradient_magnitude = np.sqrt(grad_x**2 + grad_y**2)
        
        # Identify mask boundary
        mask_uint8 = (mask * 255).astype(np.uint8)
        contours, _ = cv2.findContours(mask_uint8, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        # Create a distance map from current mask
        dt = cv2.distanceTransform(255 - mask_uint8, cv2.DIST_L2, 3)
        dt = dt / dt.max()
        
        # Adjust mask based on gradient information
        grad_normalized = gradient_magnitude / (gradient_magnitude.max() + 1e-8)
        
        # Expand/contract mask based on gradient strength
        adjustment = (grad_normalized - 0.5) * 0.3  # Adjust magnitude of change
        refined_mask = mask + adjustment * (1 - dt)  # Apply more changes further from mask center
        
        # Ensure mask stays in [0, 1] range
        refined_mask = np.clip(refined_mask, 0, 1)
        
        mask = refined_mask
    
    return mask


if __name__ == "__main__":
    print("Enhanced Segmentation module ready!")