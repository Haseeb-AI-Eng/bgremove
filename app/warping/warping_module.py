"""
Cloth Warping Module
Implements geometric warping using Thin-Plate Spline (TPS) and geometric matching
"""
import numpy as np
import cv2
from PIL import Image
import torch
import torch.nn as nn
import torch.nn.functional as F
from scipy.spatial.distance import cdist
import math


class ThinPlateSpline:
    """
    Thin-Plate Spline transformation for image warping
    """
    def __init__(self):
        self.coefficients = None
        self.source_points = None
    
    def solve_tps(self, source_points, target_points):
        """
        Solve for TPS coefficients
        """
        n = len(source_points)
        
        # Construct the L matrix
        K = self._calculate_kernel(source_points, source_points)
        P = np.hstack([np.ones((n, 1)), source_points])
        O = np.zeros((3, 3))
        L_top = np.hstack([K, P])
        L_bottom = np.hstack([P.T, O])
        L = np.vstack([L_top, L_bottom])
        
        # Construct the right-hand side
        Y = np.vstack([target_points, np.zeros((3, 2))])
        
        # Solve for coefficients
        try:
            coefficients = np.linalg.solve(L, Y)
        except np.linalg.LinAlgError:
            # If singular, use least squares
            coefficients = np.linalg.lstsq(L, Y, rcond=None)[0]
        
        return coefficients
    
    def _calculate_kernel(self, points1, points2):
        """
        Calculate the TPS kernel matrix
        """
        dist = cdist(points1, points2, 'euclidean')
        dist[dist == 0] = 1e-8  # Avoid log(0)
        K = dist ** 2 * np.log(dist)
        return K
    
    def apply_tps(self, image, source_points, target_points, output_shape=None):
        """
        Apply TPS transformation to an image
        """
        if output_shape is None:
            output_shape = image.shape[:2][::-1]  # width, height
        
        # Solve for coefficients
        self.coefficients = self.solve_tps(source_points, target_points)
        self.source_points = source_points
        
        # Create coordinate grids
        h, w = image.shape[:2] if len(image.shape) == 3 else image.shape
        if len(image.shape) == 3:
            channels = image.shape[2]
        else:
            channels = 1
            image = image[:, :, np.newaxis]
        
        # Create mesh grid for target coordinates
        x, y = np.meshgrid(np.arange(output_shape[0]), np.arange(output_shape[1]))
        target_coords = np.stack([x.flatten(), y.flatten()], axis=1)
        
        # Calculate source coordinates for each target coordinate
        source_coords = self._transform_coordinates(target_coords)
        
        # Create warped image
        warped_image = np.zeros((output_shape[1], output_shape[0], channels), dtype=image.dtype)
        
        # Use cv2.remap for efficient warping
        map_x = source_coords[:, 0].reshape(output_shape[1], output_shape[0]).astype(np.float32)
        map_y = source_coords[:, 1].reshape(output_shape[1], output_shape[0]).astype(np.float32)
        
        # Remap each channel separately
        for c in range(channels):
            warped_image[:, :, c] = cv2.remap(
                image[:, :, c], 
                map_x, 
                map_y, 
                interpolation=cv2.INTER_LINEAR,
                borderMode=cv2.BORDER_REFLECT
            )
        
        # Return to original number of dimensions
        if channels == 1:
            warped_image = warped_image[:, :, 0]
        
        return warped_image
    
    def _transform_coordinates(self, target_coords):
        """
        Transform target coordinates to source coordinates using TPS
        """
        n = len(self.source_points)
        W, A = self.coefficients[:n, :], self.coefficients[n:, :]
        
        # Calculate kernel from target points to source points
        K = self._calculate_kernel(target_coords, self.source_points)
        
        # Polynomial part
        P = np.hstack([np.ones((len(target_coords), 1)), target_coords])
        
        # Calculate new coordinates
        source_coords = K @ W + P @ A
        
        return source_coords


class GeometricMatchingModule(nn.Module):
    """
    Geometric Matching Module (GMM) for cloth warping
    This is a simplified version of the GMM from CP-VTON
    """
    def __init__(self, grid_size=20):
        super(GeometricMatchingModule, self).__init__()
        self.grid_size = grid_size
        
        # Simple CNN to extract features
        self.feature_extractor = nn.Sequential(
            nn.Conv2d(3, 64, kernel_size=3, padding=1),
            nn.ReLU(inplace=True),
            nn.Conv2d(64, 128, kernel_size=3, padding=1),
            nn.ReLU(inplace=True),
            nn.MaxPool2d(2),
            nn.Conv2d(128, 256, kernel_size=3, padding=1),
            nn.ReLU(inplace=True),
            nn.Conv2d(256, 256, kernel_size=3, padding=1),
            nn.ReLU(inplace=True),
            nn.MaxPool2d(2),
        )
        
        # Predict transformation parameters
        self.flow_generator = nn.Sequential(
            nn.Conv2d(256, 128, kernel_size=3, padding=1),
            nn.ReLU(inplace=True),
            nn.ConvTranspose2d(128, 64, kernel_size=4, stride=2, padding=1),
            nn.ReLU(inplace=True),
            nn.Conv2d(64, 32, kernel_size=3, padding=1),
            nn.ReLU(inplace=True),
            nn.ConvTranspose2d(32, 16, kernel_size=4, stride=2, padding=1),
            nn.ReLU(inplace=True),
            nn.Conv2d(16, 2, kernel_size=3, padding=1),  # 2 for x, y flow
        )
    
    def forward(self, cloth_image, person_image, cloth_parse=None, person_parse=None):
        """
        Forward pass to generate flow field for warping
        """
        batch_size = cloth_image.size(0)
        
        # Extract features from both images
        cloth_features = self.feature_extractor(cloth_image)
        person_features = self.feature_extractor(person_image)
        
        # Combine features
        combined_features = torch.cat([cloth_features, person_features], dim=1)
        
        # Generate flow field
        flow = self.flow_generator(combined_features)
        
        # Normalize flow to reasonable range
        flow = torch.tanh(flow) * 0.1  # Keep flow small initially
        
        return flow


def warp_cloth_image(cloth_image, person_image, keypoints_person, keypoints_cloth=None, method='tps', garment_type='top'):
    """
    Warp cloth image to match person's pose
    """
    if method == 'tps':
        return warp_cloth_tps(cloth_image, person_image, keypoints_person, keypoints_cloth)
    elif method == 'flow':
        return warp_cloth_flow(cloth_image, person_image)
    else:
        raise ValueError(f"Unknown warping method: {method}")


def warp_cloth_tps(cloth_image, person_image, keypoints_person, keypoints_cloth=None):
    """
    Warp cloth using Thin-Plate Spline transformation
    """
    # Convert images to numpy arrays
    cloth_np = np.array(cloth_image)
    person_np = np.array(person_image)

    # Get image dimensions
    cloth_h, cloth_w = cloth_np.shape[:2]
    person_h, person_w = person_np.shape[:2]

    # Ensure person image dimensions match expected size
    expected_person_shape = person_np.shape
    expected_cloth_shape = cloth_np.shape

    # If no cloth keypoints provided, create default ones that match person proportions
    if keypoints_cloth is None:
        # Define default cloth keypoints based on cloth image
        # These keypoints will be mapped to the person's body landmarks
        keypoints_cloth = np.array([
            [cloth_w // 2, cloth_h // 4],    # center top (neck area)
            [cloth_w // 4, cloth_h // 3],    # left shoulder
            [3 * cloth_w // 4, cloth_h // 3], # right shoulder
            [cloth_w // 2, cloth_h // 2],    # chest center
            [cloth_w // 4, 3 * cloth_h // 4], # left waist
            [3 * cloth_w // 4, 3 * cloth_h // 4]  # right waist
        ])

    # Extract relevant person keypoints for garment alignment
    # Use neck, shoulders and hips for upper garment alignment
    person_keypoints_for_cloth = []
    keypoint_indices = [1, 2, 5, 8, 11]  # neck, right_shoulder, left_shoulder, right_hip, left_hip
    for idx in keypoint_indices:
        if idx < len(keypoints_person) and keypoints_person[idx][2] > 0.1:  # confidence check
            person_keypoints_for_cloth.append(keypoints_person[idx][:2])

    # If we don't have enough person keypoints with good confidence, use proportional ones
    if len(person_keypoints_for_cloth) < 3:
        print("Warning: Not enough confident keypoints found in person image. Using proportional positions.")
        # Use proportional positions based on person image dimensions
        neck_pos = [person_w // 2, person_h // 4]  # approximate neck position
        r_shoulder = [person_w // 3, person_h // 3]  # right shoulder
        l_shoulder = [2 * person_w // 3, person_h // 3]  # left shoulder
        chest_pos = [person_w // 2, person_h // 2]  # chest/center
        r_hip = [person_w // 3, 2 * person_h // 3]  # right hip
        l_hip = [2 * person_w // 3, 2 * person_h // 3]  # left hip

        person_keypoints_for_cloth = [neck_pos, r_shoulder, l_shoulder, chest_pos, r_hip, l_hip]

    person_keypoints_for_cloth = np.array(person_keypoints_for_cloth)

    # Adjust source keypoints to cloth image size and target to person image size
    # Scale cloth keypoints to person image dimensions
    scaled_cloth_keypoints = []
    for kp in keypoints_cloth:
        # Scale from cloth dimensions to person dimensions
        x_scaled = int((kp[0] / cloth_w) * person_w)
        y_scaled = int((kp[1] / cloth_h) * person_h)
        scaled_cloth_keypoints.append([x_scaled, y_scaled])

    scaled_cloth_keypoints = np.array(scaled_cloth_keypoints)

    # Ensure both point sets have the same number of points
    # Use the minimum number of points
    min_points = min(len(scaled_cloth_keypoints), len(person_keypoints_for_cloth))
    if min_points < 3:
        print(f"Warning: Not enough matching keypoints (found {min_points}, need at least 3). Using simpler alignment method.")
        # Fall back to simple resizing if we don't have enough points
        # But make sure it's the right size
        warped_image = cloth_image.resize((person_w, person_h), Image.Resampling.LANCZOS)
        # Create a simple TPS object for the return value
        tps = ThinPlateSpline()
        return warped_image, tps

    source_points = scaled_cloth_keypoints[:min_points]
    target_points = person_keypoints_for_cloth[:min_points]

    # Create TPS transformer
    tps = ThinPlateSpline()

    # Apply TPS transformation
    try:
        warped_cloth = tps.apply_tps(
            cloth_np,
            source_points,
            target_points,
            output_shape=(person_w, person_h)
        )
    except Exception as e:
        print(f"TPS transformation failed: {e}. Falling back to advanced alignment method.")
        # If TPS fails, use improved alignment based on garment type
        warped_image = advanced_cloth_alignment(cloth_image, person_image, keypoints_person)
        return warped_image, tps

    # Ensure warped cloth has the exact same shape as person image for compatibility
    if warped_cloth.shape != expected_person_shape:
        # Handle different channel configurations
        if len(expected_person_shape) == 3 and len(warped_cloth.shape) == 3:
            # Both are 3-channel images
            if warped_cloth.shape[:2] != expected_person_shape[:2]:
                # Resize spatial dimensions to match
                if len(warped_cloth.shape) == 3:
                    warped_cloth = cv2.resize(warped_cloth, (expected_person_shape[1], expected_person_shape[0]))
                else:
                    # If somehow it became 2D after TPS, make sure it's 3D
                    warped_cloth = cv2.resize(warped_cloth, (expected_person_shape[1], expected_person_shape[0]))
                    if len(warped_cloth.shape) == 2:
                        warped_cloth = np.stack([warped_cloth] * 3, axis=-1)
        elif len(expected_person_shape) == 3 and len(warped_cloth.shape) == 2:
            # Warped cloth is 2D but person is 3D, convert to 3D
            warped_cloth = cv2.resize(warped_cloth, (expected_person_shape[1], expected_person_shape[0]))
            warped_cloth = np.stack([warped_cloth, warped_cloth, warped_cloth], axis=-1)
        elif len(expected_person_shape) == 2 and len(warped_cloth.shape) == 3:
            # Warped cloth is 3D but person is 2D, convert to 2D
            warped_cloth = cv2.cvtColor(warped_cloth, cv2.COLOR_RGB2GRAY) if warped_cloth.shape[2] == 3 else warped_cloth[:,:,0]
            warped_cloth = cv2.resize(warped_cloth, (expected_person_shape[1], expected_person_shape[0]))
        else:
            # Both have same number of dimensions, just resize spatially
            warped_cloth = cv2.resize(warped_cloth, (expected_person_shape[1], expected_person_shape[0]),
                                      interpolation=cv2.INTER_LINEAR)

    # Convert back to PIL image
    if len(warped_cloth.shape) == 3:
        # Ensure it has 3 channels in RGB format
        if warped_cloth.shape[2] == 3:
            warped_image = Image.fromarray(warped_cloth.astype('uint8'), 'RGB')
        elif warped_cloth.shape[2] == 4:
            warped_image = Image.fromarray(warped_cloth.astype('uint8'), 'RGBA')
        else:
            # Handle other channel configurations
            if warped_cloth.shape[2] == 1:
                warped_image = Image.fromarray(warped_cloth[:,:,0].astype('uint8'), 'L')
            else:
                # Take first 3 channels if more than 3
                warped_image = Image.fromarray(warped_cloth[:,:,:3].astype('uint8'), 'RGB')
    else:
        # Grayscale image
        warped_image = Image.fromarray(warped_cloth.astype('uint8'), 'L')

    return warped_image, tps


def advanced_cloth_alignment(cloth_image, person_image, keypoints_person):
    """
    Advanced cloth alignment when TPS fails - uses pose-guided scaling and positioning
    """
    cloth_np = np.array(cloth_image)
    person_np = np.array(person_image)

    person_h, person_w = person_np.shape[:2]
    cloth_h, cloth_w = cloth_np.shape[:2]

    # Calculate torso dimensions from pose keypoints to scale the cloth appropriately
    neck_idx, l_shoulder_idx, r_shoulder_idx, l_hip_idx, r_hip_idx = 1, 2, 5, 8, 11

    neck = keypoints_person[neck_idx] if neck_idx < len(keypoints_person) and keypoints_person[neck_idx][2] > 0.1 else None
    l_shoulder = keypoints_person[l_shoulder_idx] if l_shoulder_idx < len(keypoints_person) and keypoints_person[l_shoulder_idx][2] > 0.1 else None
    r_shoulder = keypoints_person[r_shoulder_idx] if r_shoulder_idx < len(keypoints_person) and keypoints_person[r_shoulder_idx][2] > 0.1 else None
    l_hip = keypoints_person[l_hip_idx] if l_hip_idx < len(keypoints_person) and keypoints_person[l_hip_idx][2] > 0.1 else None
    r_hip = keypoints_person[r_hip_idx] if r_hip_idx < len(keypoints_person) and keypoints_person[r_hip_idx][2] > 0.1 else None

    # Calculate torso width and height based on keypoints
    torso_width = 0
    torso_height = 0

    # Calculate shoulder width
    if l_shoulder is not None and r_shoulder is not None:
        shoulder_width = abs(r_shoulder[0] - l_shoulder[0])
        torso_width = shoulder_width * 1.2  # Add some extra width to cover shoulders well
    elif l_shoulder is not None or r_shoulder is not None:
        # Estimate from single shoulder
        shoulder_pos = l_shoulder if l_shoulder is not None else r_shoulder
        torso_width = person_w * 0.6  # Use 60% of image width as fallback
    else:
        torso_width = person_w * 0.5  # Fallback width

    # Calculate torso height from neck to hip
    if neck is not None and (l_hip is not None or r_hip is not None):
        if l_hip is not None and r_hip is not None:
            hip_y = (l_hip[1] + r_hip[1]) / 2  # Average hip position
        elif l_hip is not None:
            hip_y = l_hip[1]
        else:  # r_hip is not None
            hip_y = r_hip[1]

        neck_y = neck[1]
        torso_height = abs(hip_y - neck_y) * 1.1  # Add 10% to make sure we cover the torso area
    elif neck is not None:
        # If we only have neck, estimate torso height
        torso_height = person_h * 0.4  # Use 40% of image height as torso height
        neck_y = neck[1]
    else:
        # Complete fallback values
        torso_width = person_w * 0.5
        torso_height = person_h * 0.4
        neck_y = person_h * 0.25

    # Determine appropriate scale factor to make cloth fit the torso area
    width_scale = torso_width / cloth_w
    height_scale = torso_height / cloth_h

    # Use the smaller scale factor to ensure the cloth fits within the torso area
    # but also ensure it's not too small
    scale_factor = min(width_scale, height_scale)
    scale_factor = max(scale_factor, 0.5)  # Don't shrink too much
    scale_factor = min(scale_factor, 3.0)  # Don't enlarge too much

    # Calculate new dimensions
    new_width = int(cloth_w * scale_factor)
    new_height = int(cloth_h * scale_factor)

    # Resize the cloth image
    cloth_scaled = cloth_image.resize((new_width, new_height), Image.Resampling.LANCZOS)
    cloth_scaled_np = np.array(cloth_scaled)

    # Position the scaled cloth on the person based on pose keypoints
    # Center horizontally based on shoulders/neck
    if l_shoulder is not None and r_shoulder is not None:
        center_x = (l_shoulder[0] + r_shoulder[0]) / 2
    elif neck is not None:
        center_x = neck[0]
    else:
        center_x = person_w / 2  # Center of person image

    # Position vertically - place the top of the cloth at the neck level
    center_y = neck_y if neck is not None else person_h * 0.25

    # Calculate the placement coordinates
    cloth_scaled_h, cloth_scaled_w = cloth_scaled_np.shape[:2]

    start_x = int(center_x - cloth_scaled_w // 2)
    end_x = start_x + cloth_scaled_w
    start_y = int(center_y - cloth_scaled_h // 4)  # Position slightly above the neck
    end_y = start_y + cloth_scaled_h

    # Adjust coordinates to stay within image bounds
    if start_x < 0:
        start_x = 0
        end_x = cloth_scaled_w
    elif end_x > person_w:
        end_x = person_w
        start_x = end_x - cloth_scaled_w

    if start_y < 0:
        start_y = 0
        end_y = cloth_scaled_h
    elif end_y > person_h:
        end_y = person_h
        start_y = end_y - cloth_scaled_h

    # Create the result by pasting the cloth onto the person image
    result = person_np.copy()

    # Ensure the cloth region fits in the result image
    cloth_roi_h = min(cloth_scaled_h, end_y - start_y)
    cloth_roi_w = min(cloth_scaled_w, end_x - start_x)

    if cloth_roi_h > 0 and cloth_roi_w > 0:
        cloth_roi = cloth_scaled_np[:cloth_roi_h, :cloth_roi_w]
        result[start_y:start_y+cloth_roi_h, start_x:start_x+cloth_roi_w] = cloth_roi

    return Image.fromarray(result, 'RGB')


def warp_cloth_flow(cloth_image, person_image):
    """
    Warp cloth using learned flow field (simplified implementation)
    """
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    
    # Convert images to tensors
    transform = lambda img: torch.from_numpy(np.array(img)).permute(2, 0, 1).float().unsqueeze(0) / 255.0
    cloth_tensor = transform(cloth_image).to(device)
    person_tensor = transform(person_image).to(device)
    
    # Initialize GMM model
    gmm_model = GeometricMatchingModule()
    gmm_model = gmm_model.to(device)
    
    # Generate flow field
    flow_field = gmm_model(cloth_tensor, person_tensor)
    
    # Create grid for warping
    _, _, h, w = cloth_tensor.shape
    grid_y, grid_x = torch.meshgrid(torch.linspace(-1, 1, h), torch.linspace(-1, 1, w))
    grid = torch.stack([grid_x, grid_y], dim=2).unsqueeze(0).to(device)
    
    # Add flow to grid
    flow_field_resized = F.interpolate(flow_field, size=(h, w), mode='bilinear', align_corners=False)
    grid_warped = grid + flow_field_resized.permute(0, 2, 3, 1)
    
    # Apply warping
    warped_tensor = F.grid_sample(cloth_tensor, grid_warped, align_corners=False)
    
    # Convert back to image
    warped_np = (warped_tensor.squeeze(0).permute(1, 2, 0).cpu().detach().numpy() * 255).astype('uint8')
    warped_image = Image.fromarray(warped_np, 'RGB')
    
    return warped_image, flow_field


def get_dense_correspondences(cloth_image, person_image, keypoints_person, parsing_masks_person):
    """
    Get dense correspondences between cloth and person for more accurate warping
    """
    # For now, return the parsing masks and keypoints
    # In a real implementation, this would find dense correspondences
    return {
        'person_keypoints': keypoints_person,
        'person_parsing_masks': parsing_masks_person,
        'cloth_image': cloth_image
    }


def create_cloth_mask_from_image(cloth_image, garment_type='top'):
    """
    Create a garment-specific mask of the cloth from the image
    This is a simplified approach - in reality, you'd have more sophisticated segmentation
    """
    # Convert to numpy
    cloth_np = np.array(cloth_image)

    # Create a simple mask by finding the main region of the cloth
    # Convert to grayscale to find the main area
    if len(cloth_np.shape) == 3:
        gray = cv2.cvtColor(cloth_np, cv2.COLOR_RGB2GRAY)
    else:
        gray = cloth_np

    # Apply threshold to get binary mask
    # Use a more adaptive approach to handle different backgrounds
    _, binary_mask = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

    # Alternative approach: try to find connected components and keep the largest
    # This helps when the Otsu threshold doesn't work well
    if np.count_nonzero(binary_mask) < 0.01 * binary_mask.size:  # If less than 1% of image is foreground
        # Use a fixed threshold instead
        _, binary_mask = cv2.threshold(gray, 10, 255, cv2.THRESH_BINARY)

    # Apply morphological operations to clean up the mask
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (15, 15))
    binary_mask = cv2.morphologyEx(binary_mask, cv2.MORPH_CLOSE, kernel)
    binary_mask = cv2.morphologyEx(binary_mask, cv2.MORPH_OPEN, kernel)

    # For different garment types, we might want to adjust the mask shape
    # This is a simplified approach for different garment types
    if garment_type == 'top':
        # For tops, we might want to make sure the mask covers the upper part more
        h, w = binary_mask.shape
        # Create a shape that focuses on the upper part of the garment
        # This should make sure we keep the main torso area
        upper_mask = np.zeros_like(binary_mask)
        upper_third = int(h * 0.33)
        upper_mask[:upper_third * 2, :] = binary_mask[:upper_third * 2, :]
        # Combine with the original mask to keep connected parts
        binary_mask = cv2.bitwise_or(binary_mask, upper_mask)
    elif garment_type == 'bottom':
        # For bottoms, focus on lower part
        h, w = binary_mask.shape
        lower_third = int(h * 0.33)
        lower_mask = np.zeros_like(binary_mask)
        lower_mask[h - lower_third * 2:, :] = binary_mask[h - lower_third * 2:, :]
        binary_mask = cv2.bitwise_or(binary_mask, lower_mask)
    elif garment_type == 'full':
        # For full body garments, use the full mask
        pass

    # Normalize to [0, 1] float
    cloth_mask = binary_mask.astype(np.float32) / 255.0

    # Return the mask in the same shape as input image
    # If input was multichannel, return multichannel mask
    if len(cloth_mask.shape) == 2:
        if len(cloth_np.shape) == 3 and cloth_np.shape[2] == 3:
            cloth_mask = np.stack([cloth_mask] * 3, axis=-1)
        elif len(cloth_np.shape) == 3:
            cloth_mask = np.stack([cloth_mask] * cloth_np.shape[2], axis=-1)

    return cloth_mask


if __name__ == "__main__":
    print("Warping Module ready!")