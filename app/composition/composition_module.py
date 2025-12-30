"""
Composition and Blending Module
Implements the Try-On Module for combining warped cloth with person image
"""
import numpy as np
import cv2
from PIL import Image
import torch
import torch.nn as nn
import torch.nn.functional as F
from skimage.restoration import inpaint
from skimage import filters
from scipy import ndimage
import math


class TryOnModule(nn.Module):
    """
    Try-On Module that combines person representation with warped cloth
    This is a simplified version of the generator from CP-VTON/VITON
    """
    def __init__(self, input_nc=24, output_nc=3, ngf=64):
        """
        input_nc: number of input channels
          - 3 for person image
          - 20 for parsing map (one-hot encoded)
          - 3 for pose heatmaps (if using)
          - 3 for warped cloth
          - 3 for cloth mask (if separate)
          = Total ~32 channels, using 24 for this simplified version
          
        output_nc: number of output channels (3 for RGB)
        ngf: number of generator filters in the last conv layer
        """
        super(TryOnModule, self).__init__()
        
        # Encoder
        self.conv1 = nn.Conv2d(input_nc, ngf, kernel_size=4, stride=2, padding=1)
        self.norm1 = nn.InstanceNorm2d(ngf)
        self.relu1 = nn.LeakyReLU(0.2, inplace=True)
        
        self.conv2 = nn.Conv2d(ngf, ngf * 2, kernel_size=4, stride=2, padding=1)
        self.norm2 = nn.InstanceNorm2d(ngf * 2)
        self.relu2 = nn.LeakyReLU(0.2, inplace=True)
        
        self.conv3 = nn.Conv2d(ngf * 2, ngf * 4, kernel_size=4, stride=2, padding=1)
        self.norm3 = nn.InstanceNorm2d(ngf * 4)
        self.relu3 = nn.LeakyReLU(0.2, inplace=True)
        
        self.conv4 = nn.Conv2d(ngf * 4, ngf * 8, kernel_size=4, stride=2, padding=1)
        self.norm4 = nn.InstanceNorm2d(ngf * 8)
        self.relu4 = nn.LeakyReLU(0.2, inplace=True)
        
        # Bottleneck
        self.bottleneck = nn.Sequential(
            nn.Conv2d(ngf * 8, ngf * 8, kernel_size=4, stride=2, padding=1),
            nn.InstanceNorm2d(ngf * 8),
            nn.ReLU(inplace=True),
            nn.ConvTranspose2d(ngf * 8, ngf * 8, kernel_size=4, stride=2, padding=1),
            nn.InstanceNorm2d(ngf * 8),
            nn.ReLU(inplace=True)
        )
        
        # Decoder
        self.deconv4 = nn.ConvTranspose2d(ngf * 8 * 2, ngf * 4, kernel_size=4, stride=2, padding=1)
        self.norm_d4 = nn.InstanceNorm2d(ngf * 4)
        self.relu_d4 = nn.ReLU(inplace=True)
        
        self.deconv3 = nn.ConvTranspose2d(ngf * 4 * 2, ngf * 2, kernel_size=4, stride=2, padding=1)
        self.norm_d3 = nn.InstanceNorm2d(ngf * 2)
        self.relu_d3 = nn.ReLU(inplace=True)
        
        self.deconv2 = nn.ConvTranspose2d(ngf * 2 * 2, ngf, kernel_size=4, stride=2, padding=1)
        self.norm_d2 = nn.InstanceNorm2d(ngf)
        self.relu_d2 = nn.ReLU(inplace=True)
        
        self.deconv1 = nn.ConvTranspose2d(ngf * 2, output_nc, kernel_size=4, stride=2, padding=1)
        self.tanh = nn.Tanh()
    
    def forward(self, person_image, parsing_map, pose_map, warped_cloth, cloth_mask):
        """
        Forward pass to generate try-on result
        """
        # Concatenate all inputs along channel dimension
        x = torch.cat([person_image, parsing_map, pose_map, warped_cloth, cloth_mask], dim=1)
        
        # Encoder path
        e1 = self.relu1(self.norm1(self.conv1(x)))  # ngf x H/2 x W/2
        e2 = self.relu2(self.norm2(self.conv2(e1)))  # ngf*2 x H/4 x W/4
        e3 = self.relu3(self.norm3(self.conv3(e2)))  # ngf*4 x H/8 x W/8
        e4 = self.relu4(self.norm4(self.conv4(e3)))  # ngf*8 x H/16 x W/16
        
        # Bottleneck
        b = self.bottleneck(e4)  # ngf*8 x H/8 x W/8
        
        # Decoder path with skip connections
        d4 = self.relu_d4(self.norm_d4(self.deconv4(torch.cat([b, e4], dim=1))))  # ngf*4 x H/4 x W/4
        d3 = self.relu_d3(self.norm_d3(self.deconv3(torch.cat([d4, e3], dim=1))))  # ngf*2 x H/2 x W/2
        d2 = self.relu_d2(self.norm_d2(self.deconv2(torch.cat([d3, e2], dim=1))))  # ngf x H x W
        d1 = self.deconv1(torch.cat([d2, e1], dim=1))  # output_nc x H x W
        
        # Tanh to get output in [-1, 1] then scale to [0, 1]
        output = self.tanh(d1)
        output = (output + 1) / 2.0
        
        return output


class CompositionModule:
    """
    Composition module for blending warped cloth with person image
    """
    def __init__(self):
        self.tryon_model = None  # Placeholder for neural network model
    
    def create_composition_mask(self, person_image, parsing_masks, keypoints=None, garment_type='top'):
        """
        Create a learned composition mask based on parsing and pose
        """
        # Start with garments masks based on garment type
        if garment_type == 'top':
            # For tops, use upper clothes (typically classes 5, 6, 7)
            if 'upper' in parsing_masks:
                garment_mask = parsing_masks['upper']
            elif 'parsing_map' in parsing_masks and hasattr(parsing_masks['parsing_map'], 'shape'):
                # If we have a full parsing map, extract upper clothes (typically class 5, 6, 7)
                parsing_map = parsing_masks['parsing_map']
                garment_mask = np.zeros_like(parsing_map)
                # Assuming classes 5 (upperclothes), 6 (dress), 7 (coat) are upper garments
                for class_id in [5, 6, 7]:
                    garment_mask = np.where(parsing_map == class_id, 1, garment_mask)
            else:
                # Fallback to a default shape-based mask for upper body
                h, w = person_image.shape[:2] if len(person_image.shape) > 2 else (person_image.shape[0], person_image.shape[1])
                garment_mask = np.zeros((h, w), dtype=np.float32)
                # Create a simple torso-like mask
                torso_h_start = int(h * 0.25)  # Start from 25% height (neck area)
                torso_h_end = int(h * 0.6)    # End at 60% height (waist area)
                torso_w_start = int(w * 0.2)  # Start at 20% width
                torso_w_end = int(w * 0.8)    # End at 80% width
                garment_mask[torso_h_start:torso_h_end, torso_w_start:torso_w_end] = 1
        elif garment_type == 'bottom':
            # For bottoms, use lower clothes (typically classes 9, 10, 11)
            if 'lower' in parsing_masks:
                garment_mask = parsing_masks['lower']
            elif 'parsing_map' in parsing_masks and hasattr(parsing_masks['parsing_map'], 'shape'):
                # If we have a full parsing map, extract lower clothes (typically class 9, 10, 11)
                parsing_map = parsing_masks['parsing_map']
                garment_mask = np.zeros_like(parsing_map)
                # Assuming classes 9 (pants), 10 (jumpsuit), 11 (skirt) are lower garments
                for class_id in [9, 10, 11]:
                    garment_mask = np.where(parsing_map == class_id, 1, garment_mask)
            else:
                # Fallback to a default shape-based mask for lower body
                h, w = person_image.shape[:2] if len(person_image.shape) > 2 else (person_image.shape[0], person_image.shape[1])
                garment_mask = np.zeros((h, w), dtype=np.float32)
                # Create a simple lower body mask
                lower_h_start = int(h * 0.4)  # Start from 40% height (waist area)
                lower_h_end = int(h * 0.85)   # End at 85% height (above ankles)
                lower_w_start = int(w * 0.25)  # Start at 25% width
                lower_w_end = int(w * 0.75)   # End at 75% width
                garment_mask[lower_h_start:lower_h_end, lower_w_start:lower_w_end] = 1
        elif garment_type == 'full':
            # For full body garments, combine upper and lower
            if 'upper' in parsing_masks and 'lower' in parsing_masks:
                upper_mask = parsing_masks['upper']
                lower_mask = parsing_masks['lower']
                garment_mask = np.maximum(upper_mask, lower_mask)
            elif 'parsing_map' in parsing_masks and hasattr(parsing_masks['parsing_map'], 'shape'):
                # If we have a full parsing map, extract full body clothes
                parsing_map = parsing_masks['parsing_map']
                garment_mask = np.zeros_like(parsing_map)
                # Include both upper and lower garments
                for class_id in [5, 6, 7, 9, 10, 11]:
                    garment_mask = np.where(parsing_map == class_id, 1, garment_mask)
            else:
                # Fallback to a full body shape-based mask
                h, w = person_image.shape[:2] if len(person_image.shape) > 2 else (person_image.shape[0], person_image.shape[1])
                garment_mask = np.ones((h, w), dtype=np.float32)  # Full body mask
        else:
            # If unknown garment type, default to upper garments
            if 'upper' in parsing_masks:
                garment_mask = parsing_masks['upper']
            elif 'parsing_map' in parsing_masks and hasattr(parsing_masks['parsing_map'], 'shape'):
                # If we have a full parsing map, extract upper clothes (typically class 5, 6, 7)
                parsing_map = parsing_masks['parsing_map']
                garment_mask = np.zeros_like(parsing_map)
                # Assuming classes 5 (upperclothes), 6 (dress), 7 (coat) are upper garments
                for class_id in [5, 6, 7]:
                    garment_mask = np.where(parsing_map == class_id, 1, garment_mask)
            else:
                # Fallback to a default shape-based mask
                h, w = person_image.shape[:2] if len(person_image.shape) > 2 else (person_image.shape[0], person_image.shape[1])
                garment_mask = np.zeros((h, w), dtype=np.float32)
                # Create a simple torso-like mask
                torso_h_start = int(h * 0.25)  # Start from 25% height
                torso_h_end = int(h * 0.6)    # End at 60% height
                torso_w_start = int(w * 0.3)  # Start at 30% width
                torso_w_end = int(w * 0.7)    # End at 70% width
                garment_mask[torso_h_start:torso_h_end, torso_w_start:torso_w_end] = 1

        # If we have keypoints, refine the mask to focus on the appropriate area based on garment type
        if keypoints is not None and len(keypoints) > 0:
            h, w = person_image.shape[:2] if len(person_image.shape) > 2 else (person_image.shape[0], person_image.shape[1])

            if garment_type == 'top':
                # For tops, focus on upper body using neck, shoulders, and upper torso
                neck = keypoints[1] if len(keypoints) > 1 else np.array([w//2, h//4, 0.5])  # neck
                r_shoulder = keypoints[2] if len(keypoints) > 2 else np.array([w//3, h//3, 0.5])  # right shoulder
                l_shoulder = keypoints[5] if len(keypoints) > 5 else np.array([2*w//3, h//3, 0.5])  # left shoulder
                r_hip = keypoints[8] if len(keypoints) > 8 else np.array([w//3, 2*h//3, 0.5])  # right hip
                l_hip = keypoints[11] if len(keypoints) > 11 else np.array([2*w//3, 2*h//3, 0.5])  # left hip

                # Create a polygon mask for upper torso
                if neck[2] > 0.1 and r_shoulder[2] > 0.1 and l_shoulder[2] > 0.1:  # Check confidence
                    # Create a trapezoid covering the upper torso
                    pts = np.array([
                        [int(neck[0]), int(neck[1])],  # neck
                        [int(r_shoulder[0]), int(r_shoulder[1])],  # right shoulder
                        [int(r_hip[0]), int(r_hip[1])],  # right hip (lower limit)
                        [int(l_hip[0]), int(l_hip[1])],  # left hip (lower limit)
                        [int(l_shoulder[0]), int(l_shoulder[1])]   # left shoulder
                    ])

                    # Ensure all points are within image bounds
                    pts[:, 0] = np.clip(pts[:, 0], 0, w-1)
                    pts[:, 1] = np.clip(pts[:, 1], 0, h-1)

                    # Create torso mask
                    torso_mask = np.zeros((h, w), dtype=np.uint8)
                    cv2.fillPoly(torso_mask, [pts.astype(np.int32)], 1)

                    # Combine with garment mask
                    if len(garment_mask.shape) == 2:
                        garment_mask = garment_mask * torso_mask
                    else:
                        # If upper_mask is 3-channel, apply 2D torso mask to each channel
                        garment_mask_2d = np.where(garment_mask[:, :, 0] > 0, 1, 0) if len(garment_mask.shape) > 2 else garment_mask
                        garment_mask_2d = garment_mask_2d * torso_mask
                        garment_mask = np.stack([garment_mask_2d, garment_mask_2d, garment_mask_2d], axis=-1)

            elif garment_type == 'bottom':
                # For bottom garments, focus on lower body using hips, legs
                r_hip = keypoints[8] if len(keypoints) > 8 else np.array([w//3, 2*h//3, 0.5])  # right hip
                l_hip = keypoints[11] if len(keypoints) > 11 else np.array([2*w//3, 2*h//3, 0.5])  # left hip
                r_knee = keypoints[9] if len(keypoints) > 9 else np.array([w//3, 3*h//4, 0.5])  # right knee
                l_knee = keypoints[12] if len(keypoints) > 12 else np.array([2*w//3, 3*h//4, 0.5])  # left knee
                r_ankle = keypoints[10] if len(keypoints) > 10 else np.array([w//3, 4*h//5, 0.5])  # right ankle
                l_ankle = keypoints[13] if len(keypoints) > 13 else np.array([2*w//3, 4*h//5, 0.5])  # left ankle

                # Create a polygon mask for lower body
                if r_hip[2] > 0.1 and l_hip[2] > 0.1:
                    # Create a polygon covering the lower body
                    pts = np.array([
                        [int(r_hip[0]), int(r_hip[1])],  # right hip
                        [int(r_knee[0]), int(r_knee[1])],  # right knee
                        [int(r_ankle[0]), int(r_ankle[1])],  # right ankle
                        [int(l_ankle[0]), int(l_ankle[1])],  # left ankle
                        [int(l_knee[0]), int(l_knee[1])],  # left knee
                        [int(l_hip[0]), int(l_hip[1])]   # left hip
                    ])

                    # Ensure all points are within image bounds
                    pts[:, 0] = np.clip(pts[:, 0], 0, w-1)
                    pts[:, 1] = np.clip(pts[:, 1], 0, h-1)

                    # Create lower body mask
                    lower_mask = np.zeros((h, w), dtype=np.uint8)
                    cv2.fillPoly(lower_mask, [pts.astype(np.int32)], 1)

                    # Combine with garment mask
                    if len(garment_mask.shape) == 2:
                        garment_mask = garment_mask * lower_mask
                    else:
                        # If upper_mask is 3-channel, apply 2D torso mask to each channel
                        garment_mask_2d = np.where(garment_mask[:, :, 0] > 0, 1, 0) if len(garment_mask.shape) > 2 else garment_mask
                        garment_mask_2d = garment_mask_2d * lower_mask
                        garment_mask = np.stack([garment_mask_2d, garment_mask_2d, garment_mask_2d], axis=-1)

            elif garment_type == 'full':
                # For full garments, use the full body area
                neck = keypoints[1] if len(keypoints) > 1 else np.array([w//2, h//4, 0.5])  # neck
                r_shoulder = keypoints[2] if len(keypoints) > 2 else np.array([w//3, h//3, 0.5])  # right shoulder
                l_shoulder = keypoints[5] if len(keypoints) > 5 else np.array([2*w//3, h//3, 0.5])  # left shoulder
                r_hip = keypoints[8] if len(keypoints) > 8 else np.array([w//3, 2*h//3, 0.5])  # right hip
                l_hip = keypoints[11] if len(keypoints) > 11 else np.array([2*w//3, 2*h//3, 0.5])  # left hip
                r_ankle = keypoints[10] if len(keypoints) > 10 else np.array([w//3, 4*h//5, 0.5])  # right ankle
                l_ankle = keypoints[13] if len(keypoints) > 13 else np.array([2*w//3, 4*h//5, 0.5])  # left ankle

                # Create a polygon mask for full body
                if neck[2] > 0.1 and r_shoulder[2] > 0.1 and l_shoulder[2] > 0.1:
                    # Create a polygon covering the full body
                    pts = np.array([
                        [int(neck[0]), int(neck[1])],  # neck
                        [int(r_shoulder[0]), int(r_shoulder[1])],  # right shoulder
                        [int(r_hip[0]), int(r_hip[1])],  # right hip
                        [int(r_ankle[0]), int(r_ankle[1])],  # right ankle
                        [int(l_ankle[0]), int(l_ankle[1])],  # left ankle
                        [int(l_hip[0]), int(l_hip[1])],  # left hip
                        [int(l_shoulder[0]), int(l_shoulder[1])]   # left shoulder
                    ])

                    # Ensure all points are within image bounds
                    pts[:, 0] = np.clip(pts[:, 0], 0, w-1)
                    pts[:, 1] = np.clip(pts[:, 1], 0, h-1)

                    # Create full body mask
                    full_mask = np.zeros((h, w), dtype=np.uint8)
                    cv2.fillPoly(full_mask, [pts.astype(np.int32)], 1)

                    # Combine with garment mask
                    if len(garment_mask.shape) == 2:
                        garment_mask = garment_mask * full_mask
                    else:
                        # If upper_mask is 3-channel, apply 2D torso mask to each channel
                        garment_mask_2d = np.where(garment_mask[:, :, 0] > 0, 1, 0) if len(garment_mask.shape) > 2 else garment_mask
                        garment_mask_2d = garment_mask_2d * full_mask
                        garment_mask = np.stack([garment_mask_2d, garment_mask_2d, garment_mask_2d], axis=-1)

        # Smooth the mask to create soft transitions
        kernel = np.ones((15, 15), np.float32) / 225
        if len(garment_mask.shape) == 2:
            garment_mask = cv2.filter2D(garment_mask.astype(np.float32), -1, kernel)
        else:
            # Apply smoothing to each channel separately
            for i in range(garment_mask.shape[2]):
                garment_mask[:, :, i] = cv2.filter2D(garment_mask[:, :, i].astype(np.float32), -1, kernel)

        # Ensure the mask is in the right format
        if len(garment_mask.shape) == 2:
            # Expand to 3 channels for RGB
            garment_mask = np.stack([garment_mask] * 3, axis=-1)

        return garment_mask
    
    def poisson_blend(self, src_img, dst_img, mask):
        """
        Implement Poisson blending for seamless composition
        """
        # Convert PIL images to numpy arrays if needed
        if isinstance(src_img, Image.Image):
            src_np = np.array(src_img)
        else:
            src_np = src_img
            
        if isinstance(dst_img, Image.Image):
            dst_np = np.array(dst_img)
        else:
            dst_np = dst_img
        
        # Ensure mask is binary
        mask_binary = (mask > 0.5).astype(np.uint8)
        
        # If mask is 3-channel, use the first channel
        if len(mask_binary.shape) == 3:
            mask_binary = mask_binary[:, :, 0]
        
        # Find the bounding box of the mask
        coords = np.where(mask_binary > 0)
        if len(coords[0]) == 0:
            return dst_img  # Return original if no mask area found
        
        y_min, y_max = coords[0].min(), coords[0].max()
        x_min, x_max = coords[1].min(), coords[1].max()
        
        # Expand the bounding box slightly for better blending
        margin = 10
        y_min = max(0, y_min - margin)
        y_max = min(dst_np.shape[0], y_max + margin)
        x_min = max(0, x_min - margin)
        x_max = min(dst_np.shape[1], x_max + margin)
        
        # Crop images and mask
        crop_src = src_np[y_min:y_max, x_min:x_max]
        crop_dst = dst_np[y_min:y_max, x_min:x_max]
        crop_mask = mask_binary[y_min:y_max, x_min:x_max]
        
        # Calculate center of the mask area for the seeding point
        mask_coords = np.where(crop_mask > 0)
        center_y = int(np.mean(mask_coords[0]))
        center_x = int(np.mean(mask_coords[1]))
        
        # Ensure center is within bounds
        center_y = max(0, min(center_y, crop_dst.shape[0] - 1))
        center_x = max(0, min(center_x, crop_dst.shape[1] - 1))
        
        # Apply seamless cloning using OpenCV
        try:
            center = (center_x, center_y)
            blended_crop = cv2.seamlessClone(crop_src.astype(np.uint8), crop_dst.astype(np.uint8), 
                                           (crop_mask * 255).astype(np.uint8), center, cv2.NORMAL_CLONE)
            # Create result image
            result = dst_np.copy()
            result[y_min:y_max, x_min:x_max] = blended_crop
            return result
        except:
            # If seamless cloning fails, use simple alpha blending
            blended = self.alpha_blend(src_np, dst_np, mask)
            return blended
    
    def alpha_blend(self, src_img, dst_img, mask):
        """
        Alpha blending for combining images
        """
        # Convert to numpy arrays if PIL images
        if isinstance(src_img, Image.Image):
            src_np = np.array(src_img).astype(np.float32)
        else:
            src_np = src_img.astype(np.float32)
            
        if isinstance(dst_img, Image.Image):
            dst_np = np.array(dst_img).astype(np.float32)
        else:
            dst_np = dst_img.astype(np.float32)
        
        # Ensure mask has same spatial dimensions as images
        if mask.shape[:2] != dst_np.shape[:2]:
            mask_resized = cv2.resize(mask, (dst_np.shape[1], dst_np.shape[0]))
        else:
            mask_resized = mask
        
        # If mask is 3-channel, use it directly; else expand to 3 channels
        if len(mask_resized.shape) == 2:
            mask_3ch = np.stack([mask_resized] * 3, axis=-1)
        else:
            mask_3ch = mask_resized
        
        # Apply blending
        result = src_np * mask_3ch + dst_np * (1 - mask_3ch)
        result = np.clip(result, 0, 255).astype(np.uint8)
        
        return result
    
    def composite_images(self, person_image, warped_cloth, composition_mask):
        """
        Composite the person and warped cloth using the composition mask
        """
        # Convert to numpy arrays
        person_np = np.array(person_image).astype(np.float32)
        cloth_np = np.array(warped_cloth).astype(np.float32)
        
        # Ensure composition mask has same dimensions as images
        h, w = person_np.shape[:2]
        if composition_mask.shape[:2] != (h, w):
            composition_mask = cv2.resize(composition_mask, (w, h))
        
        # If composition mask is 2D, make it 3D to match image channels
        if len(composition_mask.shape) == 2:
            comp_mask_3ch = np.stack([composition_mask] * 3, axis=-1)
        else:
            comp_mask_3ch = composition_mask
        
        # Clamp mask values to [0, 1]
        comp_mask_3ch = np.clip(comp_mask_3ch, 0, 1)
        
        # Perform the composition
        result = cloth_np * comp_mask_3ch + person_np * (1 - comp_mask_3ch)
        result = np.clip(result, 0, 255).astype(np.uint8)
        
        # Convert back to PIL
        result_image = Image.fromarray(result, 'RGB')
        
        return result_image

    def refine_with_unet(self, image, person_rep, cloth_image):
        """
        Apply a refinement U-Net to improve realism
        This is a simplified version of the refinement step
        """
        # For this implementation, we'll apply some post-processing filters
        # to improve the appearance
        
        np_image = np.array(image)
        
        # Apply slight sharpening to enhance details
        kernel = np.array([[-1,-1,-1],
                          [-1, 9,-1],
                          [-1,-1,-1]])
        sharpened = cv2.filter2D(np_image, -1, kernel)
        
        # Apply bilateral filter to reduce noise while preserving edges
        refined = cv2.bilateralFilter(sharpened, 9, 75, 75)
        
        return Image.fromarray(refined, 'RGB')


def blend_images(person_image, warped_cloth, parsing_masks, keypoints=None, garment_type='top'):
    """
    Main function to blend person and cloth images
    """
    comp_module = CompositionModule()

    # Ensure warped cloth has the same dimensions as person image
    person_np = np.array(person_image)
    warped_np = np.array(warped_cloth)

    if person_np.shape[:2] != warped_np.shape[:2]:
        # Resize warped cloth to match person image dimensions
        warped_cloth = warped_cloth.resize(person_image.size, Image.Resampling.LANCZOS)
        warped_np = np.array(warped_cloth)  # Update warped_np after resize

    # Create composition mask based on garment type
    try:
        comp_mask = comp_module.create_composition_mask(
            person_np,
            parsing_masks,
            keypoints,
            garment_type
        )
    except Exception as e:
        print(f"Error creating composition mask: {e}. Falling back to upper clothes mask.")
        # Fallback: use upper clothes mask directly from parsing
        if garment_type == 'top':
            upper_mask = parsing_masks.get('upper', np.zeros_like(person_np[:, :, 0]))
            if len(upper_mask.shape) == 2:
                comp_mask = np.stack([upper_mask] * 3, axis=-1)  # Convert to 3-channel mask
            else:
                comp_mask = upper_mask  # Already has multiple channels
        elif garment_type == 'bottom':
            lower_mask = parsing_masks.get('lower', np.zeros_like(person_np[:, :, 0]))
            if len(lower_mask.shape) == 2:
                comp_mask = np.stack([lower_mask] * 3, axis=-1)  # Convert to 3-channel mask
            else:
                comp_mask = lower_mask  # Already has multiple channels
        else:  # full body or default
            upper_mask = parsing_masks.get('upper', np.zeros_like(person_np[:, :, 0]))
            lower_mask = parsing_masks.get('lower', np.zeros_like(person_np[:, :, 0]))
            combined_mask = np.maximum(upper_mask, lower_mask)
            if len(combined_mask.shape) == 2:
                comp_mask = np.stack([combined_mask] * 3, axis=-1)  # Convert to 3-channel mask
            else:
                comp_mask = combined_mask  # Already has multiple channels

    # Ensure the composition mask has the same dimensions as the person image
    h, w = person_np.shape[:2]
    if comp_mask.shape[:2] != (h, w):
        # If mask is 2D, resize it directly
        if len(comp_mask.shape) == 2:
            comp_mask = cv2.resize(comp_mask, (w, h))
        else:
            # If mask is 3D, resize each channel separately
            comp_mask_resized = np.zeros((h, w, comp_mask.shape[2]), dtype=comp_mask.dtype)
            for i in range(comp_mask.shape[2]):
                comp_mask_resized[:, :, i] = cv2.resize(comp_mask[:, :, i], (w, h))
            comp_mask = comp_mask_resized

    # Ensure that both person_image and warped_cloth are the same size before composition
    if person_image.size != warped_cloth.size:
        warped_cloth = warped_cloth.resize(person_image.size, Image.Resampling.LANCZOS)

    # Ensure the composition mask has the same dimensions as the person image
    h, w = person_np.shape[:2]
    if comp_mask.shape[:2] != (h, w):
        # If mask is 2D, resize it directly
        if len(comp_mask.shape) == 2:
            comp_mask = cv2.resize(comp_mask, (w, h))
        else:
            # If mask is 3D, resize each channel separately
            comp_mask_resized = np.zeros((h, w, comp_mask.shape[2]), dtype=comp_mask.dtype)
            for i in range(comp_mask.shape[2]):
                comp_mask_resized[:, :, i] = cv2.resize(comp_mask[:, :, i], (w, h))
            comp_mask = comp_mask_resized

    # Perform composition
    try:
        result = comp_module.composite_images(person_image, warped_cloth, comp_mask)
    except Exception as e:
        print(f"Error in composition: {e}. Falling back to simple alpha blending.")
        # Fallback to simple alpha blending
        result = comp_module.alpha_blend(warped_cloth, person_image, comp_mask)

    # Refine the result
    try:
        result = comp_module.refine_with_unet(result, None, warped_cloth)
    except Exception as e:
        print(f"Error in refinement: {e}. Returning result without refinement.")
        # Just return the result without refinement if it fails

    return result, comp_mask


def color_match(source_img, target_img, mask):
    """
    Perform color matching between source and target regions within mask
    """
    # Convert to numpy arrays
    source_np = np.array(source_img).astype(np.float32)
    target_np = np.array(target_img).astype(np.float32)
    
    # If mask is 3-channel, use the first channel
    if len(mask.shape) == 3:
        mask_2d = mask[:, :, 0]
    else:
        mask_2d = mask
    
    # Find the region to transfer
    mask_region = mask_2d > 0.5
    
    # Calculate mean and std of source and target regions
    src_region = source_np[mask_region]
    tgt_region = target_np[mask_region]
    
    if len(src_region) > 0 and len(tgt_region) > 0:
        # Calculate statistics
        src_mean = np.mean(src_region, axis=0)
        src_std = np.std(src_region, axis=0)
        tgt_mean = np.mean(tgt_region, axis=0)
        tgt_std = np.std(tgt_region, axis=0)
        
        # Normalize source region
        normalized = (src_region - src_mean) / (src_std + 1e-6)
        
        # Match target statistics
        matched = normalized * (tgt_std + 1e-6) + tgt_mean
        
        # Clip values
        matched = np.clip(matched, 0, 255)
        
        # Create result image
        result = source_np.copy()
        result[mask_region] = matched
        
        return Image.fromarray(result.astype(np.uint8), 'RGB')
    
    return source_img


def post_process(image, person_image, warped_cloth, parsing_masks, keypoints=None):
    """
    Apply post-processing including color matching and shadow addition
    """
    # Apply color matching to make cloth blend better with person
    comp_module = CompositionModule()
    comp_mask = comp_module.create_composition_mask(
        np.array(person_image),
        parsing_masks,
        keypoints
    )

    # Extract the garment region from the composition mask
    garment_region = comp_mask
    if len(garment_region.shape) == 3:
        garment_region = garment_region[:, :, 0]

    # Apply color matching
    color_matched = color_match(image, person_image, garment_region)

    # Additional refinements can be added here
    # like shadow addition, edge smoothing, etc.

    return color_matched


def create_debug_visuals(person_image, cloth_image, warped_cloth, composition_mask, result_image):
    """
    Create debug visualizations showing the pipeline steps
    """
    debug_images = {}

    # Convert images to numpy for easier manipulation
    person_np = np.array(person_image)
    cloth_np = np.array(cloth_image)
    warped_np = np.array(warped_cloth)
    result_np = np.array(result_image)

    # Create a grid visualization
    h, w = person_np.shape[:2]

    # Create a debug image showing all steps
    debug_height = h * 2
    debug_width = w * 2
    debug_img = np.zeros((debug_height, debug_width, 3), dtype=np.uint8)

    # Place original person (top-left)
    debug_img[0:h, 0:w] = person_np

    # Place original cloth (top-right)
    cloth_resized = cv2.resize(cloth_np, (w, h))
    debug_img[0:h, w:w*2] = cloth_resized

    # Place warped cloth (bottom-left)
    warped_resized = cv2.resize(warped_np, (w, h))
    debug_img[h:h*2, 0:w] = warped_resized

    # Place result (bottom-right)
    result_resized = cv2.resize(result_np, (w, h))
    debug_img[h:h*2, w:w*2] = result_resized

    debug_images['pipeline_steps'] = Image.fromarray(debug_img)
    debug_images['composition_mask'] = Image.fromarray((composition_mask[:, :, 0] * 255).astype(np.uint8), 'L') if len(composition_mask.shape) == 3 else Image.fromarray((composition_mask * 255).astype(np.uint8), 'L')

    return debug_images


if __name__ == "__main__":
    print("Composition Module ready!")