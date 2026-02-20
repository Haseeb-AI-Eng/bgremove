"""
Image Processing API - FastAPI Application
Provides multiple endpoints for image processing:
1. Remove background from images
2. Replace clothes in images with new clothes images (masking & segmentation)
3. Change clothes color in images (color shifting)
4. Change background color in images
5. Replace background with custom image
6. User authentication and payment processing
"""

import io
import os
import sys
import glob
import uuid
from pathlib import Path
from typing import Optional
from fastapi import FastAPI, File, UploadFile, HTTPException, Form, Depends, Query
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi import Request
from fastapi import status
from PIL import Image, ImageEnhance, ImageFilter
import numpy as np
from rembg import remove, new_session
import cv2
import json
import time
import base64
from io import BytesIO
import requests
from datetime import datetime, timedelta
from dotenv import load_dotenv
import openai
from enum import Enum

# Load environment variables
load_dotenv()

# Initialize OpenAI client
openai_client = None
if os.getenv("OPENAI_API_KEY"):
    openai_client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Import authentication and payment modules
import jwt
from auth import (
    UserRegister, UserLogin, UserInDB, create_user, authenticate_user,
    create_access_token, get_current_user, get_user, update_user_subscription,
    update_user_profile, update_user_profile_image, ACCESS_TOKEN_EXPIRE_MINUTES,
    get_current_user_or_api_key, get_user_by_api_key,
    create_auth_response, Token, RefreshTokenRequest, create_refresh_token,
    is_refresh_token_valid, invalidate_refresh_token, security,
    create_api_key_for_user, get_api_keys_for_user, get_api_key_by_id,
    revoke_api_key, delete_api_key, APIKey, require_api_key
)
from payment import create_payment_intent, create_subscription, verify_payment_status, PaymentIntentCreate, SubscriptionCreate
import stripe

# Import cache management and production config
try:
    from cache_manager import setup_cache_management
except ImportError:
    setup_cache_management = None
    print("Cache manager not available")

try:
    from production_config import configure_app
except ImportError:
    configure_app = None
    print("Production config not available")

# Add the app directory to the path to properly import submodules
current_dir = os.path.dirname(__file__)
sys.path.insert(0, current_dir)

from human_parsing.human_parsing_model import load_pretrained_model, get_parsing_map, extract_garment_masks, get_high_accuracy_garment_masks
from pose_estimation.pose_estimator import estimate_pose_from_image
from warping.warping_module import warp_cloth_tps, create_cloth_mask_from_image
from composition.composition_module import blend_images, post_process as comp_post_process
from enhanced_blending import enhanced_blend_images, create_enhanced_composition_mask, enhanced_difference_detection
from enhanced_segmentation import enhanced_garment_segmentation, manual_mask_correction, refine_mask_boundaries, validate_mask_accuracy
from enhanced_difference_detection import detect_replacement_quality
from refinement.refinement_module import enhance_realism
from post_processing.post_processing_module import post_process_pipeline, enhance_contrast_brightness, sharpen_image
from composition.composition_module import create_debug_visuals

class AutoAgentOperation(str, Enum):
    BACKGROUND_REMOVE = "background_remove"
    BACKGROUND_CHANGE_COLOR = "background_change_color"
    BACKGROUND_REPLACE = "background_replace"
    CLOTHES_CHANGE = "clothes_change"
    OBJECT_REMOVE = "object_remove"
    OBJECT_ADD = "object_add"
    COLOR_ADJUST = "color_adjust"
    RESIZE = "resize"
    ENHANCE = "enhance"
    FILTER = "filter"


def analyze_instruction_with_ai(instruction: str) -> dict:
    """
    Use OpenAI to analyze the user instruction and determine what operations to perform
    """
    if not openai_client:
        # Fallback to keyword matching if OpenAI is not configured
        return analyze_instruction_fallback(instruction)

    prompt = f"""
    Analyze the following instruction and break it down into specific image processing operations:

    Instruction: "{instruction}"

    Return a JSON object with the following structure:
    {{
        "operations": [
            {{
                "type": "operation_type",
                "parameters": {{"key": "value"}}
            }}
        ],
        "description": "Brief description of what will be done"
    }}

    Available operation types:
    - background_remove: Remove the background
    - background_change_color: Change background to a specific color
    - background_replace: Replace background with a new one
    - clothes_change: Change clothes in the image
    - object_remove: Remove a specific object
    - object_add: Add an object to the image
    - color_adjust: Adjust colors, brightness, contrast
    - resize: Resize the image
    - enhance: Enhance image quality
    - filter: Apply a filter

    Be specific about parameters like colors, objects to remove/add, etc.
    """

    try:
        response = openai_client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are an expert at understanding image processing instructions. Analyze the user's request and break it down into specific operations with parameters."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1,
            max_tokens=500,
            response_format={"type": "json_object"}
        )

        result = json.loads(response.choices[0].message.content)
        return result
    except Exception as e:
        print(f"Error calling OpenAI API: {e}")
        # Fallback to keyword matching if API call fails
        return analyze_instruction_fallback(instruction)


def analyze_instruction_fallback(instruction: str) -> dict:
    """
    Fallback function to analyze instruction using keyword matching
    """
    instruction_lower = instruction.lower()
    operations = []

    # Background removal
    if any(keyword in instruction_lower for keyword in ['background', 'bg', 'remove', 'transparent', 'erase', 'delete']) and \
       any(keyword in instruction_lower for keyword in ['remove', 'delete', 'erase', 'get rid', 'take out', 'no background']):
        operations.append({
            "type": "background_remove",
            "parameters": {}
        })

    # Background color change
    elif any(keyword in instruction_lower for keyword in ['background', 'bg', 'color', 'colour']) and \
         any(keyword in instruction_lower for keyword in ['change', 'replace', 'set', 'to', 'make it']):
        bg_color = "FFFFFF"  # Default to white
        color_keywords = {
            'white': 'FFFFFF', 'black': '000000', 'red': 'FF0000', 'blue': '0000FF',
            'green': '00FF00', 'yellow': 'FFFF00', 'purple': '800080', 'pink': 'FFC0CB',
            'orange': 'FFA500', 'brown': 'A52A2A', 'gray': '808080', 'grey': '808080',
            'cyan': '00FFFF', 'magenta': 'FF00FF', 'silver': 'C0C0C0', 'gold': 'FFD700'
        }

        for color_word, hex_val in color_keywords.items():
            if color_word in instruction_lower:
                bg_color = hex_val
                break

        import re
        hex_colors = re.findall(r'#([A-Fa-f0-9]{6})', instruction)
        if hex_colors:
            bg_color = hex_colors[0]

        operations.append({
            "type": "background_change_color",
            "parameters": {"color": bg_color}
        })

    # Image enhancement operations
    elif any(keyword in instruction_lower for keyword in ['enhance', 'enhancement', 'quality', 'sharp', 'sharpen', 'sharpening', 'improve', 'better', 'clear', 'clarity', 'detail', 'details']):
        operations.append({
            "type": "enhance",
            "parameters": {}
        })

    # Default to background removal if no specific operation identified
    elif operations == []:
        operations.append({
            "type": "background_remove",
            "parameters": {}
        })

    return {
        "operations": operations,
        "description": f"Processing based on instruction: {instruction}"
    }


def execute_operations(image, operations: list) -> Image.Image:
    """
    Execute the sequence of operations on the image
    """
    result_img = image.copy()

    for operation in operations:
        op_type = operation["type"]
        params = operation.get("parameters", {})

        if op_type == "background_remove":
            # Convert to bytes for rembg
            img_byte_arr = io.BytesIO()
            result_img.save(img_byte_arr, format='PNG')
            img_byte_arr.seek(0)

            output = remove(img_byte_arr.getvalue(), session=session)
            result_img = Image.open(io.BytesIO(output)).convert("RGB")

        elif op_type == "background_change_color":
            color_hex = params.get("color", "FFFFFF")
            # Remove background first
            img_byte_arr = io.BytesIO()
            result_img.save(img_byte_arr, format='PNG')
            img_byte_arr.seek(0)

            removed_bg = remove(img_byte_arr.getvalue(), session=session)
            img_with_transparency = Image.open(io.BytesIO(removed_bg)).convert("RGBA")

            # Create new background with specified color
            bg_rgba = Image.new("RGBA", img_with_transparency.size,
                               tuple(int(color_hex[i:i+2], 16) for i in (0, 2, 4)) + (255,))

            # Composite the transparent image onto the colored background
            composited = Image.alpha_composite(bg_rgba, img_with_transparency)
            result_img = composited.convert("RGB")

        elif op_type == "color_adjust":
            # Adjust brightness, contrast, saturation
            brightness_factor = params.get("brightness", 1.0)
            contrast_factor = params.get("contrast", 1.0)
            saturation_factor = params.get("saturation", 1.0)

            # Convert to numpy array for processing
            img_array = np.array(result_img)

            # Apply brightness adjustment
            if brightness_factor != 1.0:
                img_array = np.clip(img_array * brightness_factor, 0, 255).astype(np.uint8)

            # Convert back to PIL Image for further processing
            result_img = Image.fromarray(img_array)

            # Apply contrast adjustment using ImageEnhance
            if contrast_factor != 1.0:
                enhancer = ImageEnhance.Contrast(result_img)
                result_img = enhancer.enhance(contrast_factor)

            # Apply saturation adjustment
            if saturation_factor != 1.0:
                enhancer = ImageEnhance.Color(result_img)
                result_img = enhancer.enhance(saturation_factor)

        elif op_type == "enhance":
            # Apply powerful enhancement using our new function
            result_img = enhance_image_quality(result_img)

    return result_img


def add_watermark(image, user_id):
    """
    Add a super dark, bright shiny kite-shaped logo watermark that's clearly visible on any background
    """
    from PIL import ImageDraw, ImageFont
    import hashlib

    # Create a copy of the image to draw on
    watermarked = image.copy()

    # Create a unique identifier based on user_id
    unique_id = hashlib.md5(user_id.encode()).hexdigest()[:8]  # Take first 8 chars

    # Convert to RGBA if not already (required for alpha compositing)
    if watermarked.mode != 'RGBA':
        watermarked = watermarked.convert('RGBA')

    # Create a transparent overlay for the watermark
    watermark_overlay = Image.new('RGBA', watermarked.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(watermark_overlay)

    # Define watermark position (bottom-left corner)
    img_width, img_height = watermarked.size
    padding = 20
    size_factor = min(img_width, img_height) / 400  # Scale with image size
    kite_size = int(40 * size_factor)

    # Calculate kite position in bottom-left with slight forward tilt
    center_x = padding + kite_size // 2 + 5  # Slight right offset for forward tilt
    center_y = img_height - padding - kite_size // 2

    # Define kite shape points with slight directional tilt (forward)
    top_y = center_y - kite_size // 2 - 2  # Tilted forward
    bottom_y = center_y + kite_size // 2 + 2
    left_x = center_x - kite_size // 3
    right_x = center_x + kite_size // 3

    # Create premium super dark kite shape with bright shiny effect
    # Main kite outline with super dark embossed look
    kite_points = [
        (center_x, top_y),  # Top point
        (right_x, center_y),  # Right point
        (center_x, bottom_y),  # Bottom point
        (left_x, center_y),  # Left point
        (center_x, top_y)  # Close the shape
    ]

    # Create super dark fabric-like fill with maximum opacity for visibility
    dark_fill_color = (15, 15, 25, 220)  # Super dark gray with very high opacity
    dark_outline_color = (140, 140, 160, 240)  # Brighter outline for contrast
    draw.polygon(kite_points[:-1], fill=dark_fill_color, outline=dark_outline_color, width=4)

    # Add very bright inner shine effect for maximum depth and contrast
    inner_points = [
        (center_x, top_y + 4),
        (right_x - 3, center_y),
        (center_x, bottom_y - 4),
        (left_x + 3, center_y)
    ]
    inner_fill = (250, 250, 255, 150)  # Very bright inner for maximum contrast
    draw.polygon(inner_points[:-1], fill=inner_fill, outline=inner_fill)

    # Add subtle fabric texture lines inside the kite
    fabric_line_color = (60, 60, 80, 180)  # Darker texture lines

    # Horizontal texture lines
    for i in range(3):
        y_pos = top_y + (bottom_y - top_y) * (i + 1) / 4
        x_start = left_x + (right_x - left_x) * 0.1
        x_end = right_x - (right_x - left_x) * 0.1
        draw.line([(x_start, y_pos), (x_end, y_pos)], fill=fabric_line_color, width=2)

    # Add diagonal stitching lines for fashion detail - super bright
    stitch_color = (180, 180, 200, 220)  # Super bright stitching for maximum visibility
    # Diagonal lines
    draw.line([(left_x + 4, center_y - 4), (right_x - 4, center_y + 4)], fill=stitch_color, width=3)
    draw.line([(left_x + 4, center_y + 4), (right_x - 4, center_y - 4)], fill=stitch_color, width=3)

    # Add super bright highlight to one side for glossy effect
    highlight_color = (250, 250, 255, 240)  # Super bright highlight
    draw.line([(center_x - 5, top_y + 3), (center_x + 5, top_y + 3)], fill=highlight_color, width=4)

    # Add strongest shadow effect for maximum embossed look
    shadow_color = (0, 0, 0, 140)  # Strongest shadow
    shadow_points = [
        (center_x + 3, top_y + 3),
        (right_x + 3, center_y + 3),
        (center_x + 3, bottom_y + 3),
        (left_x + 3, center_y + 3)
    ]
    draw.polygon(shadow_points[:-1], outline=shadow_color, width=3)

    # Add directional thread-like element inside the kite (flowing from top to bottom)
    thread_color = (220, 220, 240, 220)  # Super bright thread
    # Draw a subtle "thread" from top to center
    draw.arc([center_x - 3, top_y + 3, center_x + 3, center_y - 6],
             start=180, end=360, fill=thread_color, width=3)

    # Add a small text identifier with premium styling
    try:
        font_size = max(6, int(kite_size / 5))
        font = ImageFont.truetype("arial.ttf", size=font_size)
    except:
        font = ImageFont.load_default()

    text = unique_id[:2]  # Use first 2 chars
    try:
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
    except:
        text_width = len(text) * font_size // 2
        text_height = font_size

    # Position text with premium styling in bottom-right of kite
    text_x = right_x - text_width - 4
    text_y = center_y + 6
    text_color = (250, 250, 255, 250)  # Super light gray for maximum contrast
    draw.text((text_x, text_y), text, fill=text_color, font=font)

    # Add a super strong shiny effect to the entire watermark
    shine_layer = Image.new('RGBA', watermarked.size, (0, 0, 0, 0))
    shine_draw = ImageDraw.Draw(shine_layer)

    # Add a super bright glow around the entire kite
    glow_color = (250, 250, 255, 120)  # Super bright glow
    # Create a slightly larger kite shape for most prominent glow
    glow_offset = 5
    glow_points = [
        (center_x, top_y - glow_offset),
        (right_x + glow_offset, center_y),
        (center_x, bottom_y + glow_offset),
        (left_x - glow_offset, center_y)
    ]
    shine_draw.polygon(glow_points[:-1], outline=glow_color, width=3)

    # Composite the shine layer
    watermark_overlay = Image.alpha_composite(watermark_overlay, shine_layer)

    # Composite the watermark onto the original image
    watermarked = Image.alpha_composite(watermarked, watermark_overlay)

    # Convert back to RGB if the original was in RGB
    if image.mode == 'RGB':
        watermarked = watermarked.convert('RGB')

    return watermarked

# Initialize FastAPI app
app = FastAPI(
    title="Image Processing API",
    description="API for image processing tasks: background removal, clothing replacement with segmentation, clothing color change, and background manipulation",
    version="1.0.0"
)

# Configure app with production settings if available
if configure_app:
    app = configure_app(app)
else:
    # Add standard CORS middleware as fallback
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

# Setup cache management if available
if setup_cache_management:
    setup_cache_management(app)

# Create uploads directory if it doesn't exist
# Use absolute path relative to the main.py file location
uploads_dir = os.path.join(os.path.dirname(__file__), "uploads")
os.makedirs(uploads_dir, exist_ok=True)

# Mount static files directory for uploaded images
app.mount("/uploads", StaticFiles(directory=uploads_dir), name="uploads")

# Initialize rembg session for background removal
try:
    session = new_session()
except Exception as e:
    print(f"Failed to initialize rembg session: {e}")
    session = None



@app.get("/")
async def root():
    """Root endpoint - returns API information"""
    return {
        "name": "Image Processing API",
        "version": "1.0.0",
        "endpoints": {
            "remove_background": "/api/remove-background",
            "change_clothes": "/api/change-clothes",  # Change color of existing clothes
            "replace_clothes": "/api/replace-clothes",  # Replace clothes with new clothes image
            "change_background": "/api/change-background",
            "replace_background": "/api/replace-background"
        }
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}


@app.get("/api/gallery/images")
async def get_gallery_images(current_user: UserInDB = Depends(get_current_user)):
    """
    Retrieve list of processed images from output directory for the current user.
    Returns a list of image metadata with paths accessible via API.
    """
    try:
        output_dir = os.path.join(current_dir, "output")
        os.makedirs(output_dir, exist_ok=True)

        # Define the supported image types
        image_extensions = ['.png', '.jpg', '.jpeg', '.gif', '.bmp', '.tiff']

        # Get all image files in the output directory
        image_files = []
        for filename in os.listdir(output_dir):
            if any(filename.lower().endswith(ext) for ext in image_extensions):
                # Look for corresponding metadata JSON file
                metadata_path = os.path.join(output_dir, f"{filename}.json")
                metadata = None

                if os.path.exists(metadata_path):
                    try:
                        with open(metadata_path, 'r') as f:
                            metadata = json.load(f)
                    except:
                        pass  # If JSON parsing fails, we'll create basic metadata below

                # If metadata exists, use it, otherwise create basic info from filename
                if metadata:
                    # Only include images that belong to the current user
                    if metadata.get("user_id") == current_user.id or current_user.is_pro:
                        image_info = metadata
                        image_files.append(image_info)
                else:
                    # Parse timestamp from filename if following the pattern result_{timestamp}.png
                    if filename.startswith("result_") and len(filename) > 7:
                        try:
                            # Extract timestamp from filename
                            name_part = filename[7:]  # Remove "result_" prefix
                            timestamp_str = name_part.split('.')[0]  # Remove extension
                            timestamp = int(timestamp_str)
                            timestamp_formatted = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(timestamp))
                        except (ValueError, IndexError):
                            # If parsing fails, use file modification time
                            file_path = os.path.join(output_dir, filename)
                            timestamp = int(os.path.getmtime(file_path))
                            timestamp_formatted = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(timestamp))
                    else:
                        # If filename doesn't follow the expected pattern, use modification time
                        file_path = os.path.join(output_dir, filename)
                        timestamp = int(os.path.getmtime(file_path))
                        timestamp_formatted = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(timestamp))

                    # Try to determine operation type from the filename or just default to generic
                    if "bg_changed" in filename or "background" in filename.lower():
                        operation = "change-background"
                    elif "background_replaced" in filename:
                        operation = "replace-background"
                    elif "removed" in filename or "remove" in filename:
                        operation = "remove-background"
                    else:
                        operation = "unknown"

                    # For images without metadata, we'll allow them if user is pro or filter appropriately
                    if current_user.is_pro:
                        image_info = {
                            "id": filename,
                            "filename": filename,
                            "path": f"/api/image/{filename}",
                            "timestamp": timestamp_formatted,
                            "operation": operation,
                            "title": f"Processed Image {filename}",
                            "user_id": current_user.id  # Add user ID to track
                        }
                        image_files.append(image_info)

        # Sort by timestamp (newest first)
        image_files.sort(key=lambda x: x.get('timestamp', ''), reverse=True)

        return {
            "images": image_files,
            "count": len(image_files)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving images: {str(e)}")


@app.get("/api/gallery/images/{operation}")
async def get_gallery_images_by_operation(operation: str, current_user: UserInDB = Depends(get_current_user)):
    """
    Retrieve list of processed images filtered by operation type for the current user.
    Operation can be: remove-background, change-background, replace-background, replace-clothes
    """
    try:
        output_dir = os.path.join(current_dir, "output")
        os.makedirs(output_dir, exist_ok=True)

        # Define the supported image types
        image_extensions = ['.png', '.jpg', '.jpeg', '.gif', '.bmp', '.tiff']

        # Get all image files in the output directory
        image_files = []
        for filename in os.listdir(output_dir):
            if any(filename.lower().endswith(ext) for ext in image_extensions):
                # Look for corresponding metadata JSON file
                metadata_path = os.path.join(output_dir, f"{filename}.json")
                metadata = None

                if os.path.exists(metadata_path):
                    try:
                        with open(metadata_path, 'r') as f:
                            metadata = json.load(f)
                    except:
                        continue  # Skip if JSON parsing fails

                # If metadata exists and operation matches, add to results
                # Also check that it belongs to the current user
                if (metadata and
                    metadata.get("operation", "").lower() == operation.lower() and
                    (metadata.get("user_id") == current_user.id or current_user.is_pro)):
                    image_files.append(metadata)

        # Sort by timestamp (newest first)
        image_files.sort(key=lambda x: x.get('timestamp', ''), reverse=True)

        return {
            "images": image_files,
            "count": len(image_files),
            "operation": operation
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving images: {str(e)}")


@app.get("/api/image/{filename}")
async def get_image(filename: str):
    """
    Serve a specific processed image from the output directory.
    """
    try:
        output_dir = os.path.join(current_dir, "output")
        file_path = os.path.join(output_dir, filename)

        # Security check: ensure the path is within the output directory
        file_path = os.path.abspath(file_path)
        output_dir_abs = os.path.abspath(output_dir)

        if not file_path.startswith(output_dir_abs):
            raise HTTPException(status_code=400, detail="Invalid file path")

        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail="Image not found")

        # Check if it's an image file for security
        _, ext = os.path.splitext(filename.lower())
        allowed_extensions = ['.png', '.jpg', '.jpeg', '.gif', '.bmp', '.tiff']
        if ext not in allowed_extensions:
            raise HTTPException(status_code=400, detail="Invalid file type")

        return StreamingResponse(
            open(file_path, 'rb'),
            media_type=f"image/{ext[1:]}",  # Remove the dot from extension
            headers={"Content-Disposition": f"inline; filename={filename}"}
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving image: {str(e)}")


@app.post("/api/public-remove-background")
async def public_remove_background(
    file: UploadFile = File(...)
):
    """
    Remove background from an image.

    Args:
        file: Image file (PNG, JPG, etc.)

    Returns:
        PNG image with transparent background
    """
    try:
        # Read the uploaded file
        contents = await file.read()

        # Validate file type by checking file signature
        if not contents[:4] in [b'\x89PNG', b'\xFF\xD8\xFF', b'GIF8', b'\x49\x49\x2A\x00', b'\x4D\x4D\x00\x2A', b'\x00\x00\x00\x0C']:
            # Not perfect but checks for common image formats: PNG, JPEG, GIF, TIFF, etc.
            # Use file extension as backup check as well
            file_ext = os.path.splitext(file.filename)[1].lower()
            allowed_exts = ['.png', '.jpg', '.jpeg', '.gif', '.bmp', '.tiff', '.webp']
            if file_ext not in allowed_exts:
                raise HTTPException(status_code=400, detail="Invalid file type. Only image files are allowed")

        # Validate file size (max 10MB)
        if len(contents) > 10 * 1024 * 1024:
            raise HTTPException(status_code=400, detail="File size exceeds 10MB limit")

        # Try to open image with PIL to validate it's a valid image file
        try:
            img = Image.open(io.BytesIO(contents))
            img.verify()  # Verify that it's a valid image
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid or corrupted image file")

        # Reopen image after verification
        img = Image.open(io.BytesIO(contents))

        # Process image with rembg
        output = remove(contents, session=session)

        # Convert to PIL Image
        result_img = Image.open(io.BytesIO(output))

        # Convert to RGB for watermarking
        if result_img.mode == 'RGBA':
            img_rgb = result_img.convert("RGB")
        else:
            img_rgb = result_img

        # Add watermark with anonymous identifier for public endpoint
        watermarked_img = add_watermark(img_rgb, "anonymous_user")

        # Save to bytes
        output_bytes = io.BytesIO()
        watermarked_img.save(output_bytes, format="PNG")
        output_bytes.seek(0)

        # Return as PNG
        return StreamingResponse(
            output_bytes,
            media_type="image/png",
            headers={"Content-Disposition": "attachment; filename=output.png"}
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing image: {str(e)}")


@app.post("/api/public-passport-photo")
async def public_passport_photo(
    file: UploadFile = File(...),
    bg_color: str = Form("blue")
):
    """
    Transform an image to passport photo size with colored background.
    
    Standard passport photo sizes:
    - US: 2x2 inches (51x51 mm)
    - EU/International: 35x45 mm
    - Common pixel size at 300 DPI: 600x600 pixels (2x2 inches)

    Args:
        file: Image file (PNG, JPG, etc.)
        bg_color: Background color ("blue", "white", "red", "gray", "light-blue")

    Returns:
        PNG image with passport photo dimensions and background
    """
    try:
        # Read the uploaded file
        contents = await file.read()

        # Validate file type by checking file signature
        if not contents[:4] in [b'\x89PNG', b'\xFF\xD8\xFF', b'GIF8', b'\x49\x49\x2A\x00', b'\x4D\x4D\x00\x2A', b'\x00\x00\x00\x0C']:
            # Not perfect but checks for common image formats: PNG, JPEG, GIF, TIFF, etc.
            # Use file extension as backup check as well
            file_ext = os.path.splitext(file.filename)[1].lower()
            allowed_exts = ['.png', '.jpg', '.jpeg', '.gif', '.bmp', '.tiff', '.webp']
            if file_ext not in allowed_exts:
                raise HTTPException(status_code=400, detail="Invalid file type. Only image files are allowed")

        # Validate file size (max 10MB)
        if len(contents) > 10 * 1024 * 1024:
            raise HTTPException(status_code=400, detail="File size exceeds 10MB limit")

        # Try to open image with PIL to validate it's a valid image file
        try:
            img = Image.open(io.BytesIO(contents))
            img.verify()  # Verify that it's a valid image
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid or corrupted image file")

        # Reopen image after verification
        img = Image.open(io.BytesIO(contents))

        # Process image with rembg to remove background first
        output = remove(contents, session=session)

        # Convert to PIL Image
        result_img = Image.open(io.BytesIO(output))

        # Apply passport photo transformation
        result_img = transform_to_passport_photo(result_img, bg_color)

        # Convert to RGB for watermarking
        if result_img.mode == 'RGBA':
            img_rgb = result_img.convert("RGB")
        else:
            img_rgb = result_img

        # Add watermark with anonymous identifier for public endpoint
        watermarked_img = add_watermark(img_rgb, "anonymous_user")

        # Save to bytes
        output_bytes = io.BytesIO()
        watermarked_img.save(output_bytes, format="PNG")
        output_bytes.seek(0)

        # Return as PNG
        return StreamingResponse(
            output_bytes,
            media_type="image/png",
            headers={"Content-Disposition": "attachment; filename=passport_photo.png"}
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing passport photo: {str(e)}")


@app.post("/api/change-clothes")
async def change_clothes(
    original_image: UploadFile = File(..., description="Original image with person wearing clothes to be replaced"),
    new_clothes_image: UploadFile = File(..., description="New clothes image to replace with"),
    current_user: UserInDB = Depends(get_current_user_or_api_key)
):
    """
    Replace clothes in original image with new clothes image using segmentation.

    Args:
        original_image: Original image with person wearing clothes to be replaced (PNG, JPG, etc.)
        new_clothes_image: New clothes image to replace with (PNG, JPG, etc.)

    Returns:
        Image with original person wearing new clothes
    """
    try:
        # Read both uploaded files
        original_contents = await original_image.read()
        new_clothes_contents = await new_clothes_image.read()

        # Validate file type for original image
        if not original_contents[:4] in [b'\x89PNG', b'\xFF\xD8\xFF', b'GIF8', b'\x49\x49\x2A\x00', b'\x4D\x4D\x00\x2A', b'\x00\x00\x00\x0C']:
            file_ext = os.path.splitext(original_image.filename)[1].lower()
            allowed_exts = ['.png', '.jpg', '.jpeg', '.gif', '.bmp', '.tiff', '.webp']
            if file_ext not in allowed_exts:
                raise HTTPException(status_code=400, detail="Invalid file type for original image. Only image files are allowed")

        # Validate file type for new clothes image
        if not new_clothes_contents[:4] in [b'\x89PNG', b'\xFF\xD8\xFF', b'GIF8', b'\x49\x49\x2A\x00', b'\x4D\x4D\x00\x2A', b'\x00\x00\x00\x0C']:
            clothes_file_ext = os.path.splitext(new_clothes_image.filename)[1].lower()
            allowed_exts = ['.png', '.jpg', '.jpeg', '.gif', '.bmp', '.tiff', '.webp']
            if clothes_file_ext not in allowed_exts:
                raise HTTPException(status_code=400, detail="Invalid file type for clothes image. Only image files are allowed")

        # Validate file sizes (max 10MB each)
        if len(original_contents) > 10 * 1024 * 1024:
            raise HTTPException(status_code=400, detail="Original image file size exceeds 10MB limit")

        if len(new_clothes_contents) > 10 * 1024 * 1024:
            raise HTTPException(status_code=400, detail="New clothes image file size exceeds 10MB limit")

        # Try to open images with PIL to validate they're valid image files
        try:
            original_img_check = Image.open(io.BytesIO(original_contents))
            original_img_check.verify()
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid or corrupted original image file")

        try:
            clothes_img_check = Image.open(io.BytesIO(new_clothes_contents))
            clothes_img_check.verify()
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid or corrupted clothes image")

        # Open images
        original_img = Image.open(io.BytesIO(original_contents)).convert("RGB")
        clothes_img = Image.open(io.BytesIO(new_clothes_contents)).convert("RGB")

        # Resize clothes image to match the original image dimensions
        clothes_img = clothes_img.resize(original_img.size, Image.Resampling.LANCZOS)

        # Find clothing region in the original image
        clothes_mask = find_clothing_region(original_img)

        # Convert to numpy arrays for processing
        original_array = np.array(original_img)
        clothes_array = np.array(clothes_img)

        # Resize clothes image to fit the clothing area properly
        # First, we need to get the bounding box of the clothing area
        coords = np.column_stack(np.where(clothes_mask > 0))
        if coords.size > 0:
            y_min, x_min = coords.min(axis=0)
            y_max, x_max = coords.max(axis=0)

            # Calculate the size of the clothing area in the original image
            clothing_h, clothing_w = y_max - y_min, x_max - x_min

            # Resize the new clothes image to match the clothing area size
            resized_clothes = cv2.resize(clothes_array, (clothing_w, clothing_h), interpolation=cv2.INTER_CUBIC)

            # Create a canvas to place the resized clothes onto
            clothes_placement = np.zeros_like(original_array)

            # Place the resized clothes in the appropriate location
            if y_min + resized_clothes.shape[0] <= original_array.shape[0] and x_min + resized_clothes.shape[1] <= original_array.shape[1]:
                clothes_placement[y_min:y_min + resized_clothes.shape[0], x_min:x_min + resized_clothes.shape[1]] = resized_clothes

            # Create a more refined mask for blending - use the clothing mask as-is
            mask_3channel = np.stack([clothes_mask] * 3, axis=-1).astype(np.float32) / 255.0

            # Blend the original image with the new clothes using the mask
            result = original_array.copy()

            # For better blending, only replace pixels where the mask is white (clothing areas)
            result = original_array * (1 - mask_3channel) + clothes_placement * mask_3channel
            result = result.astype(np.uint8)
        else:
            # If no clothing area detected, just return original image
            result = original_array

        # Convert back to PIL Image
        result_img = Image.fromarray(result)

        # Add watermark with user ID for authenticated endpoint
        watermarked_img = add_watermark(result_img, current_user.id)

        # Save to the output directory
        output_dir = os.path.join(current_dir, "output")
        os.makedirs(output_dir, exist_ok=True)

        # Save the original uploaded images
        original_img_original = Image.open(io.BytesIO(original_contents))
        original_timestamp = int(time.time())
        original_filename = f"original_{original_timestamp}_{original_image.filename}"
        original_path = os.path.join(output_dir, original_filename)
        original_img_original.save(original_path)
        print(f"Saved original to {original_path}")

        # Save the clothes image as well
        clothes_img_original = Image.open(io.BytesIO(new_clothes_contents))
        clothes_filename = f"clothes_{original_timestamp}_{new_clothes_image.filename}"
        clothes_path = os.path.join(output_dir, clothes_filename)
        clothes_img_original.save(clothes_path)
        print(f"Saved clothes image to {clothes_path}")

        # Generate a unique filename for processed result
        timestamp = int(time.time())
        output_filename = f"result_{timestamp}.png"
        output_path = os.path.join(output_dir, output_filename)
        result_img.save(output_path)
        print(f"Saved result to {output_path}")

        # Also save metadata about this processed image
        metadata = {
            "id": output_filename,
            "input_filename": original_image.filename,
            "clothes_filename": new_clothes_image.filename,
            "original_filename": original_filename,
            "clothes_original_filename": clothes_filename,
            "operation": "change-clothes",
            "timestamp": timestamp,
            "timestamp_formatted": time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(timestamp)),
            "original_path": f"/api/image/{original_filename}",
            "clothes_path": f"/api/image/{clothes_filename}",
            "processed_path": f"/api/image/{output_filename}",
            "api_endpoint": f"/api/image/{output_filename}",
            "user_id": current_user.id,  # Add user ID to track
            "title": f"Changed {original_image.filename} clothes"
        }

        # Save metadata to a JSON file
        metadata_path = os.path.join(output_dir, f"{output_filename}.json")
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f)

        # Save to bytes
        output_bytes = io.BytesIO()
        watermarked_img.save(output_bytes, format="PNG")
        output_bytes.seek(0)

        return StreamingResponse(
            output_bytes,
            media_type="image/png",
            headers={"Content-Disposition": "attachment; filename=clothes_replaced.png"}
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing images: {str(e)}")


@app.post("/api/public-change-clothes")
async def public_change_clothes(
    original_image: UploadFile = File(..., description="Original image with person wearing clothes to be replaced"),
    new_clothes_image: UploadFile = File(..., description="New clothes image to replace with")
):
    """
    Replace clothes in original image with new clothes image using segmentation (public endpoint without authentication).

    Args:
        original_image: Original image with person wearing clothes to be replaced (PNG, JPG, etc.)
        new_clothes_image: New clothes image to replace with (PNG, JPG, etc.)

    Returns:
        Image with original person wearing new clothes
    """
    try:
        # Read both uploaded files
        original_contents = await original_image.read()
        new_clothes_contents = await new_clothes_image.read()

        # Validate file sizes (max 10MB each)
        if len(original_contents) > 10 * 1024 * 1024:
            raise HTTPException(status_code=400, detail="Original image file size exceeds 10MB limit")

        if len(new_clothes_contents) > 10 * 1024 * 1024:
            raise HTTPException(status_code=400, detail="New clothes image file size exceeds 10MB limit")

        # Open images
        original_img = Image.open(io.BytesIO(original_contents)).convert("RGB")
        clothes_img = Image.open(io.BytesIO(new_clothes_contents)).convert("RGB")

        # Resize clothes image to match the original image dimensions
        clothes_img = clothes_img.resize(original_img.size, Image.Resampling.LANCZOS)

        # Find clothing region in the original image
        clothes_mask = find_clothing_region(original_img)

        # Convert to numpy arrays for processing
        original_array = np.array(original_img)
        clothes_array = np.array(clothes_img)

        # Resize clothes image to fit the clothing area properly
        # First, we need to get the bounding box of the clothing area
        coords = np.column_stack(np.where(clothes_mask > 0))
        if coords.size > 0:
            y_min, x_min = coords.min(axis=0)
            y_max, x_max = coords.max(axis=0)

            # Calculate the size of the clothing area in the original image
            clothing_h, clothing_w = y_max - y_min, x_max - x_min

            # Resize the new clothes image to match the clothing area size
            resized_clothes = cv2.resize(clothes_array, (clothing_w, clothing_h), interpolation=cv2.INTER_CUBIC)

            # Create a canvas to place the resized clothes onto
            clothes_placement = np.zeros_like(original_array)

            # Place the resized clothes in the appropriate location
            if y_min + resized_clothes.shape[0] <= original_array.shape[0] and x_min + resized_clothes.shape[1] <= original_array.shape[1]:
                clothes_placement[y_min:y_min + resized_clothes.shape[0], x_min:x_min + resized_clothes.shape[1]] = resized_clothes

            # Create a more refined mask for blending - use the clothing mask as-is
            mask_3channel = np.stack([clothes_mask] * 3, axis=-1).astype(np.float32) / 255.0

            # Blend the original image with the new clothes using the mask
            result = original_array.copy()

            # For better blending, only replace pixels where the mask is white (clothing areas)
            result = original_array * (1 - mask_3channel) + clothes_placement * mask_3channel
            result = result.astype(np.uint8)
        else:
            # If no clothing area detected, just return original image
            result = original_array

        # Convert back to PIL Image
        result_img = Image.fromarray(result)

        # Add watermark with anonymous identifier for public endpoint
        watermarked_img = add_watermark(result_img, "anonymous_user")

        # Save to bytes
        output_bytes = io.BytesIO()
        watermarked_img.save(output_bytes, format="PNG")
        output_bytes.seek(0)

        return StreamingResponse(
            output_bytes,
            media_type="image/png",
            headers={"Content-Disposition": "attachment; filename=clothes_replaced.png"}
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing images: {str(e)}")


@app.post("/api/public-change-background")
async def change_background(
    file: UploadFile = File(...),
    bg_color: Optional[str] = Form(None),
    quality: Optional[str] = Form("high")
):
    """
    Change background color in an image.
    First removes the background, then applies a new background color.

    Args:
        file: Image file (PNG, JPG, etc.)
        bg_color: Background color in hex format (default: "FFFFFF" for white)

    Returns:
        Image with new background color
    """
    try:
        # Read the uploaded file
        contents = await file.read()

        # Validate file type by checking file signature
        if not contents[:4] in [b'\x89PNG', b'\xFF\xD8\xFF', b'GIF8', b'\x49\x49\x2A\x00', b'\x4D\x4D\x00\x2A', b'\x00\x00\x00\x0C']:
            # Not perfect but checks for common image formats: PNG, JPEG, GIF, TIFF, etc.
            # Use file extension as backup check as well
            file_ext = os.path.splitext(file.filename)[1].lower()
            allowed_exts = ['.png', '.jpg', '.jpeg', '.gif', '.bmp', '.tiff', '.webp']
            if file_ext not in allowed_exts:
                raise HTTPException(status_code=400, detail="Invalid file type. Only image files are allowed")

        # Validate file size
        if len(contents) > 10 * 1024 * 1024:
            raise HTTPException(status_code=400, detail="File size exceeds 10MB limit")

        # Try to open image with PIL to validate it's a valid image file
        try:
            img = Image.open(io.BytesIO(contents))
            img.verify()  # Verify that it's a valid image
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid or corrupted image file")

        # Reopen image after verification
        img = Image.open(io.BytesIO(contents))

        # Parse background color
        bg_hex = bg_color if bg_color else "FFFFFF"
        if len(bg_hex) != 6:
            raise HTTPException(status_code=400, detail="bg_color must be 6-character hex value")

        try:
            bg_rgb = tuple(int(bg_hex[i:i+2], 16) for i in (0, 2, 4))
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid hex color format")

        # Remove background first
        removed_bg = remove(contents, session=session)

        # Open the image with transparent background
        img_with_transparency = Image.open(io.BytesIO(removed_bg)).convert("RGBA")

        # Create new background image with specified color
        # Use alpha compositing for proper blending
        bg_rgba = Image.new("RGBA", img_with_transparency.size, bg_rgb + (255,))  # Add alpha of 255 (opaque)

        # Composite the transparent image onto the colored background
        composited = Image.alpha_composite(bg_rgba, img_with_transparency)

        # Convert back to RGB
        result_img = composited.convert("RGB")

        # Add watermark with anonymous identifier for public endpoint
        watermarked_img = add_watermark(result_img, "anonymous_user")

        # Save to bytes
        output_bytes = io.BytesIO()
        watermarked_img.save(output_bytes, format="PNG")
        output_bytes.seek(0)

        return StreamingResponse(
            output_bytes,
            media_type="image/png",
            headers={"Content-Disposition": "attachment; filename=bg_changed.png"}
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing image: {str(e)}")


def find_clothing_region(image):
    """
    Find the clothing region in an image using advanced computer vision techniques.
    This function detects clothing areas by identifying human body regions and excluding skin.
    """
    # Convert PIL image to OpenCV format
    cv_image = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)

    # Create a mask for the entire person using background removal technique
    # First convert back to PIL for rembg processing
    pil_img = Image.fromarray(cv2.cvtColor(cv_image, cv2.COLOR_BGR2RGB))
    img_byte_arr = io.BytesIO()
    pil_img.save(img_byte_arr, format='PNG')
    img_byte_arr.seek(0)

    # Use rembg to get person silhouette (this gives us the person outline)
    person_silhouette_bytes = remove(img_byte_arr.getvalue(), session=session)
    person_silhouette_pil = Image.open(io.BytesIO(person_silhouette_bytes)).convert("L")
    person_silhouette = np.array(person_silhouette_pil)

    # Threshold to get binary mask
    _, person_mask = cv2.threshold(person_silhouette, 127, 255, cv2.THRESH_BINARY)

    # Convert original image to HSV for better color-based segmentation
    hsv = cv2.cvtColor(cv_image, cv2.COLOR_BGR2HSV)

    # Create a more sophisticated skin detection using multiple ranges
    # These ranges handle different skin tones
    skin_ranges = [
        # Standard skin range
        (np.array([0, 20, 70], dtype=np.uint8), np.array([20, 255, 255], dtype=np.uint8)),
        # Alternative skin range
        (np.array([0, 30, 60], dtype=np.uint8), np.array([25, 170, 250], dtype=np.uint8)),
        # For lighter/darker skin tones
        (np.array([0, 10, 10], dtype=np.uint8), np.array([30, 100, 150], dtype=np.uint8)),
    ]

    skin_mask = np.zeros(hsv.shape[:2], dtype=np.uint8)
    for lower, upper in skin_ranges:
        single_mask = cv2.inRange(hsv, lower, upper)
        skin_mask = cv2.bitwise_or(skin_mask, single_mask)

    # Apply morphological operations to clean up skin mask
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (15, 15))
    skin_mask = cv2.morphologyEx(skin_mask, cv2.MORPH_CLOSE, kernel)
    skin_mask = cv2.morphologyEx(skin_mask, cv2.MORPH_OPEN, kernel)

    # Refine person mask by combining with skin detection
    refined_person_mask = cv2.bitwise_and(person_mask, person_mask, mask=skin_mask)

    # Invert the skin mask to find non-skin areas within person silhouette
    possible_clothing = cv2.bitwise_and(person_mask, cv2.bitwise_not(skin_mask))

    # Apply morphological operations to clean up the possible clothing mask
    kernel_clothing = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (12, 12))
    clothing_mask = cv2.morphologyEx(possible_clothing, cv2.MORPH_CLOSE, kernel_clothing)
    clothing_mask = cv2.morphologyEx(clothing_mask, cv2.MORPH_OPEN, kernel_clothing)

    # Additional refinement: focus on torso area and filter small regions
    h, w = clothing_mask.shape

    # Create a region of interest that excludes head and hands (just torso/upper body)
    roi_mask = np.zeros_like(clothing_mask)
    roi_y_start = int(h * 0.2)
    roi_y_end = int(h * 0.75)
    roi_mask[roi_y_start:roi_y_end, :] = 255

    # Apply ROI to focus on torso area
    clothing_mask = cv2.bitwise_and(clothing_mask, roi_mask)

    # Find contours to isolate individual clothing items
    contours, _ = cv2.findContours(clothing_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    # Filter contours based on area and position
    filtered_contours = []
    min_area = max(500, (w * h) * 0.01)  # Minimum area based on image size

    for contour in contours:
        area = cv2.contourArea(contour)
        if area > min_area:  # Only include reasonably sized clothing regions
            filtered_contours.append(contour)

    # Create final mask with filtered contours
    final_clothing_mask = np.zeros_like(clothing_mask)
    if filtered_contours:
        cv2.drawContours(final_clothing_mask, filtered_contours, -1, (255), thickness=cv2.FILLED)

    # Apply additional smoothing and refinement
    final_clothing_mask = cv2.GaussianBlur(final_clothing_mask, (5, 5), 0)
    _, final_clothing_mask = cv2.threshold(final_clothing_mask, 127, 255, cv2.THRESH_BINARY)

    return final_clothing_mask


def detect_garment_type_from_text(text: str) -> str:
    """
    Detect garment type from user-provided text by mapping clothing names to categories
    """
    text = text.lower().strip()

    # Top clothing items
    top_items = {
        'shirt', 't-shirt', 'tshirt', 'blouse', 'top', 'tank', 'tank top', 'tanktop',
        'sweater', 'hoodie', 'jacket', 'coat', 'vest', 'polo', 'button', 'button-down',
        'dress shirt', 'casual shirt', 'formal shirt', 'crop top', 'sleeveless', 'cardigan'
    }

    # Bottom clothing items
    bottom_items = {
        'pant', 'pants', 'trousers', 'jeans', 'short', 'shorts', 'skirt', 'skorts',
        'legging', 'leggings', 'chino', 'cargo', 'sweatpants', 'jogger', 'joggers',
        'capri', 'capris', 'culotte', 'culottes', 'palazzo', 'palazzos'
    }

    # Full body clothing items
    full_items = {
        'dress', 'overall', 'overalls', 'jumpsuit', 'romper', 'suit', 'gown', 'robe',
        'onesie', 'bodysuit', 'full dress', 'long dress', 'maxi dress', 'midi dress'
    }

    # Check if text contains any full items
    for item in full_items:
        if item in text:
            return 'full'

    # Check if text contains any bottom items
    for item in bottom_items:
        if item in text:
            return 'bottom'

    # Check if text contains any top items
    for item in top_items:
        if item in text:
            return 'top'

    # Default to 'top' if no specific match found, since tops are most common
    return 'top'




def get_specific_garment_mask(image: Image.Image, garment_type: str) -> np.ndarray:
    """
    Get a specific garment mask based on the requested garment type
    Updated to use high-accuracy segmentation prompt
    """
    # Get enhanced segmentation masks using the high-accuracy prompt
    parsing_masks = create_high_accuracy_segmentation_prompt(image, garment_type)

    # Map garment_type to the appropriate mask
    if garment_type == 'top':
        # For tops, combine upper clothing items from parsing results
        mask = None
        # Check for masks from enhanced parsing
        for key in parsing_masks.keys():
            if any(keyword in key.lower() for keyword in ['shirt', 'top', 'upper', 'blouse', 't-shirt', 'sweater', 'jacket', 'coat', 'shirt_top']):
                if mask is None:
                    mask = parsing_masks[key].copy()
                else:
                    mask = np.maximum(mask, parsing_masks[key])

        # If no specific top-related mask found, fall back to 'upper' from parsing
        if mask is None and 'upper' in parsing_masks:
            mask = parsing_masks['upper']
        elif mask is None and 'top' in parsing_masks:
            mask = parsing_masks['top']

        # If still no mask, try to create one based on position (upper body)
        if mask is None:
            h, w = image.height, image.width
            mask = np.zeros((h, w), dtype=np.uint8)
            # Default for top: upper 60% of person area (if pose keypoints are available)
            # This would be refined if we have pose information

        return mask if mask is not None else np.zeros((image.height, image.width), dtype=np.uint8)

    elif garment_type == 'bottom':
        # For bottoms, combine lower clothing items
        mask = None
        for key in parsing_masks.keys():
            if any(keyword in key.lower() for keyword in ['pants', 'bottom', 'lower', 'skirt', 'shorts', 'trousers', 'skirt', 'jumpsuit']):
                if mask is None:
                    mask = parsing_masks[key].copy()
                else:
                    mask = np.maximum(mask, parsing_masks[key])

        # If no specific bottom-related mask found, fall back to 'lower' from parsing
        if mask is None and 'lower' in parsing_masks:
            mask = parsing_masks['lower']
        elif mask is None and 'bottom' in parsing_masks:
            mask = parsing_masks['bottom']

        # If still no mask, try to create one based on position (lower body)
        if mask is None:
            h, w = image.height, image.width
            mask = np.zeros((h, w), dtype=np.uint8)
            # Default for bottom: lower 60% of person area

        return mask if mask is not None else np.zeros((image.height, image.width), dtype=np.uint8)

    elif garment_type == 'full':
        # For full-body garments, combine upper and lower
        mask = None
        for key in parsing_masks.keys():
            if any(keyword in key.lower() for keyword in ['dress', 'full', 'overall', 'jumpsuit', 'gown']):
                if mask is None:
                    mask = parsing_masks[key].copy()
                else:
                    mask = np.maximum(mask, parsing_masks[key])

        # If no specific full garment found, combine upper and lower
        if mask is None and 'full' in parsing_masks:
            mask = parsing_masks['full']
        elif mask is None:
            upper_mask = parsing_masks.get('upper', None) or parsing_masks.get('dress', None) or parsing_masks.get('jumpsuit', None)
            lower_mask = parsing_masks.get('lower', None) or parsing_masks.get('dress', None) or parsing_masks.get('jumpsuit', None)
            if upper_mask is not None and lower_mask is not None:
                mask = np.maximum(upper_mask, lower_mask)
            elif upper_mask is not None:
                mask = upper_mask
            elif lower_mask is not None:
                mask = lower_mask

        return mask if mask is not None else np.zeros((image.height, image.width), dtype=np.uint8)

    else:
        # For specific garment names, try to find the most appropriate match
        mask = None
        for key in parsing_masks.keys():
            if garment_type.lower() in key.lower():
                mask = parsing_masks[key]
                break

        # If no exact match, try partial matches
        if mask is None:
            for key in parsing_masks.keys():
                if garment_type.lower() in key.lower() or any(garment_type.lower() in k.lower() for k in key.split('_')):
                    mask = parsing_masks[key]
                    break

        # Also check for exact garment name matches in our predefined categories
        if mask is None:
            if garment_type.lower() in ['shirt', 't-shirt', 'blouse']:
                mask = parsing_masks.get('shirt_top', None)
            elif garment_type.lower() in ['coat', 'jacket']:
                mask = parsing_masks.get('coat', None)
            elif garment_type.lower() in ['pants', 'trousers']:
                mask = parsing_masks.get('pants', None)
            elif garment_type.lower() in ['skirt']:
                mask = parsing_masks.get('skirt', None)
            elif garment_type.lower() in ['dress']:
                mask = parsing_masks.get('dress', None)
            elif garment_type.lower() in ['jumpsuit', 'overall']:
                mask = parsing_masks.get('jumpsuit', None)

        return mask if mask is not None else np.zeros((image.height, image.width), dtype=np.uint8)


def get_improved_garment_segmentation(image: Image.Image, garment_type: str) -> dict:
    """
    Enhanced garment segmentation using human parsing model:
    1. Human parsing model
    2. Morphological operations for refinement
    """
    # Get initial masks from human parsing model
    parsing_model = load_pretrained_model()
    parsing_map = get_parsing_map(parsing_model, image)

    # Use the new high-accuracy segmentation function
    parsing_masks = get_high_accuracy_garment_masks(parsing_map, garment_type)

    # Apply morphological operations to refine the masks
    for garment, mask in parsing_masks.items():
        if mask is not None and mask.size > 0:
            # Apply morphological closing to remove small holes
            kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))  # Slightly larger kernel
            mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)

            # Apply morphological opening to remove small noise
            kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
            mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)

            # Apply Gaussian smoothing for boundary refinement
            mask = cv2.GaussianBlur(mask, (5, 5), 0)

            # Threshold to create binary mask (0 or 1)
            mask = (mask > 127).astype(np.uint8)

            parsing_masks[garment] = mask

    return parsing_masks


def create_high_accuracy_segmentation_prompt(image: Image.Image, garment_type: str) -> dict:
    """
    Create high-accuracy segmentation masks for the specified garment type
    Following all requirements: pixel-perfect, multi-garment separation, mask refinement, etc.

    Returns:
        Dictionary containing binary masks for each garment type
    """
    # Load the parsing model
    parsing_model = load_pretrained_model()

    # Get the parsing map
    parsing_map = get_parsing_map(parsing_model, image)

    # Get high accuracy garment masks based on the specified garment type
    masks = get_high_accuracy_garment_masks(parsing_map, garment_type)

    # Apply additional refinement operations to meet all requirements
    for garment_name, mask in masks.items():
        if mask is not None and mask.size > 0:
            # Requirements implementation:
            # 1. Pixel-Perfect Segmentation - achieved through contour-based refinement
            # 2. Multi-Garment Separation - each garment has its own mask
            # 3. Mask Refinement - apply morphological operations

            # Apply morphological closing to remove holes (requirement 3)
            kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (15, 15))
            mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)

            # Apply morphological opening to remove noise
            kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (10, 10))
            mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)

            # Smooth boundary using contour-based refinement (requirement 3)
            contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

            if contours:
                # Create a clean mask with refined contours
                refined_mask = np.zeros_like(mask)
                # Draw the largest contour to ensure clean garment shape
                largest_contour = max(contours, key=cv2.contourArea)
                cv2.drawContours(refined_mask, [largest_contour], -1, 1, thickness=cv2.FILLED)

                # Apply Gaussian blur for smooth edges
                refined_mask = cv2.GaussianBlur(refined_mask, (5, 5), 0)
                refined_mask = (refined_mask > 0.5).astype(np.uint8)

                masks[garment_name] = refined_mask
            else:
                # If no contours found, use the original mask after refinement
                mask = cv2.GaussianBlur(mask, (5, 5), 0)
                mask = (mask > 0.5).astype(np.uint8)
                masks[garment_name] = mask

    return masks


def advanced_garment_mask_refinement(mask, image, iterations=2):
    """
    Apply advanced refinement to garment masks using image features
    """
    for _ in range(iterations):
        # Convert image to grayscale for gradient computation
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
        else:
            gray = image

        # Compute gradients to detect edges
        grad_x = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
        grad_y = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=3)
        gradient_magnitude = np.sqrt(grad_x**2 + grad_y**2)

        # Normalize gradient magnitude
        grad_normalized = gradient_magnitude / (gradient_magnitude.max() + 1e-8)

        # Create distance transform from mask
        mask_uint8 = (mask * 255).astype(np.uint8)
        dist_transform = cv2.distanceTransform(255 - mask_uint8, cv2.DIST_L2, 3)
        dist_transform = dist_transform / (dist_transform.max() + 1e-8)

        # Refine mask based on gradient information and distance
        # Preserve mask in high-gradient (edge) areas, but adjust based on distance from current mask
        adjustment_factor = 0.3
        refined_mask = mask + adjustment_factor * grad_normalized * (1 - dist_transform)
        refined_mask = np.clip(refined_mask, 0, 1)

        # Apply morphological operations to clean up the mask
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
        refined_mask_uint8 = (refined_mask * 255).astype(np.uint8)
        refined_mask_uint8 = cv2.morphologyEx(refined_mask_uint8, cv2.MORPH_CLOSE, kernel)
        refined_mask_uint8 = cv2.morphologyEx(refined_mask_uint8, cv2.MORPH_OPEN, kernel)

        refined_mask = refined_mask_uint8.astype(np.float32) / 255.0

        mask = refined_mask

    return mask


def get_parsing_map_with_enhancement(parsing_model, image):
    """
    Get parsing map with potential enhancement
    """
    # Use the standard parsing map function
    return get_parsing_map(parsing_model, image)


def get_enhanced_garment_masks(parsing_map, garment_type):
    """
    Get enhanced garment masks based on parsing map
    """
    # Use the high accuracy garment masks function
    return get_high_accuracy_garment_masks(parsing_map, garment_type)


@app.post("/api/replace-clothes")
async def replace_clothes(
    original_image: UploadFile = File(..., description="Original image with person wearing clothes to be replaced"),
    new_clothes_image: UploadFile = File(..., description="New clothes image to replace with"),
    garment_type: str = Form("top", description="Type of garment: top, bottom, full, or provide clothing name like 'shirt', 'pants', 'dress'"),
    options: str = Form('{}', description="JSON options like {\"preserve_logo\":true,\"resolution\":1024}"),
    return_debug: bool = Form(False, description="Return debug images for visualization"),
    enable_manual_correction: bool = Form(False, description="Enable manual mask correction capability"),
    return_cropped: bool = Form(False, description="Return cropped version of just the replaced garment"),
    current_user: UserInDB = Depends(get_current_user)
):
    """
    Enhanced clothes replacement with improved segmentation, blending, and validation.

    Processing flow:
    1. Enhanced garment segmentation with validation
    2. Human detection & parsing
    3. Pose estimation
    4. Cloth alignment (warping)
    5. Advanced composition & blending
    6. Quality validation and enhancement
    7. Refinement and post-processing

    Args:
        original_image: Original image with person wearing clothes to be replaced (PNG, JPG, etc.)
        new_clothes_image: New clothes image to replace with (PNG, JPG, etc.)
        garment_type: Type of garment ('top', 'bottom', 'full') or specific clothing name like 'shirt', 'pants', 'dress' - defaults to 'top'
        options: JSON string with options like {"preserve_logo": true, "resolution": 1024}
        return_debug: Whether to return debug images for visualization
        enable_manual_correction: Enable manual mask correction capability

    Returns:
        JSON with result_image and optionally debug images (debug_masks, warp_preview, composition_mask)
    """
    try:
        # Parse options
        try:
            options_dict = json.loads(options) if options else {}
        except json.JSONDecodeError:
            options_dict = {}

        preserve_logo = options_dict.get('preserve_logo', False)
        resolution = options_dict.get('resolution', 1024)
        manual_correction = options_dict.get('manual_correction', False)

        # Auto-detect garment type from the provided text if not one of standard types
        if garment_type not in ['top', 'bottom', 'full']:
            detected_type = detect_garment_type_from_text(garment_type)
            print(f"Auto-detected garment type: '{garment_type}' -> '{detected_type}'")
            garment_type = detected_type
        else:
            print(f"Using provided garment type: {garment_type}")

        # Read both uploaded files
        original_contents = await original_image.read()
        new_clothes_contents = await new_clothes_image.read()

        # Validate file sizes (max 10MB each)
        if len(original_contents) > 10 * 1024 * 1024:
            raise HTTPException(status_code=400, detail="Original image file size exceeds 10MB limit")

        if len(new_clothes_contents) > 10 * 1024 * 1024:
            raise HTTPException(status_code=400, detail="New clothes image file size exceeds 10MB limit")

        # Open images
        original_img = Image.open(io.BytesIO(original_contents)).convert("RGB")
        clothes_img = Image.open(io.BytesIO(new_clothes_contents)).convert("RGB")

        # Store original dimensions for later use
        orig_width, orig_height = original_img.size
        orig_aspect_ratio = orig_width / orig_height

        # Determine the processing resolution - either original or limited by max resolution
        if max(orig_width, orig_height) > resolution:
            if orig_width > orig_height:
                proc_width = resolution
                proc_height = int(resolution / orig_aspect_ratio)
            else:
                proc_height = resolution
                proc_width = int(resolution * orig_aspect_ratio)
        else:
            proc_width, proc_height = orig_width, orig_height

        # Resize both images to the same processing dimensions to avoid shape mismatch
        original_img = original_img.resize((proc_width, proc_height), Image.Resampling.LANCZOS)
        clothes_img = clothes_img.resize((proc_width, proc_height), Image.Resampling.LANCZOS)

        # Ensure both images have exactly the same dimensions after resizing
        if original_img.size != clothes_img.size:
            # If there's still a slight difference due to rounding, fix it
            clothes_img = clothes_img.resize(original_img.size, Image.Resampling.LANCZOS)

        # STEP 1: Pose estimation (needed for fallback masks)
        keypoints = estimate_pose_from_image(original_img)
        print(f"Generated {len(keypoints)} keypoints for pose estimation")

        # STEP 2: Enhanced human parsing and garment segmentation
        print("Starting enhanced garment segmentation...")
        parsing_model = load_pretrained_model()
        enhanced_masks = enhanced_garment_segmentation(original_img, garment_type, parsing_model)

        # Validate mask accuracy
        mask_key = list(enhanced_masks.keys())[0]  # Get the first available mask
        current_mask = enhanced_masks[mask_key]
        is_valid_mask, mask_validation_msg = validate_mask_accuracy(original_img, current_mask, garment_type)
        print(f"Mask validation: {mask_validation_msg}")

        # If mask validation fails (low coverage or other issues), create a pose-based fallback mask
        if not is_valid_mask:
            mask_coverage = np.mean(current_mask)

            # If completely no coverage or very low coverage (< 0.5%), use pose-based fallback
            if mask_coverage < 0.005:  # < 0.5% coverage
                print("Segmentation failed or has very low coverage. Creating pose-based fallback mask...")
                # Generate a fallback mask based on pose estimation
                if garment_type == 'top':
                    fallback_mask = create_torso_mask(original_img, keypoints)
                elif garment_type == 'bottom':
                    fallback_mask = create_lower_body_mask(original_img, keypoints)
                elif garment_type == 'full':
                    # Combine upper and lower torso
                    upper_mask = refine_shirt_mask_with_parsing(parsing_model, original_img, keypoints, "top")
                    lower_mask = create_lower_body_mask(original_img, keypoints)
                    fallback_mask = np.maximum(upper_mask, lower_mask)
                else:  # Default to top
                    fallback_mask = refine_shirt_mask_with_parsing(parsing_model, original_img, keypoints, "top")

                # Apply refinement to the fallback mask
                fallback_mask = refine_mask_boundaries(fallback_mask, np.array(original_img))
                enhanced_masks[mask_key] = fallback_mask
                current_mask = fallback_mask
                # Re-validate the fallback mask
                is_valid_mask, mask_validation_msg = validate_mask_accuracy(original_img, current_mask, garment_type)
                print(f"Fallback mask validation: {mask_validation_msg}")

            # If validation still fails after initial check, but we have some mask coverage,
            # consider using pose-based mask as an alternative if it's better than current
            elif mask_coverage < 0.05 and not is_valid_mask:  # Less than 5% coverage and still not valid
                print("Low coverage mask detected. Creating pose-based mask as alternative...")
                # Create pose-based mask to compare
                if garment_type == 'top':
                    pose_based_mask = refine_shirt_mask_with_parsing(parsing_model, original_img, keypoints, "top")
                elif garment_type == 'bottom':
                    pose_based_mask = create_lower_body_mask(original_img, keypoints)
                elif garment_type == 'full':
                    upper_mask = refine_shirt_mask_with_parsing(parsing_model, original_img, keypoints, "top")
                    lower_mask = create_lower_body_mask(original_img, keypoints)
                    pose_based_mask = np.maximum(upper_mask, lower_mask)
                else:  # Default to top
                    pose_based_mask = refine_shirt_mask_with_parsing(parsing_model, original_img, keypoints, "top")

                # Check the pose-based mask coverage
                pose_mask_coverage = np.mean(pose_based_mask)
                if pose_mask_coverage > mask_coverage:  # If pose-based mask covers more area
                    print(f"Pose-based mask has better coverage ({pose_mask_coverage:.2%} vs {mask_coverage:.2%}), using it instead...")
                    pose_based_mask = refine_mask_boundaries(pose_based_mask, np.array(original_img))
                    enhanced_masks[mask_key] = pose_based_mask
                    current_mask = pose_based_mask
                    # Re-validate the pose-based mask
                    is_valid_mask, mask_validation_msg = validate_mask_accuracy(original_img, current_mask, garment_type)
                    print(f"Pose-based mask validation: {mask_validation_msg}")

            elif not is_valid_mask and enable_manual_correction:
                print("Applying manual mask correction...")
                corrected_mask = manual_mask_correction(original_img, current_mask)
                enhanced_masks[mask_key] = corrected_mask

        # Refine mask boundaries using image features
        refined_mask = refine_mask_boundaries(current_mask, np.array(original_img))
        enhanced_masks[mask_key] = refined_mask

        # STEP 3: Cloth alignment (warping)
        # Ensure images have the same size before warping
        if original_img.size != clothes_img.size:
            clothes_img = clothes_img.resize(original_img.size, Image.Resampling.LANCZOS)

        # Create a mask for the new clothes image to extract only the clothes part and remove background
        # This will prevent the black background of the new clothes from being warped and blended
        print("Creating mask for new clothes image to remove background...")

        # First, try to use the existing function
        try:
            new_clothes_mask = create_cloth_mask_from_image(clothes_img)
        except:
            # If the function fails, create a basic mask to detect non-black pixels
            print("Falling back to basic black background detection...")
            clothes_array = np.array(clothes_img)
            # Detect pixels that are not pure black (0,0,0)
            if len(clothes_array.shape) == 3:
                # For RGB images, check if all channels are not all zero
                gray_check = np.mean(clothes_array, axis=2)
                new_clothes_mask = (gray_check > 20).astype(np.uint8)  # Threshold to detect non-black pixels
                # Apply morphological operations to clean up the mask
                kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
                new_clothes_mask = cv2.morphologyEx(new_clothes_mask, cv2.MORPH_CLOSE, kernel)
                new_clothes_mask = cv2.morphologyEx(new_clothes_mask, cv2.MORPH_OPEN, kernel)
            else:
                new_clothes_mask = (clothes_array > 20).astype(np.uint8)

        # Apply the mask to the new clothes image to remove its background
        clothes_array = np.array(clothes_img)
        if len(new_clothes_mask.shape) == 2:
            new_clothes_mask_3ch = np.stack([new_clothes_mask] * 3, axis=-1)
        else:
            new_clothes_mask_3ch = new_clothes_mask

        # Apply the mask to remove the background of the new clothes
        # Keep clothes where mask is 1, and set background to white (or original image's background)
        masked_clothes = (clothes_array * new_clothes_mask_3ch +
                         (1 - new_clothes_mask_3ch) * np.array([255, 255, 255])).astype(np.uint8)  # White background
        masked_clothes_img = Image.fromarray(masked_clothes, 'RGB')

        # Improve size fitting: Before warping, estimate the target garment size from the segmentation mask
        # and resize the new clothes to approximately match those dimensions for better initial scaling
        print("Analyzing target garment area for size fitting...")
        # Get the mask for the current garment type to understand target size
        if mask_key in enhanced_masks:
            target_mask = enhanced_masks[mask_key]
            # Find bounding box of the target garment area
            coords = np.where(target_mask > 0.1)
            if len(coords[0]) > 0 and len(coords[1]) > 0:
                y_min, y_max = coords[0].min(), coords[0].max()
                x_min, x_max = coords[1].min(), coords[1].max()

                # Calculate target dimensions
                target_height = y_max - y_min
                target_width = x_max - x_min

                # Get current dimensions of the masked clothes
                current_height, current_width = masked_clothes_img.height, masked_clothes_img.width

                # Calculate a scaling factor to better match target dimensions
                # Preserve aspect ratio while fitting within the target area with some margin
                scale_h = target_height / current_height * 0.8  # 80% to allow for fitting
                scale_w = target_width / current_width * 0.8

                # Use the smaller scale to ensure the clothes fit within the target area
                scale_factor = min(scale_h, scale_w, 1.0)  # Don't upscale beyond 1.0

                if scale_factor < 1.0:  # Only resize if scaling down
                    new_size = (int(current_width * scale_factor), int(current_height * scale_factor))
                    masked_clothes_img = masked_clothes_img.resize(new_size, Image.Resampling.LANCZOS)

                    # Also resize the mask to match
                    new_clothes_mask_resized = cv2.resize(new_clothes_mask, new_size, interpolation=cv2.INTER_NEAREST)

                    # Reapply the mask after resizing to ensure no background pixels are introduced
                    resized_clothes_array = np.array(masked_clothes_img)
                    if len(new_clothes_mask_resized.shape) == 2:
                        resized_mask_3ch = np.stack([new_clothes_mask_resized] * 3, axis=-1)
                    else:
                        resized_mask_3ch = new_clothes_mask_resized

                    # Apply the resized mask to make sure background is still clean
                    masked_and_resized = (resized_clothes_array * resized_mask_3ch +
                                         (1 - resized_mask_3ch) * np.array([255, 255, 255])).astype(np.uint8)
                    masked_clothes_img = Image.fromarray(masked_and_resized, 'RGB')

        print("Warping cloth to fit person's pose...")
        # Warp the masked clothes image (with background removed) to fit the person's pose
        warped_cloth, tps_transformer = warp_cloth_tps(
            masked_clothes_img,  # Use the masked version without background
            original_img,
            keypoints,
            keypoints_cloth=None  # Will be generated internally
        )

        # STEP 4: Create enhanced composition mask
        print("Creating enhanced composition mask...")
        composition_mask = create_enhanced_composition_mask(
            original_img,
            enhanced_masks,
            keypoints,
            garment_type,
            mask_refinement=True
        )

        # STEP 5: Enhanced composition and blending
        print("Performing enhanced blending...")
        # Use enhanced blending function
        result_img = enhanced_blend_images(
            original_img,
            warped_cloth,
            composition_mask,
            garment_type
        )

        # Safety check: Ensure original image is preserved outside garment area
        # This ensures that even if enhanced_blend_images doesn't perfectly respect the mask,
        # we explicitly preserve the original image outside the garment area
        original_array = np.array(original_img)
        result_array = np.array(result_img)

        # Ensure composition mask is in the right format
        if len(composition_mask.shape) == 3:
            garment_mask_2d = composition_mask[:, :, 0]  # Take first channel
        else:
            garment_mask_2d = composition_mask

        # Expand mask to 3 channels for RGB
        if len(garment_mask_2d.shape) == 2:
            mask_3ch = np.stack([garment_mask_2d] * 3, axis=-1)
        else:
            mask_3ch = garment_mask_2d

        # Ensure mask values are between 0 and 1
        mask_3ch = np.clip(mask_3ch, 0, 1)

        # Preserve original image outside the mask, and use result inside the mask
        final_array = original_array * (1 - mask_3ch) + result_array * mask_3ch
        result_img = Image.fromarray(final_array.astype(np.uint8), 'RGB')

        # Improve size fitting: Adjust the garment area to better match original dimensions
        # Find the bounding box of the garment mask to understand the target area
        coords = np.where(garment_mask_2d > 0.1)  # Use threshold to find garment pixels
        if len(coords[0]) > 0 and len(coords[1]) > 0:  # If garment mask has content
            y_min, y_max = coords[0].min(), coords[0].max()
            x_min, x_max = coords[1].min(), coords[1].max()

            # Calculate the size of the target garment area
            target_h, target_w = y_max - y_min, x_max - x_min

            # The warped garment should already have similar proportions to the target,
            # but we can enhance the blending to make sure it fits well within the boundaries
            # Create a refined mask with soft edges for smoother blending
            refined_mask = cv2.GaussianBlur(garment_mask_2d, (15, 15), 0)  # Smooth edges
            refined_mask_3ch = np.stack([refined_mask] * 3, axis=-1) if len(refined_mask.shape) == 2 else refined_mask
            refined_mask_3ch = np.clip(refined_mask_3ch, 0, 1)

            # Apply the refined mask to ensure smooth integration
            final_array = original_array * (1 - refined_mask_3ch) + result_array * refined_mask_3ch
            result_img = Image.fromarray(final_array.astype(np.uint8), 'RGB')

        # STEP 6: Validate clothes replacement effectiveness
        print("Validating clothes replacement effectiveness...")
        replacement_quality = detect_replacement_quality(
            original_img,
            result_img,
            composition_mask[:, :, 0] if len(composition_mask.shape) == 3 else composition_mask
        )

        print(f"Replacement quality: {replacement_quality['quality']} (confidence: {replacement_quality['confidence']:.2f})")

        # If replacement quality is low, use more aggressive approach
        if not replacement_quality['is_successful']:
            print("Clothes replacement quality is low. Using more aggressive approach...")

            # Even more aggressive: use the original new clothes image directly from the byte stream
            # to ensure we have a completely unprocessed version, with proper sizing
            original_array = np.array(original_img)
            result_array = np.array(result_img)

            # Use the original new clothes image directly from the uploaded content
            original_new_clothes_img = Image.open(io.BytesIO(new_clothes_contents)).convert("RGB")

            # Create a mask for the new clothes image to extract only the clothes part and remove background
            print("Creating mask for new clothes image to remove background (aggressive replacement)...")

            # Try to create a mask for the new clothes image
            try:
                original_clothes_mask = create_cloth_mask_from_image(original_new_clothes_img)
            except:
                # If the function fails, create a basic mask to detect non-black pixels
                print("Falling back to basic black background detection (aggressive replacement)...")
                original_clothes_array = np.array(original_new_clothes_img)
                # Detect pixels that are not pure black (0,0,0)
                if len(original_clothes_array.shape) == 3:
                    # For RGB images, check if all channels are not all zero
                    gray_check = np.mean(original_clothes_array, axis=2)
                    original_clothes_mask = (gray_check > 20).astype(np.uint8)  # Threshold to detect non-black pixels
                    # Apply morphological operations to clean up the mask
                    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
                    original_clothes_mask = cv2.morphologyEx(original_clothes_mask, cv2.MORPH_CLOSE, kernel)
                    original_clothes_mask = cv2.morphologyEx(original_clothes_mask, cv2.MORPH_OPEN, kernel)
                else:
                    original_clothes_mask = (original_clothes_array > 20).astype(np.uint8)

            # Apply the mask to the new clothes image to remove its background
            original_clothes_array = np.array(original_new_clothes_img)
            if len(original_clothes_mask.shape) == 2:
                original_clothes_mask_3ch = np.stack([original_clothes_mask] * 3, axis=-1)
            else:
                original_clothes_mask_3ch = original_clothes_mask

            # Apply the mask to remove the background of the new clothes
            masked_original_clothes = (original_clothes_array * original_clothes_mask_3ch +
                                     (1 - original_clothes_mask_3ch) * np.array([255, 255, 255])).astype(np.uint8)  # White background
            masked_original_clothes_img = Image.fromarray(masked_original_clothes, 'RGB')

            # Improve size fitting: Resize based on target garment area while preserving aspect ratio
            # Calculate the bounding box of the garment mask to determine the proper size
            if len(composition_mask.shape) == 3:
                mask_2d = composition_mask[:, :, 0]
            else:
                mask_2d = composition_mask

            # Find the bounding box of the mask to determine the area for clothes
            coords = np.where(mask_2d > 0.1)
            if len(coords[0]) > 0 and len(coords[1]) > 0:  # If there are any masked pixels
                y_min, y_max = coords[0].min(), coords[0].max()
                x_min, x_max = coords[1].min(), coords[1].max()

                # Calculate the size of the garment area in the original image
                target_height = y_max - y_min
                target_width = x_max - x_min

                # Get current dimensions of the masked clothes
                current_height, current_width = masked_original_clothes_img.height, masked_original_clothes_img.width

                # Calculate a scaling factor to better match target dimensions
                # Preserve aspect ratio while fitting within the target area with some margin
                scale_h = target_height / current_height * 0.8  # 80% to allow for fitting
                scale_w = target_width / current_width * 0.8

                # Use the smaller scale to ensure the clothes fit within the target area
                scale_factor = min(scale_h, scale_w, 1.0)  # Don't upscale beyond 1.0

                if scale_factor < 1.0:  # Only resize if scaling down
                    new_size = (int(current_width * scale_factor), int(current_height * scale_factor))
                    masked_original_clothes_img = masked_original_clothes_img.resize(new_size, Image.Resampling.LANCZOS)

                # Resize to target dimensions with proper aspect ratio handling
                new_clothes_sized = masked_original_clothes_img.resize(
                    (target_width, target_height),
                    Image.Resampling.LANCZOS
                )

                # Create a canvas to place the sized clothes onto
                sized_clothes_array = np.zeros_like(original_array)

                # Place the sized clothes in the appropriate location
                if (y_min + target_height <= original_array.shape[0] and
                    x_min + target_width <= original_array.shape[1]):
                    sized_clothes_array[y_min:y_min + target_height, x_min:x_min + target_width] = np.array(new_clothes_sized)
                else:
                    # If out of bounds, use the original approach but properly positioned
                    cloth_array = np.array(new_clothes_sized)
                    end_y = min(y_min + target_height, original_array.shape[0])
                    end_x = min(x_min + target_width, original_array.shape[1])
                    actual_h, actual_w = end_y - y_min, end_x - x_min
                    sized_clothes_array[y_min:end_y, x_min:end_x] = cloth_array[:actual_h, :actual_w]

                # Use the composition mask to directly replace areas
                if len(composition_mask.shape) == 3:
                    mask_3ch = composition_mask
                else:
                    mask_3ch = np.stack([composition_mask] * 3, axis=-1)

                # Apply direct replacement in high-confidence mask areas with properly sized clothes
                mask_threshold = 0.1  # Very low threshold to ensure maximum replacement area
                direct_replacement = np.where(
                    mask_3ch > mask_threshold,
                    sized_clothes_array,  # Use properly sized new clothes
                    original_array
                ).astype(np.uint8)
            else:
                # Fallback: use the original approach if no mask area found
                # But first, apply the background mask to the original clothes image
                try:
                    original_clothes_mask = create_cloth_mask_from_image(original_new_clothes_img)
                except:
                    # If the function fails, create a basic mask to detect non-black pixels
                    print("Falling back to basic black background detection (fallback)...")
                    original_clothes_array = np.array(original_new_clothes_img)
                    # Detect pixels that are not pure black (0,0,0)
                    if len(original_clothes_array.shape) == 3:
                        # For RGB images, check if all channels are not all zero
                        gray_check = np.mean(original_clothes_array, axis=2)
                        original_clothes_mask = (gray_check > 20).astype(np.uint8)  # Threshold to detect non-black pixels
                        # Apply morphological operations to clean up the mask
                        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
                        original_clothes_mask = cv2.morphologyEx(original_clothes_mask, cv2.MORPH_CLOSE, kernel)
                        original_clothes_mask = cv2.morphologyEx(original_clothes_mask, cv2.MORPH_OPEN, kernel)
                    else:
                        original_clothes_mask = (original_clothes_array > 20).astype(np.uint8)

                # Apply the mask to the new clothes image to remove its background
                original_clothes_array = np.array(original_new_clothes_img)
                if len(original_clothes_mask.shape) == 2:
                    original_clothes_mask_3ch = np.stack([original_clothes_mask] * 3, axis=-1)
                else:
                    original_clothes_mask_3ch = original_clothes_mask

                # Apply the mask to remove the background of the new clothes
                masked_original_clothes = (original_clothes_array * original_clothes_mask_3ch +
                                         (1 - original_clothes_mask_3ch) * np.array([255, 255, 255])).astype(np.uint8)  # White background
                masked_original_clothes_img = Image.fromarray(masked_original_clothes, 'RGB')

                # Now resize the MASKED clothes
                new_clothes_resized = masked_original_clothes_img.resize(original_img.size, Image.Resampling.LANCZOS)
                new_clothes_array = np.array(new_clothes_resized)

                # Use the composition mask to directly replace areas
                if len(composition_mask.shape) == 3:
                    mask_3ch = composition_mask
                else:
                    mask_3ch = np.stack([composition_mask] * 3, axis=-1)

                # Apply direct replacement in high-confidence mask areas with maximum visibility
                mask_threshold = 0.1  # Very low threshold to ensure maximum replacement area
                direct_replacement = np.where(
                    mask_3ch > mask_threshold,
                    new_clothes_array,  # Use MASKED original new clothes
                    original_array
                ).astype(np.uint8)

            # For maximum impact, use 100% of the direct replacement instead of blending
            result_array = direct_replacement

            result_img = Image.fromarray(result_array, 'RGB')

            # Update the result_img to be used for all subsequent processing
            # This ensures that further processing steps use our replaced image
            final_img = result_img

            # Validate again after aggressive enhancement
            final_quality = detect_replacement_quality(
                original_img,
                result_img,
                composition_mask[:, :, 0] if len(composition_mask.shape) == 3 else composition_mask
            )
            print(f"Final replacement quality after aggressive enhancement: {final_quality['quality']} (confidence: {final_quality['confidence']:.2f})")
        else:
            print("Clothes replacement was effective based on comprehensive quality assessment.")

        # STEP 7: Refinement GAN
        print("Applying realism enhancement...")
        refined_img = enhance_realism(
            result_img,
            original_img,
            warped_cloth
        )

        # STEP 8: Post-processing
        print("Applying post-processing...")
        final_img = post_process_pipeline(
            refined_img,
            original_img,
            warped_cloth,
            enhanced_masks,  # Use enhanced masks instead of basic parsing masks
            composition_mask,
            garment_type
        )

        # Additional post-processing to ensure clothes are clearly visible
        original_array = np.array(original_img)
        final_array = np.array(final_img)

        # Check if the image is too similar to original, and enhance if needed
        similarity_check = detect_replacement_quality(original_img, final_img)
        if not similarity_check['is_successful']:
            print("Applying final enhancements for better visibility...")

            # Ultimate safeguard: if quality is still low after all processing,
            # do a final direct replacement with properly sized clothes
            original_new_clothes_img = Image.open(io.BytesIO(new_clothes_contents)).convert("RGB")

            # Create a mask for the new clothes image to extract only the clothes part and remove background
            print("Creating mask for new clothes image to remove background (final safeguard)...")

            # Try to create a mask for the new clothes image
            try:
                original_clothes_mask = create_cloth_mask_from_image(original_new_clothes_img)
            except:
                # If the function fails, create a basic mask to detect non-black pixels
                print("Falling back to basic black background detection (final safeguard)...")
                original_clothes_array = np.array(original_new_clothes_img)
                # Detect pixels that are not pure black (0,0,0)
                if len(original_clothes_array.shape) == 3:
                    # For RGB images, check if all channels are not all zero
                    gray_check = np.mean(original_clothes_array, axis=2)
                    original_clothes_mask = (gray_check > 20).astype(np.uint8)  # Threshold to detect non-black pixels
                    # Apply morphological operations to clean up the mask
                    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
                    original_clothes_mask = cv2.morphologyEx(original_clothes_mask, cv2.MORPH_CLOSE, kernel)
                    original_clothes_mask = cv2.morphologyEx(original_clothes_mask, cv2.MORPH_OPEN, kernel)
                else:
                    original_clothes_mask = (original_clothes_array > 20).astype(np.uint8)

            # Apply the mask to the new clothes image to remove its background
            original_clothes_array = np.array(original_new_clothes_img)
            if len(original_clothes_mask.shape) == 2:
                original_clothes_mask_3ch = np.stack([original_clothes_mask] * 3, axis=-1)
            else:
                original_clothes_mask_3ch = original_clothes_mask

            # Apply the mask to remove the background of the new clothes
            masked_original_clothes = (original_clothes_array * original_clothes_mask_3ch +
                                     (1 - original_clothes_mask_3ch) * np.array([255, 255, 255])).astype(np.uint8)  # White background
            masked_original_clothes_img = Image.fromarray(masked_original_clothes, 'RGB')

            # Improve size fitting: Resize based on target garment area while preserving aspect ratio
            # Calculate the bounding box of the garment mask to determine the proper size
            if len(composition_mask.shape) == 3:
                mask_2d = composition_mask[:, :, 0]
            else:
                mask_2d = composition_mask

            # Find the bounding box of the mask to determine the area for clothes
            coords = np.where(mask_2d > 0.1)
            if len(coords[0]) > 0 and len(coords[1]) > 0:  # If there are any masked pixels
                y_min, y_max = coords[0].min(), coords[0].max()
                x_min, x_max = coords[1].min(), coords[1].max()

                # Calculate the size of the garment area in the original image
                target_height = y_max - y_min
                target_width = x_max - x_min

                # Get current dimensions of the masked clothes
                current_height, current_width = masked_original_clothes_img.height, masked_original_clothes_img.width

                # Calculate a scaling factor to better match target dimensions
                # Preserve aspect ratio while fitting within the target area with some margin
                scale_h = target_height / current_height * 0.8  # 80% to allow for fitting
                scale_w = target_width / current_width * 0.8

                # Use the smaller scale to ensure the clothes fit within the target area
                scale_factor = min(scale_h, scale_w, 1.0)  # Don't upscale beyond 1.0

                if scale_factor < 1.0:  # Only resize if scaling down
                    new_size = (int(current_width * scale_factor), int(current_height * scale_factor))
                    masked_original_clothes_img = masked_original_clothes_img.resize(new_size, Image.Resampling.LANCZOS)

                # Resize to target dimensions with proper aspect ratio handling
                new_clothes_sized = masked_original_clothes_img.resize(
                    (target_width, target_height),
                    Image.Resampling.LANCZOS
                )

                # Create a canvas to place the sized clothes onto
                sized_clothes_array = np.zeros_like(original_array)

                # Place the sized clothes in the appropriate location
                if (y_min + target_height <= original_array.shape[0] and
                    x_min + target_width <= original_array.shape[1]):
                    sized_clothes_array[y_min:y_min + target_height, x_min:x_min + target_width] = np.array(new_clothes_sized)
                else:
                    # If out of bounds, use the original approach but properly positioned
                    cloth_array = np.array(new_clothes_sized)
                    end_y = min(y_min + target_height, original_array.shape[0])
                    end_x = min(x_min + target_width, original_array.shape[1])
                    actual_h, actual_w = end_y - y_min, end_x - x_min
                    sized_clothes_array[y_min:end_y, x_min:end_x] = cloth_array[:actual_h, :actual_w]

                # Use the composition mask to do final direct replacement with properly sized clothes
                if len(composition_mask.shape) == 3:
                    comp_mask_3ch = composition_mask
                else:
                    comp_mask_3ch = np.stack([composition_mask] * 3, axis=-1)

                # Final replacement - only replace in the mask area with properly sized clothes
                final_direct_replace = np.where(
                    comp_mask_3ch > 0.1,  # Very low threshold
                    sized_clothes_array,  # Properly sized new clothes
                    final_array           # Keep other parts as processed
                ).astype(np.uint8)

                final_img = Image.fromarray(final_direct_replace, 'RGB')
            else:
                # Fallback: use the original approach if no mask area found
                # But first, apply the background mask to the original clothes image
                try:
                    original_clothes_mask = create_cloth_mask_from_image(original_new_clothes_img)
                except:
                    # If the function fails, create a basic mask to detect non-black pixels
                    print("Falling back to basic black background detection (final safeguard fallback)...")
                    original_clothes_array = np.array(original_new_clothes_img)
                    # Detect pixels that are not pure black (0,0,0)
                    if len(original_clothes_array.shape) == 3:
                        # For RGB images, check if all channels are not all zero
                        gray_check = np.mean(original_clothes_array, axis=2)
                        original_clothes_mask = (gray_check > 20).astype(np.uint8)  # Threshold to detect non-black pixels
                        # Apply morphological operations to clean up the mask
                        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
                        original_clothes_mask = cv2.morphologyEx(original_clothes_mask, cv2.MORPH_CLOSE, kernel)
                        original_clothes_mask = cv2.morphologyEx(original_clothes_mask, cv2.MORPH_OPEN, kernel)
                    else:
                        original_clothes_mask = (original_clothes_array > 20).astype(np.uint8)

                # Apply the mask to the new clothes image to remove its background
                original_clothes_array = np.array(original_new_clothes_img)
                if len(original_clothes_mask.shape) == 2:
                    original_clothes_mask_3ch = np.stack([original_clothes_mask] * 3, axis=-1)
                else:
                    original_clothes_mask_3ch = original_clothes_mask

                # Apply the mask to remove the background of the new clothes
                masked_original_clothes = (original_clothes_array * original_clothes_mask_3ch +
                                         (1 - original_clothes_mask_3ch) * np.array([255, 255, 255])).astype(np.uint8)  # White background
                masked_original_clothes_img = Image.fromarray(masked_original_clothes, 'RGB')

                # Now resize the MASKED clothes
                new_clothes_resized = masked_original_clothes_img.resize(original_img.size, Image.Resampling.LANCZOS)
                new_clothes_array = np.array(new_clothes_resized)

                # Use the composition mask to do final direct replacement
                if len(composition_mask.shape) == 3:
                    comp_mask_3ch = composition_mask
                else:
                    comp_mask_3ch = np.stack([composition_mask] * 3, axis=-1)

                # Very aggressive final replacement - use very low threshold to ensure maximum coverage
                final_direct_replace = np.where(
                    comp_mask_3ch > 0.1,  # Very low threshold
                    new_clothes_array,    # MASKED new clothes
                    final_array           # Keep other parts as processed
                ).astype(np.uint8)

                final_img = Image.fromarray(final_direct_replace, 'RGB')

        # Apply final enhancements
        final_img = enhance_contrast_brightness(final_img)
        final_img = sharpen_image(final_img)

        # Additional enhancement to make clothes difference more visible if needed
        original_array = np.array(original_img)
        final_array = np.array(final_img)

        # Ensure both arrays have the same dimensions before comparison
        if original_array.shape != final_array.shape:
            # Resize final_array to match original_array dimensions
            final_array = cv2.resize(final_array, (original_array.shape[1], original_array.shape[0]), interpolation=cv2.INTER_CUBIC)

        # Check if overall difference is still quite low
        overall_diff = np.mean(np.abs(final_array.astype(float) - original_array.astype(float)))
        if overall_diff < 30:  # Increased threshold to trigger enhancement more often
            print(f"Overall difference still low ({overall_diff}), enhancing further...")

            # Enhance the contrast specifically in areas where clothes should be changed
            # Use the most accurate specific garment mask instead of default parsing masks
            specific_garment_mask = enhanced_masks.get(mask_key, get_specific_garment_mask(original_img, garment_type))

            if garment_type == 'top':
                garment_mask = specific_garment_mask
            elif garment_type == 'bottom':
                garment_mask = specific_garment_mask
            elif garment_type == 'full':
                garment_mask = specific_garment_mask
            else:
                # For specific garment names, use the specific mask
                garment_mask = specific_garment_mask

            if garment_mask is not None:
                # Expand mask to 3 channels if needed
                if len(garment_mask.shape) == 2:
                    garment_mask_3ch = np.stack([garment_mask] * 3, axis=-1)
                else:
                    garment_mask_3ch = garment_mask

                # Enhance colors and contrast specifically in garment areas
                enhanced_array = final_array.copy()

                # Convert to HSV for better color manipulation
                hsv = cv2.cvtColor(enhanced_array, cv2.COLOR_RGB2HSV).astype(np.float32)

                # Enhance saturation in garment areas
                saturation = hsv[:, :, 1]
                mask_for_sat = garment_mask_3ch[:, :, 0] if len(garment_mask_3ch.shape) > 2 else garment_mask_3ch[:, :, 0]

                # Boost saturation in garment areas
                enhanced_sat = np.where(
                    mask_for_sat > 0.1,  # In garment areas - using much lower threshold for more coverage
                    np.clip(saturation * 1.4, 0, 255),  # Boost saturation
                    saturation  # Keep other areas as is
                )
                hsv[:, :, 1] = enhanced_sat

                # Convert back to RGB
                enhanced_array = cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2RGB)

                # Also increase brightness slightly in garment areas for better visibility
                for c in range(3):  # For each color channel
                    channel = enhanced_array[:, :, c].astype(np.float32)
                    mask_slice = garment_mask_3ch[:, :, c] if len(garment_mask_3ch.shape) > 2 else garment_mask_3ch[:, :, 0]

                    # Slightly boost brightness in garment areas
                    enhanced_channel = np.where(
                        mask_slice > 0.1,  # In garment areas - using much lower threshold for more coverage
                        np.clip(channel * 1.15, 0, 255),  # Boost brightness
                        channel  # Keep other areas as is
                    )
                    enhanced_array[:, :, c] = enhanced_channel.astype(np.uint8)

                final_img = Image.fromarray(enhanced_array, 'RGB')
                print("Enhanced saturation and brightness in garment area to improve visibility.")

        # Convert back to original size if resized for processing
        if (proc_width, proc_height) != (orig_width, orig_height):
            final_img = final_img.resize((orig_width, orig_height), Image.Resampling.LANCZOS)

        # Save the final image to the output directory
        output_dir = os.path.join(current_dir, "output")
        os.makedirs(output_dir, exist_ok=True)

        # Save the original uploaded images
        original_img = Image.open(io.BytesIO(original_contents))
        original_timestamp = int(time.time())
        original_filename = f"original_{original_timestamp}_{original_image.filename}"
        original_path = os.path.join(output_dir, original_filename)
        original_img.save(original_path)
        print(f"Saved original to {original_path}")

        # Save the clothes image as well
        clothes_img_original = Image.open(io.BytesIO(new_clothes_contents))
        clothes_filename = f"clothes_{original_timestamp}_{new_clothes_image.filename}"
        clothes_path = os.path.join(output_dir, clothes_filename)
        clothes_img_original.save(clothes_path)
        print(f"Saved clothes image to {clothes_path}")

        # Generate a unique filename for processed result
        timestamp = int(time.time())
        output_filename = f"result_{timestamp}.png"
        output_path = os.path.join(output_dir, output_filename)
        final_img.save(output_path)
        print(f"Saved result to {output_path}")

        # Also save metadata about this processed image
        metadata = {
            "id": output_filename,
            "input_filename": original_image.filename,
            "clothes_filename": new_clothes_image.filename,
            "original_filename": original_filename,
            "clothes_original_filename": clothes_filename,
            "operation": "replace-clothes",
            "garment_type": garment_type,
            "timestamp": timestamp,
            "timestamp_formatted": time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(timestamp)),
            "original_path": f"/api/image/{original_filename}",
            "clothes_path": f"/api/image/{clothes_filename}",
            "processed_path": f"/api/image/{output_filename}",
            "api_endpoint": f"/api/image/{output_filename}",
            "user_id": current_user.id,  # Add user ID to track
            "title": f"Replaced {garment_type} clothes - {original_image.filename}"
        }

        # Save metadata to a JSON file
        metadata_path = os.path.join(output_dir, f"{output_filename}.json")
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f)

        # Create debug images if requested
        debug_images = {}
        if return_debug:
            debug_visuals = create_debug_visuals(
                original_img,
                clothes_img,
                warped_cloth,
                composition_mask,
                final_img
            )
            debug_images = {
                'pipeline_steps': image_to_bytes(debug_visuals['pipeline_steps']),
                'composition_mask': image_to_bytes(debug_visuals['composition_mask'])
            }

        # Apply watermark to final result
        watermarked_img = add_watermark(final_img, current_user.id)

        # Convert final result to bytes
        output_bytes = image_to_bytes(watermarked_img)

        # Prepare response
        response_data = {
            "result_image": output_bytes.getvalue()
        }

        if return_debug:
            response_data["debug_masks"] = debug_images['composition_mask']
            response_data["warp_preview"] = debug_images['pipeline_steps']
            response_data["composition_mask"] = debug_images['composition_mask']

        # Return JSON response with image data
        from fastapi.responses import Response

        # Encode images as base64 for JSON response
        result_base64 = base64.b64encode(response_data["result_image"]).decode('utf-8')

        response_json = {
            "result_image": f"data:image/png;base64,{result_base64}",
            "status": "success",
            "message": "Clothes replacement completed successfully",
            "output_path": output_path,  # Include the output path for verification
            "replacement_quality": replacement_quality  # Include quality metrics
        }

        if return_debug:
            warp_base64 = base64.b64encode(response_data["warp_preview"]).decode('utf-8')
            mask_base64 = base64.b64encode(response_data["composition_mask"]).decode('utf-8')
            response_json.update({
                "debug_masks": f"data:image/png;base64,{mask_base64}",
                "warp_preview": f"data:image/png;base64,{warp_base64}",
                "composition_mask": f"data:image/png;base64,{mask_base64}"
            })

        # Apply final enhancements
        final_img = enhance_contrast_brightness(final_img)
        final_img = sharpen_image(final_img)

        # Additional enhancement to make clothes difference more visible if needed
        original_array = np.array(original_img)
        final_array = np.array(final_img)

        # Ensure both arrays have the same dimensions before comparison
        if original_array.shape != final_array.shape:
            # Resize final_array to match original_array dimensions
            final_array = cv2.resize(final_array, (original_array.shape[1], original_array.shape[0]), interpolation=cv2.INTER_CUBIC)

        # Check if overall difference is still quite low
        overall_diff = np.mean(np.abs(final_array.astype(float) - original_array.astype(float)))
        if overall_diff < 30:  # Increased threshold to trigger enhancement more often
            print(f"Overall difference still low ({overall_diff}), enhancing further...")

            # Enhance the contrast specifically in areas where clothes should be changed
            # Use the most accurate specific garment mask instead of default parsing masks
            specific_garment_mask = get_specific_garment_mask(original_img, garment_type)

            if garment_type == 'top':
                garment_mask = specific_garment_mask
            elif garment_type == 'bottom':
                garment_mask = specific_garment_mask
            elif garment_type == 'full':
                garment_mask = specific_garment_mask
            else:
                # For specific garment names, use the specific mask
                garment_mask = specific_garment_mask

            if garment_mask is not None:
                # Expand mask to 3 channels if needed
                if len(garment_mask.shape) == 2:
                    garment_mask_3ch = np.stack([garment_mask] * 3, axis=-1)
                else:
                    garment_mask_3ch = garment_mask

                # Enhance colors and contrast specifically in garment areas
                enhanced_array = final_array.copy()

                # Convert to HSV for better color manipulation
                hsv = cv2.cvtColor(enhanced_array, cv2.COLOR_RGB2HSV).astype(np.float32)

                # Enhance saturation in garment areas
                saturation = hsv[:, :, 1]
                mask_for_sat = garment_mask_3ch[:, :, 0] if len(garment_mask_3ch.shape) > 2 else garment_mask_3ch[:, :, 0]

                # Boost saturation in garment areas
                enhanced_sat = np.where(
                    mask_for_sat > 0.1,  # In garment areas - using much lower threshold for more coverage
                    np.clip(saturation * 1.4, 0, 255),  # Boost saturation
                    saturation  # Keep other areas as is
                )
                hsv[:, :, 1] = enhanced_sat

                # Convert back to RGB
                enhanced_array = cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2RGB)

                # Also increase brightness slightly in garment areas for better visibility
                for c in range(3):  # For each color channel
                    channel = enhanced_array[:, :, c].astype(np.float32)
                    mask_slice = garment_mask_3ch[:, :, c] if len(garment_mask_3ch.shape) > 2 else garment_mask_3ch[:, :, 0]

                    # Slightly boost brightness in garment areas
                    enhanced_channel = np.where(
                        mask_slice > 0.1,  # In garment areas - using much lower threshold for more coverage
                        np.clip(channel * 1.15, 0, 255),  # Boost brightness
                        channel  # Keep other areas as is
                    )
                    enhanced_array[:, :, c] = enhanced_channel.astype(np.uint8)

                final_img = Image.fromarray(enhanced_array, 'RGB')
                print("Enhanced saturation and brightness in garment area to improve visibility.")

        # Convert back to original size if resized for processing
        if (proc_width, proc_height) != (orig_width, orig_height):
            final_img = final_img.resize((orig_width, orig_height), Image.Resampling.LANCZOS)

        # Save the final image to the output directory
        output_dir = os.path.join(current_dir, "output")
        os.makedirs(output_dir, exist_ok=True)

        # Save the original uploaded images
        original_img = Image.open(io.BytesIO(original_contents))
        original_timestamp = int(time.time())
        original_filename = f"original_{original_timestamp}_{original_image.filename}"
        original_path = os.path.join(output_dir, original_filename)
        original_img.save(original_path)
        print(f"Saved original to {original_path}")

        # Save the clothes image as well
        clothes_img_original = Image.open(io.BytesIO(new_clothes_contents))
        clothes_filename = f"clothes_{original_timestamp}_{new_clothes_image.filename}"
        clothes_path = os.path.join(output_dir, clothes_filename)
        clothes_img_original.save(clothes_path)
        print(f"Saved clothes image to {clothes_path}")

        # Generate a unique filename for processed result
        timestamp = int(time.time())
        output_filename = f"result_{timestamp}.png"
        output_path = os.path.join(output_dir, output_filename)
        final_img.save(output_path)
        print(f"Saved result to {output_path}")

        # Also save metadata about this processed image
        metadata = {
            "id": output_filename,
            "input_filename": original_image.filename,
            "clothes_filename": new_clothes_image.filename,
            "original_filename": original_filename,
            "clothes_original_filename": clothes_filename,
            "operation": "replace-clothes",
            "garment_type": garment_type,
            "timestamp": timestamp,
            "timestamp_formatted": time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(timestamp)),
            "original_path": f"/api/image/{original_filename}",
            "clothes_path": f"/api/image/{clothes_filename}",
            "processed_path": f"/api/image/{output_filename}",
            "api_endpoint": f"/api/image/{output_filename}",
            "user_id": current_user.id,  # Add user ID to track
            "title": f"Replaced {garment_type} clothes - {original_image.filename}"
        }

        # Save metadata to a JSON file
        metadata_path = os.path.join(output_dir, f"{output_filename}.json")
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f)

        # Create debug images if requested
        debug_images = {}
        if return_debug:
            debug_visuals = create_debug_visuals(
                original_img,
                clothes_img,
                warped_cloth,
                composition_mask,
                final_img
            )
            debug_images = {
                'pipeline_steps': image_to_bytes(debug_visuals['pipeline_steps']),
                'composition_mask': image_to_bytes(debug_visuals['composition_mask'])
            }

        # Apply watermark to final result
        watermarked_img = add_watermark(final_img, current_user.id)

        # Convert final result to bytes
        output_bytes = image_to_bytes(watermarked_img)

        # Prepare response
        response_data = {
            "result_image": output_bytes.getvalue()
        }

        if return_debug:
            response_data["debug_masks"] = debug_images['composition_mask']
            response_data["warp_preview"] = debug_images['pipeline_steps']
            response_data["composition_mask"] = debug_images['composition_mask']

        # Return JSON response with image data
        from fastapi.responses import Response

        # Encode images as base64 for JSON response
        result_base64 = base64.b64encode(response_data["result_image"]).decode('utf-8')

        response_json = {
            "result_image": f"data:image/png;base64,{result_base64}",
            "status": "success",
            "message": "Clothes replacement completed successfully",
            "output_path": output_path,  # Include the output path for verification
            "replacement_quality": replacement_quality  # Include quality metrics
        }

        if return_debug:
            warp_base64 = base64.b64encode(response_data["warp_preview"]).decode('utf-8')
            mask_base64 = base64.b64encode(response_data["composition_mask"]).decode('utf-8')
            response_json.update({
                "debug_masks": f"data:image/png;base64,{mask_base64}",
                "warp_preview": f"data:image/png;base64,{warp_base64}",
                "composition_mask": f"data:image/png;base64,{mask_base64}"
            })

        # If return_cropped is True, create and return a cropped version of just the garment
        if return_cropped:
            print("Creating cropped garment image...")

            # Convert the final image to array for processing
            final_img_array = np.array(final_img)

            # Ensure composition mask is in the right format
            if len(composition_mask.shape) == 3:
                garment_mask_2d = composition_mask[:, :, 0]  # Take first channel
            else:
                garment_mask_2d = composition_mask

            # Find bounding box of the garment area
            coords = np.where(garment_mask_2d > 0.1)  # Use threshold to find garment pixels
            if len(coords[0]) > 0 and len(coords[1]) > 0:  # If garment mask has content
                y_min, y_max = coords[0].min(), coords[0].max()
                x_min, x_max = coords[1].min(), coords[1].max()

                # Add a small padding around the garment
                padding = max(int(0.05 * min(final_img.width, final_img.height)), 5)  # 5% padding or 5px min
                y_min = max(0, y_min - padding)
                y_max = min(final_img_array.shape[0], y_max + padding)
                x_min = max(0, x_min - padding)
                x_max = min(final_img_array.shape[1], x_max + padding)

                # Crop the image to the bounding box
                cropped_img_array = final_img_array[y_min:y_max, x_min:x_max]
                cropped_mask = garment_mask_2d[y_min:y_max, x_min:x_max]

                # Apply the mask to the cropped image to remove background outside the garment
                cropped_mask_3ch = np.stack([cropped_mask] * 3, axis=-1) if len(cropped_mask.shape) == 2 else cropped_mask
                cropped_result = (cropped_img_array * cropped_mask_3ch +
                                 (1 - cropped_mask_3ch) * np.array([255, 255, 255])).astype(np.uint8)  # White background

                # Convert back to PIL Image
                cropped_img = Image.fromarray(cropped_result, 'RGB')

                # Convert to bytes
                cropped_bytes = image_to_bytes(cropped_img)
                cropped_base64 = base64.b64encode(cropped_bytes.getvalue()).decode('utf-8')

                # Add cropped image to response
                response_json["cropped_garment"] = f"data:image/png;base64,{cropped_base64}"
                response_json["message"] = "Clothes replacement completed successfully with cropped garment"

        return response_json

    except Exception as e:
        import traceback
        raise HTTPException(status_code=500, detail=f"Error processing images: {str(e)}\n{traceback.format_exc()}")


@app.post("/api/public-replace-clothes")
async def public_replace_clothes(
    original_image: UploadFile = File(..., description="Original image with person wearing clothes to be replaced"),
    new_clothes_image: UploadFile = File(..., description="New clothes image to replace with"),
    garment_type: str = Form("top", description="Type of garment: top, bottom, full, or provide clothing name like 'shirt', 'pants', 'dress'"),
    options: str = Form('{}', description="JSON options like {\"preserve_logo\":true,\"resolution\":1024}"),
    return_debug: bool = Form(False, description="Return debug images for visualization"),
    enable_manual_correction: bool = Form(False, description="Enable manual mask correction capability"),
    return_cropped: bool = Form(False, description="Return cropped version of just the replaced garment")
):
    """
    Enhanced clothes replacement with improved segmentation, blending, and validation (public endpoint without authentication).

    Processing flow:
    1. Enhanced garment segmentation with validation
    2. Human detection & parsing
    3. Pose estimation
    4. Cloth alignment (warping)
    5. Advanced composition & blending
    6. Quality validation and enhancement
    7. Refinement and post-processing

    Args:
        original_image: Original image with person wearing clothes to be replaced (PNG, JPG, etc.)
        new_clothes_image: New clothes image to replace with (PNG, JPG, etc.)
        garment_type: Type of garment ('top', 'bottom', 'full') or specific clothing name like 'shirt', 'pants', 'dress' - defaults to 'top'
        options: JSON string with options like {"preserve_logo": true, "resolution": 1024}
        return_debug: Whether to return debug images for visualization
        enable_manual_correction: Enable manual mask correction capability

    Returns:
        JSON with result_image and optionally debug images (debug_masks, warp_preview, composition_mask)
    """
    try:
        # Parse options
        try:
            options_dict = json.loads(options) if options else {}
        except json.JSONDecodeError:
            options_dict = {}

        preserve_logo = options_dict.get('preserve_logo', False)
        resolution = options_dict.get('resolution', 1024)
        manual_correction = options_dict.get('manual_correction', False)

        # Auto-detect garment type from the provided text if not one of standard types
        if garment_type not in ['top', 'bottom', 'full']:
            detected_type = detect_garment_type_from_text(garment_type)
            print(f"Auto-detected garment type: '{garment_type}' -> '{detected_type}'")
            garment_type = detected_type
        else:
            print(f"Using provided garment type: {garment_type}")

        # Read both uploaded files
        original_contents = await original_image.read()
        new_clothes_contents = await new_clothes_image.read()

        # Validate file sizes (max 10MB each)
        if len(original_contents) > 10 * 1024 * 1024:
            raise HTTPException(status_code=400, detail="Original image file size exceeds 10MB limit")

        if len(new_clothes_contents) > 10 * 1024 * 1024:
            raise HTTPException(status_code=400, detail="New clothes image file size exceeds 10MB limit")

        # Open images
        original_img = Image.open(io.BytesIO(original_contents)).convert("RGB")
        clothes_img = Image.open(io.BytesIO(new_clothes_contents)).convert("RGB")

        # Store original dimensions for later use
        orig_width, orig_height = original_img.size
        orig_aspect_ratio = orig_width / orig_height

        # Determine the processing resolution - either original or limited by max resolution
        if max(orig_width, orig_height) > resolution:
            if orig_width > orig_height:
                proc_width = resolution
                proc_height = int(resolution / orig_aspect_ratio)
            else:
                proc_height = resolution
                proc_width = int(resolution * orig_aspect_ratio)
        else:
            proc_width, proc_height = orig_width, orig_height

        # Resize both images to the same processing dimensions to avoid shape mismatch
        original_img = original_img.resize((proc_width, proc_height), Image.Resampling.LANCZOS)
        clothes_img = clothes_img.resize((proc_width, proc_height), Image.Resampling.LANCZOS)

        # Ensure both images have exactly the same dimensions after resizing
        if original_img.size != clothes_img.size:
            # If there's still a slight difference due to rounding, fix it
            clothes_img = clothes_img.resize(original_img.size, Image.Resampling.LANCZOS)

        # STEP 1: Pose estimation (needed for fallback masks)
        keypoints = estimate_pose_from_image(original_img)
        print(f"Generated {len(keypoints)} keypoints for pose estimation")

        # STEP 2: Enhanced human parsing and garment segmentation
        print("Starting enhanced garment segmentation...")
        parsing_model = load_pretrained_model()
        enhanced_masks = enhanced_garment_segmentation(original_img, garment_type, parsing_model)

        # Validate mask accuracy
        mask_key = list(enhanced_masks.keys())[0]  # Get the first available mask
        current_mask = enhanced_masks[mask_key]
        is_valid_mask, mask_validation_msg = validate_mask_accuracy(original_img, current_mask, garment_type)
        print(f"Mask validation: {mask_validation_msg}")

        # If mask validation fails (low coverage or other issues), create a pose-based fallback mask
        if not is_valid_mask:
            mask_coverage = np.mean(current_mask)

            # If completely no coverage or very low coverage (< 0.5%), use pose-based fallback
            if mask_coverage < 0.005:  # < 0.5% coverage
                print("Segmentation failed or has very low coverage. Creating pose-based fallback mask...")
                # Generate a fallback mask based on pose estimation
                if garment_type == 'top':
                    fallback_mask = create_torso_mask(original_img, keypoints)
                elif garment_type == 'bottom':
                    fallback_mask = create_lower_body_mask(original_img, keypoints)
                elif garment_type == 'full':
                    # Combine upper and lower torso
                    upper_mask = refine_shirt_mask_with_parsing(parsing_model, original_img, keypoints, "top")
                    lower_mask = create_lower_body_mask(original_img, keypoints)
                    fallback_mask = np.maximum(upper_mask, lower_mask)
                else:  # Default to top
                    fallback_mask = refine_shirt_mask_with_parsing(parsing_model, original_img, keypoints, "top")

                # Apply refinement to the fallback mask
                fallback_mask = refine_mask_boundaries(fallback_mask, np.array(original_img))
                enhanced_masks[mask_key] = fallback_mask
                current_mask = fallback_mask
                # Re-validate the fallback mask
                is_valid_mask, mask_validation_msg = validate_mask_accuracy(original_img, current_mask, garment_type)
                print(f"Fallback mask validation: {mask_validation_msg}")

            # If validation still fails after initial check, but we have some mask coverage,
            # consider using pose-based mask as an alternative if it's better than current
            elif mask_coverage < 0.05 and not is_valid_mask:  # Less than 5% coverage and still not valid
                print("Low coverage mask detected. Creating pose-based mask as alternative...")
                # Create pose-based mask to compare
                if garment_type == 'top':
                    pose_based_mask = refine_shirt_mask_with_parsing(parsing_model, original_img, keypoints, "top")
                elif garment_type == 'bottom':
                    pose_based_mask = create_lower_body_mask(original_img, keypoints)
                elif garment_type == 'full':
                    upper_mask = refine_shirt_mask_with_parsing(parsing_model, original_img, keypoints, "top")
                    lower_mask = create_lower_body_mask(original_img, keypoints)
                    pose_based_mask = np.maximum(upper_mask, lower_mask)
                else:  # Default to top
                    pose_based_mask = refine_shirt_mask_with_parsing(parsing_model, original_img, keypoints, "top")

                # Check the pose-based mask coverage
                pose_mask_coverage = np.mean(pose_based_mask)
                if pose_mask_coverage > mask_coverage:  # If pose-based mask covers more area
                    print(f"Pose-based mask has better coverage ({pose_mask_coverage:.2%} vs {mask_coverage:.2%}), using it instead...")
                    pose_based_mask = refine_mask_boundaries(pose_based_mask, np.array(original_img))
                    enhanced_masks[mask_key] = pose_based_mask
                    current_mask = pose_based_mask
                    # Re-validate the pose-based mask
                    is_valid_mask, mask_validation_msg = validate_mask_accuracy(original_img, current_mask, garment_type)
                    print(f"Pose-based mask validation: {mask_validation_msg}")

            elif not is_valid_mask and enable_manual_correction:
                print("Applying manual mask correction...")
                corrected_mask = manual_mask_correction(original_img, current_mask)
                enhanced_masks[mask_key] = corrected_mask

        # Refine mask boundaries using image features
        refined_mask = refine_mask_boundaries(current_mask, np.array(original_img))
        enhanced_masks[mask_key] = refined_mask

        # STEP 3: Cloth alignment (warping)
        # Ensure images have the same size before warping
        if original_img.size != clothes_img.size:
            clothes_img = clothes_img.resize(original_img.size, Image.Resampling.LANCZOS)

        # Create a mask for the new clothes image to extract only the clothes part and remove background
        # This will prevent the black background of the new clothes from being warped and blended
        print("Creating mask for new clothes image to remove background...")

        # First, try to use the existing function
        try:
            new_clothes_mask = create_cloth_mask_from_image(clothes_img)
        except:
            # If the function fails, create a basic mask to detect non-black pixels
            print("Falling back to basic black background detection...")
            clothes_array = np.array(clothes_img)
            # Detect pixels that are not pure black (0,0,0)
            if len(clothes_array.shape) == 3:
                # For RGB images, check if all channels are not all zero
                gray_check = np.mean(clothes_array, axis=2)
                new_clothes_mask = (gray_check > 20).astype(np.uint8)  # Threshold to detect non-black pixels
                # Apply morphological operations to clean up the mask
                kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
                new_clothes_mask = cv2.morphologyEx(new_clothes_mask, cv2.MORPH_CLOSE, kernel)
                new_clothes_mask = cv2.morphologyEx(new_clothes_mask, cv2.MORPH_OPEN, kernel)
            else:
                new_clothes_mask = (clothes_array > 20).astype(np.uint8)

        # Apply the mask to the new clothes image to remove its background
        clothes_array = np.array(clothes_img)
        if len(new_clothes_mask.shape) == 2:
            new_clothes_mask_3ch = np.stack([new_clothes_mask] * 3, axis=-1)
        else:
            new_clothes_mask_3ch = new_clothes_mask

        # Apply the mask to remove the background of the new clothes
        masked_clothes = (clothes_array * new_clothes_mask_3ch +
                         (1 - new_clothes_mask_3ch) * np.array([255, 255, 255])).astype(np.uint8)  # White background
        masked_clothes_img = Image.fromarray(masked_clothes, 'RGB')

        # Improve size fitting: Before warping, estimate the target garment size from the segmentation mask
        # and resize the new clothes to approximately match those dimensions for better initial scaling
        print("Analyzing target garment area for size fitting...")
        # Get the mask for the current garment type to understand target size
        if mask_key in enhanced_masks:
            target_mask = enhanced_masks[mask_key]
            # Find bounding box of the target garment area
            coords = np.where(target_mask > 0.1)
            if len(coords[0]) > 0 and len(coords[1]) > 0:
                y_min, y_max = coords[0].min(), coords[0].max()
                x_min, x_max = coords[1].min(), coords[1].max()

                # Calculate target dimensions
                target_height = y_max - y_min
                target_width = x_max - x_min

                # Get current dimensions of the masked clothes
                current_height, current_width = masked_clothes_img.height, masked_clothes_img.width

                # Calculate a scaling factor to better match target dimensions
                # Preserve aspect ratio while fitting within the target area with some margin
                scale_h = target_height / current_height * 0.8  # 80% to allow for fitting
                scale_w = target_width / current_width * 0.8

                # Use the smaller scale to ensure the clothes fit within the target area
                scale_factor = min(scale_h, scale_w, 1.0)  # Don't upscale beyond 1.0

                if scale_factor < 1.0:  # Only resize if scaling down
                    new_size = (int(current_width * scale_factor), int(current_height * scale_factor))
                    masked_clothes_img = masked_clothes_img.resize(new_size, Image.Resampling.LANCZOS)

                    # Also resize the mask to match
                    new_clothes_mask_resized = cv2.resize(new_clothes_mask, new_size, interpolation=cv2.INTER_NEAREST)

                    # Reapply the mask after resizing to ensure no background pixels are introduced
                    resized_clothes_array = np.array(masked_clothes_img)
                    if len(new_clothes_mask_resized.shape) == 2:
                        resized_mask_3ch = np.stack([new_clothes_mask_resized] * 3, axis=-1)
                    else:
                        resized_mask_3ch = new_clothes_mask_resized

                    # Apply the resized mask to make sure background is still clean
                    masked_and_resized = (resized_clothes_array * resized_mask_3ch +
                                         (1 - resized_mask_3ch) * np.array([255, 255, 255])).astype(np.uint8)
                    masked_clothes_img = Image.fromarray(masked_and_resized, 'RGB')

        print("Warping cloth to fit person's pose...")
        # Warp the masked clothes image (with background removed) to fit the person's pose
        warped_cloth, tps_transformer = warp_cloth_tps(
            masked_clothes_img,  # Use the masked version without background
            original_img,
            keypoints,
            keypoints_cloth=None  # Will be generated internally
        )

        # STEP 4: Create enhanced composition mask
        print("Creating enhanced composition mask...")
        composition_mask = create_enhanced_composition_mask(
            original_img,
            enhanced_masks,
            keypoints,
            garment_type,
            mask_refinement=True
        )

        # STEP 5: Enhanced composition and blending
        print("Performing enhanced blending...")
        # Use enhanced blending function
        result_img = enhanced_blend_images(
            original_img,
            warped_cloth,
            composition_mask,
            garment_type
        )

        # Safety check: Ensure original image is preserved outside garment area
        # This ensures that even if enhanced_blend_images doesn't perfectly respect the mask,
        # we explicitly preserve the original image outside the garment area
        original_array = np.array(original_img)
        result_array = np.array(result_img)

        # Ensure composition mask is in the right format
        if len(composition_mask.shape) == 3:
            garment_mask_2d = composition_mask[:, :, 0]  # Take first channel
        else:
            garment_mask_2d = composition_mask

        # Expand mask to 3 channels for RGB
        if len(garment_mask_2d.shape) == 2:
            mask_3ch = np.stack([garment_mask_2d] * 3, axis=-1)
        else:
            mask_3ch = garment_mask_2d

        # Ensure mask values are between 0 and 1
        mask_3ch = np.clip(mask_3ch, 0, 1)

        # Preserve original image outside the mask, and use result inside the mask
        final_array = original_array * (1 - mask_3ch) + result_array * mask_3ch
        result_img = Image.fromarray(final_array.astype(np.uint8), 'RGB')

        # Improve size fitting: Adjust the garment area to better match original dimensions
        # Find the bounding box of the garment mask to understand the target area
        coords = np.where(garment_mask_2d > 0.1)  # Use threshold to find garment pixels
        if len(coords[0]) > 0 and len(coords[1]) > 0:  # If garment mask has content
            y_min, y_max = coords[0].min(), coords[0].max()
            x_min, x_max = coords[1].min(), coords[1].max()

            # Calculate the size of the target garment area
            target_h, target_w = y_max - y_min, x_max - x_min

            # The warped garment should already have similar proportions to the target,
            # but we can enhance the blending to make sure it fits well within the boundaries
            # Create a refined mask with soft edges for smoother blending
            refined_mask = cv2.GaussianBlur(garment_mask_2d, (15, 15), 0)  # Smooth edges
            refined_mask_3ch = np.stack([refined_mask] * 3, axis=-1) if len(refined_mask.shape) == 2 else refined_mask
            refined_mask_3ch = np.clip(refined_mask_3ch, 0, 1)

            # Apply the refined mask to ensure smooth integration
            final_array = original_array * (1 - refined_mask_3ch) + result_array * refined_mask_3ch
            result_img = Image.fromarray(final_array.astype(np.uint8), 'RGB')

        # STEP 6: Validate clothes replacement effectiveness
        print("Validating clothes replacement effectiveness...")
        replacement_quality = detect_replacement_quality(
            original_img,
            result_img,
            composition_mask[:, :, 0] if len(composition_mask.shape) == 3 else composition_mask
        )

        print(f"Replacement quality: {replacement_quality['quality']} (confidence: {replacement_quality['confidence']:.2f})")

        # If replacement quality is low, use more aggressive approach
        if not replacement_quality['is_successful']:
            print("Clothes replacement quality is low. Using more aggressive approach...")

            # Even more aggressive: use the original new clothes image directly from the byte stream
            # to ensure we have a completely unprocessed version, with proper sizing
            original_array = np.array(original_img)
            result_array = np.array(result_img)

            # Use the original new clothes image directly from the uploaded content
            original_new_clothes_img = Image.open(io.BytesIO(new_clothes_contents)).convert("RGB")

            # Create a mask for the new clothes image to extract only the clothes part and remove background
            print("Creating mask for new clothes image to remove background (aggressive replacement)...")

            # Try to create a mask for the new clothes image
            try:
                original_clothes_mask = create_cloth_mask_from_image(original_new_clothes_img)
            except:
                # If the function fails, create a basic mask to detect non-black pixels
                print("Falling back to basic black background detection (aggressive replacement)...")
                original_clothes_array = np.array(original_new_clothes_img)
                # Detect pixels that are not pure black (0,0,0)
                if len(original_clothes_array.shape) == 3:
                    # For RGB images, check if all channels are not all zero
                    gray_check = np.mean(original_clothes_array, axis=2)
                    original_clothes_mask = (gray_check > 20).astype(np.uint8)  # Threshold to detect non-black pixels
                    # Apply morphological operations to clean up the mask
                    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
                    original_clothes_mask = cv2.morphologyEx(original_clothes_mask, cv2.MORPH_CLOSE, kernel)
                    original_clothes_mask = cv2.morphologyEx(original_clothes_mask, cv2.MORPH_OPEN, kernel)
                else:
                    original_clothes_mask = (original_clothes_array > 20).astype(np.uint8)

            # Apply the mask to the new clothes image to remove its background
            original_clothes_array = np.array(original_new_clothes_img)
            if len(original_clothes_mask.shape) == 2:
                original_clothes_mask_3ch = np.stack([original_clothes_mask] * 3, axis=-1)
            else:
                original_clothes_mask_3ch = original_clothes_mask

            # Apply the mask to remove the background of the new clothes
            masked_original_clothes = (original_clothes_array * original_clothes_mask_3ch +
                                     (1 - original_clothes_mask_3ch) * np.array([255, 255, 255])).astype(np.uint8)  # White background
            masked_original_clothes_img = Image.fromarray(masked_original_clothes, 'RGB')

            # Improve size fitting: Resize based on target garment area while preserving aspect ratio
            # Calculate the bounding box of the garment mask to determine the proper size
            if len(composition_mask.shape) == 3:
                mask_2d = composition_mask[:, :, 0]
            else:
                mask_2d = composition_mask

            # Find the bounding box of the mask to determine the area for clothes
            coords = np.where(mask_2d > 0.1)
            if len(coords[0]) > 0 and len(coords[1]) > 0:  # If there are any masked pixels
                y_min, y_max = coords[0].min(), coords[0].max()
                x_min, x_max = coords[1].min(), coords[1].max()

                # Calculate the size of the garment area in the original image
                target_height = y_max - y_min
                target_width = x_max - x_min

                # Get current dimensions of the masked clothes
                current_height, current_width = masked_original_clothes_img.height, masked_original_clothes_img.width

                # Calculate a scaling factor to better match target dimensions
                # Preserve aspect ratio while fitting within the target area with some margin
                scale_h = target_height / current_height * 0.8  # 80% to allow for fitting
                scale_w = target_width / current_width * 0.8

                # Use the smaller scale to ensure the clothes fit within the target area
                scale_factor = min(scale_h, scale_w, 1.0)  # Don't upscale beyond 1.0

                if scale_factor < 1.0:  # Only resize if scaling down
                    new_size = (int(current_width * scale_factor), int(current_height * scale_factor))
                    masked_original_clothes_img = masked_original_clothes_img.resize(new_size, Image.Resampling.LANCZOS)

                # Resize to target dimensions with proper aspect ratio handling
                new_clothes_sized = masked_original_clothes_img.resize(
                    (target_width, target_height),
                    Image.Resampling.LANCZOS
                )

                # Create a canvas to place the sized clothes onto
                sized_clothes_array = np.zeros_like(original_array)

                # Place the sized clothes in the appropriate location
                if (y_min + target_height <= original_array.shape[0] and
                    x_min + target_width <= original_array.shape[1]):
                    sized_clothes_array[y_min:y_min + target_height, x_min:x_min + target_width] = np.array(new_clothes_sized)
                else:
                    # If out of bounds, use the original approach but properly positioned
                    cloth_array = np.array(new_clothes_sized)
                    end_y = min(y_min + target_height, original_array.shape[0])
                    end_x = min(x_min + target_width, original_array.shape[1])
                    actual_h, actual_w = end_y - y_min, end_x - x_min
                    sized_clothes_array[y_min:end_y, x_min:end_x] = cloth_array[:actual_h, :actual_w]

                # Use the composition mask to directly replace areas
                if len(composition_mask.shape) == 3:
                    mask_3ch = composition_mask
                else:
                    mask_3ch = np.stack([composition_mask] * 3, axis=-1)

                # Apply direct replacement in high-confidence mask areas with properly sized clothes
                mask_threshold = 0.1  # Very low threshold to ensure maximum replacement area
                direct_replacement = np.where(
                    mask_3ch > mask_threshold,
                    sized_clothes_array,  # Use properly sized new clothes
                    original_array
                ).astype(np.uint8)
            else:
                # Fallback: use the original approach if no mask area found
                # But first, apply the background mask to the original clothes image
                try:
                    original_clothes_mask = create_cloth_mask_from_image(original_new_clothes_img)
                except:
                    # If the function fails, create a basic mask to detect non-black pixels
                    print("Falling back to basic black background detection (fallback)...")
                    original_clothes_array = np.array(original_new_clothes_img)
                    # Detect pixels that are not pure black (0,0,0)
                    if len(original_clothes_array.shape) == 3:
                        # For RGB images, check if all channels are not all zero
                        gray_check = np.mean(original_clothes_array, axis=2)
                        original_clothes_mask = (gray_check > 20).astype(np.uint8)  # Threshold to detect non-black pixels
                        # Apply morphological operations to clean up the mask
                        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
                        original_clothes_mask = cv2.morphologyEx(original_clothes_mask, cv2.MORPH_CLOSE, kernel)
                        original_clothes_mask = cv2.morphologyEx(original_clothes_mask, cv2.MORPH_OPEN, kernel)
                    else:
                        original_clothes_mask = (original_clothes_array > 20).astype(np.uint8)

                # Apply the mask to the new clothes image to remove its background
                original_clothes_array = np.array(original_new_clothes_img)
                if len(original_clothes_mask.shape) == 2:
                    original_clothes_mask_3ch = np.stack([original_clothes_mask] * 3, axis=-1)
                else:
                    original_clothes_mask_3ch = original_clothes_mask

                # Apply the mask to remove the background of the new clothes
                masked_original_clothes = (original_clothes_array * original_clothes_mask_3ch +
                                         (1 - original_clothes_mask_3ch) * np.array([255, 255, 255])).astype(np.uint8)  # White background
                masked_original_clothes_img = Image.fromarray(masked_original_clothes, 'RGB')

                # Now resize the MASKED clothes
                new_clothes_resized = masked_original_clothes_img.resize(original_img.size, Image.Resampling.LANCZOS)
                new_clothes_array = np.array(new_clothes_resized)

                # Use the composition mask to directly replace areas
                if len(composition_mask.shape) == 3:
                    mask_3ch = composition_mask
                else:
                    mask_3ch = np.stack([composition_mask] * 3, axis=-1)

                # Apply direct replacement in high-confidence mask areas with maximum visibility
                mask_threshold = 0.1  # Very low threshold to ensure maximum replacement area
                direct_replacement = np.where(
                    mask_3ch > mask_threshold,
                    new_clothes_array,  # Use MASKED original new clothes
                    original_array
                ).astype(np.uint8)

            # For maximum impact, use 100% of the direct replacement instead of blending
            result_array = direct_replacement

            result_img = Image.fromarray(result_array, 'RGB')

            # Update the result_img to be used for all subsequent processing
            # This ensures that further processing steps use our replaced image
            final_img = result_img

            # Validate again after aggressive enhancement
            final_quality = detect_replacement_quality(
                original_img,
                result_img,
                composition_mask[:, :, 0] if len(composition_mask.shape) == 3 else composition_mask
            )
            print(f"Final replacement quality after aggressive enhancement: {final_quality['quality']} (confidence: {final_quality['confidence']:.2f})")
        else:
            print("Clothes replacement was effective based on comprehensive quality assessment.")

        # STEP 7: Refinement GAN
        print("Applying realism enhancement...")
        refined_img = enhance_realism(
            result_img,
            original_img,
            warped_cloth
        )

        # STEP 8: Post-processing
        print("Applying post-processing...")
        final_img = post_process_pipeline(
            refined_img,
            original_img,
            warped_cloth,
            enhanced_masks,  # Use enhanced masks instead of basic parsing masks
            composition_mask,
            garment_type
        )

        # Additional post-processing to ensure clothes are clearly visible
        original_array = np.array(original_img)
        final_array = np.array(final_img)

        # Check if the image is too similar to original, and enhance if needed
        similarity_check = detect_replacement_quality(original_img, final_img)
        if not similarity_check['is_successful']:
            print("Applying final enhancements for better visibility...")

            # Ultimate safeguard: if quality is still low after all processing,
            # do a final direct replacement with properly sized clothes
            original_new_clothes_img = Image.open(io.BytesIO(new_clothes_contents)).convert("RGB")

            # Create a mask for the new clothes image to extract only the clothes part and remove background
            print("Creating mask for new clothes image to remove background (final safeguard)...")

            # Try to create a mask for the new clothes image
            try:
                original_clothes_mask = create_cloth_mask_from_image(original_new_clothes_img)
            except:
                # If the function fails, create a basic mask to detect non-black pixels
                print("Falling back to basic black background detection (final safeguard)...")
                original_clothes_array = np.array(original_new_clothes_img)
                # Detect pixels that are not pure black (0,0,0)
                if len(original_clothes_array.shape) == 3:
                    # For RGB images, check if all channels are not all zero
                    gray_check = np.mean(original_clothes_array, axis=2)
                    original_clothes_mask = (gray_check > 20).astype(np.uint8)  # Threshold to detect non-black pixels
                    # Apply morphological operations to clean up the mask
                    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
                    original_clothes_mask = cv2.morphologyEx(original_clothes_mask, cv2.MORPH_CLOSE, kernel)
                    original_clothes_mask = cv2.morphologyEx(original_clothes_mask, cv2.MORPH_OPEN, kernel)
                else:
                    original_clothes_mask = (original_clothes_array > 20).astype(np.uint8)

            # Apply the mask to the new clothes image to remove its background
            original_clothes_array = np.array(original_new_clothes_img)
            if len(original_clothes_mask.shape) == 2:
                original_clothes_mask_3ch = np.stack([original_clothes_mask] * 3, axis=-1)
            else:
                original_clothes_mask_3ch = original_clothes_mask

            # Apply the mask to remove the background of the new clothes
            masked_original_clothes = (original_clothes_array * original_clothes_mask_3ch +
                                     (1 - original_clothes_mask_3ch) * np.array([255, 255, 255])).astype(np.uint8)  # White background
            masked_original_clothes_img = Image.fromarray(masked_original_clothes, 'RGB')

            # Improve size fitting: Resize based on target garment area while preserving aspect ratio
            # Calculate the bounding box of the garment mask to determine the proper size
            if len(composition_mask.shape) == 3:
                mask_2d = composition_mask[:, :, 0]
            else:
                mask_2d = composition_mask

            # Find the bounding box of the mask to determine the area for clothes
            coords = np.where(mask_2d > 0.1)
            if len(coords[0]) > 0 and len(coords[1]) > 0:  # If there are any masked pixels
                y_min, y_max = coords[0].min(), coords[0].max()
                x_min, x_max = coords[1].min(), coords[1].max()

                # Calculate the size of the garment area in the original image
                target_height = y_max - y_min
                target_width = x_max - x_min

                # Get current dimensions of the masked clothes
                current_height, current_width = masked_original_clothes_img.height, masked_original_clothes_img.width

                # Calculate a scaling factor to better match target dimensions
                # Preserve aspect ratio while fitting within the target area with some margin
                scale_h = target_height / current_height * 0.8  # 80% to allow for fitting
                scale_w = target_width / current_width * 0.8

                # Use the smaller scale to ensure the clothes fit within the target area
                scale_factor = min(scale_h, scale_w, 1.0)  # Don't upscale beyond 1.0

                if scale_factor < 1.0:  # Only resize if scaling down
                    new_size = (int(current_width * scale_factor), int(current_height * scale_factor))
                    masked_original_clothes_img = masked_original_clothes_img.resize(new_size, Image.Resampling.LANCZOS)

                # Resize to target dimensions with proper aspect ratio handling
                new_clothes_sized = masked_original_clothes_img.resize(
                    (target_width, target_height),
                    Image.Resampling.LANCZOS
                )

                # Create a canvas to place the sized clothes onto
                sized_clothes_array = np.zeros_like(original_array)

                # Place the sized clothes in the appropriate location
                if (y_min + target_height <= original_array.shape[0] and
                    x_min + target_width <= original_array.shape[1]):
                    sized_clothes_array[y_min:y_min + target_height, x_min:x_min + target_width] = np.array(new_clothes_sized)
                else:
                    # If out of bounds, use the original approach but properly positioned
                    cloth_array = np.array(new_clothes_sized)
                    end_y = min(y_min + target_height, original_array.shape[0])
                    end_x = min(x_min + target_width, original_array.shape[1])
                    actual_h, actual_w = end_y - y_min, end_x - x_min
                    sized_clothes_array[y_min:end_y, x_min:end_x] = cloth_array[:actual_h, :actual_w]

                # Use the composition mask to do final direct replacement with properly sized clothes
                if len(composition_mask.shape) == 3:
                    comp_mask_3ch = composition_mask
                else:
                    comp_mask_3ch = np.stack([composition_mask] * 3, axis=-1)

                # Final replacement - only replace in the mask area with properly sized clothes
                final_direct_replace = np.where(
                    comp_mask_3ch > 0.1,  # Very low threshold
                    sized_clothes_array,  # Properly sized new clothes
                    final_array           # Keep other parts as processed
                ).astype(np.uint8)

                final_img = Image.fromarray(final_direct_replace, 'RGB')
            else:
                # Fallback: use the original approach if no mask area found
                # But first, apply the background mask to the original clothes image
                try:
                    original_clothes_mask = create_cloth_mask_from_image(original_new_clothes_img)
                except:
                    # If the function fails, create a basic mask to detect non-black pixels
                    print("Falling back to basic black background detection (final safeguard fallback)...")
                    original_clothes_array = np.array(original_new_clothes_img)
                    # Detect pixels that are not pure black (0,0,0)
                    if len(original_clothes_array.shape) == 3:
                        # For RGB images, check if all channels are not all zero
                        gray_check = np.mean(original_clothes_array, axis=2)
                        original_clothes_mask = (gray_check > 20).astype(np.uint8)  # Threshold to detect non-black pixels
                        # Apply morphological operations to clean up the mask
                        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
                        original_clothes_mask = cv2.morphologyEx(original_clothes_mask, cv2.MORPH_CLOSE, kernel)
                        original_clothes_mask = cv2.morphologyEx(original_clothes_mask, cv2.MORPH_OPEN, kernel)
                    else:
                        original_clothes_mask = (original_clothes_array > 20).astype(np.uint8)

                # Apply the mask to the new clothes image to remove its background
                original_clothes_array = np.array(original_new_clothes_img)
                if len(original_clothes_mask.shape) == 2:
                    original_clothes_mask_3ch = np.stack([original_clothes_mask] * 3, axis=-1)
                else:
                    original_clothes_mask_3ch = original_clothes_mask

                # Apply the mask to remove the background of the new clothes
                masked_original_clothes = (original_clothes_array * original_clothes_mask_3ch +
                                         (1 - original_clothes_mask_3ch) * np.array([255, 255, 255])).astype(np.uint8)  # White background
                masked_original_clothes_img = Image.fromarray(masked_original_clothes, 'RGB')

                # Now resize the MASKED clothes
                new_clothes_resized = masked_original_clothes_img.resize(original_img.size, Image.Resampling.LANCZOS)
                new_clothes_array = np.array(new_clothes_resized)

                # Use the composition mask to do final direct replacement
                if len(composition_mask.shape) == 3:
                    comp_mask_3ch = composition_mask
                else:
                    comp_mask_3ch = np.stack([composition_mask] * 3, axis=-1)

                # Very aggressive final replacement - use very low threshold to ensure maximum coverage
                final_direct_replace = np.where(
                    comp_mask_3ch > 0.1,  # Very low threshold
                    new_clothes_array,    # MASKED new clothes
                    final_array           # Keep other parts as processed
                ).astype(np.uint8)

                final_img = Image.fromarray(final_direct_replace, 'RGB')

        # Apply final enhancements
        final_img = enhance_contrast_brightness(final_img)
        final_img = sharpen_image(final_img)

        # Additional enhancement to make clothes difference more visible if needed
        original_array = np.array(original_img)
        final_array = np.array(final_img)

        # Ensure both arrays have the same dimensions before comparison
        if original_array.shape != final_array.shape:
            # Resize final_array to match original_array dimensions
            final_array = cv2.resize(final_array, (original_array.shape[1], original_array.shape[0]), interpolation=cv2.INTER_CUBIC)

        # Check if overall difference is still quite low
        overall_diff = np.mean(np.abs(final_array.astype(float) - original_array.astype(float)))
        if overall_diff < 30:  # Increased threshold to trigger enhancement more often
            print(f"Overall difference still low ({overall_diff}), enhancing further...")

            # Enhance the contrast specifically in areas where clothes should be changed
            # Use the most accurate specific garment mask instead of default parsing masks
            specific_garment_mask = get_specific_garment_mask(original_img, garment_type)

            if garment_type == 'top':
                garment_mask = specific_garment_mask
            elif garment_type == 'bottom':
                garment_mask = specific_garment_mask
            elif garment_type == 'full':
                garment_mask = specific_garment_mask
            else:
                # For specific garment names, use the specific mask
                garment_mask = specific_garment_mask

            if garment_mask is not None:
                # Expand mask to 3 channels if needed
                if len(garment_mask.shape) == 2:
                    garment_mask_3ch = np.stack([garment_mask] * 3, axis=-1)
                else:
                    garment_mask_3ch = garment_mask

                # Enhance colors and contrast specifically in garment areas
                enhanced_array = final_array.copy()

                # Convert to HSV for better color manipulation
                hsv = cv2.cvtColor(enhanced_array, cv2.COLOR_RGB2HSV).astype(np.float32)

                # Enhance saturation in garment areas
                saturation = hsv[:, :, 1]
                mask_for_sat = garment_mask_3ch[:, :, 0] if len(garment_mask_3ch.shape) > 2 else garment_mask_3ch[:, :, 0]

                # Boost saturation in garment areas
                enhanced_sat = np.where(
                    mask_for_sat > 0.1,  # In garment areas - using much lower threshold for more coverage
                    np.clip(saturation * 1.4, 0, 255),  # Boost saturation
                    saturation  # Keep other areas as is
                )
                hsv[:, :, 1] = enhanced_sat

                # Convert back to RGB
                enhanced_array = cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2RGB)

                # Also increase brightness slightly in garment areas for better visibility
                for c in range(3):  # For each color channel
                    channel = enhanced_array[:, :, c].astype(np.float32)
                    mask_slice = garment_mask_3ch[:, :, c] if len(garment_mask_3ch.shape) > 2 else garment_mask_3ch[:, :, 0]

                    # Slightly boost brightness in garment areas
                    enhanced_channel = np.where(
                        mask_slice > 0.1,  # In garment areas - using much lower threshold for more coverage
                        np.clip(channel * 1.15, 0, 255),  # Boost brightness
                        channel  # Keep other areas as is
                    )
                    enhanced_array[:, :, c] = enhanced_channel.astype(np.uint8)

                final_img = Image.fromarray(enhanced_array, 'RGB')
                print("Enhanced saturation and brightness in garment area to improve visibility.")

        # Convert back to original size if resized for processing
        if (proc_width, proc_height) != (orig_width, orig_height):
            final_img = final_img.resize((orig_width, orig_height), Image.Resampling.LANCZOS)

        # Save the final image to the output directory
        output_dir = os.path.join(current_dir, "output")
        os.makedirs(output_dir, exist_ok=True)

        # Save the original uploaded images
        original_img = Image.open(io.BytesIO(original_contents))
        original_timestamp = int(time.time())
        original_filename = f"original_{original_timestamp}_{original_image.filename}"
        original_path = os.path.join(output_dir, original_filename)
        original_img.save(original_path)
        print(f"Saved original to {original_path}")

        # Save the clothes image as well
        clothes_img_original = Image.open(io.BytesIO(new_clothes_contents))
        clothes_filename = f"clothes_{original_timestamp}_{new_clothes_image.filename}"
        clothes_path = os.path.join(output_dir, clothes_filename)
        clothes_img_original.save(clothes_path)
        print(f"Saved clothes image to {clothes_path}")

        # Generate a unique filename for processed result
        timestamp = int(time.time())
        output_filename = f"result_{timestamp}.png"
        output_path = os.path.join(output_dir, output_filename)
        final_img.save(output_path)
        print(f"Saved result to {output_path}")

        # Also save metadata about this processed image
        metadata = {
            "id": output_filename,
            "input_filename": original_image.filename,
            "clothes_filename": new_clothes_image.filename,
            "original_filename": original_filename,
            "clothes_original_filename": clothes_filename,
            "operation": "replace-clothes",
            "garment_type": garment_type,
            "timestamp": timestamp,
            "timestamp_formatted": time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(timestamp)),
            "original_path": f"/api/image/{original_filename}",
            "clothes_path": f"/api/image/{clothes_filename}",
            "processed_path": f"/api/image/{output_filename}",
            "api_endpoint": f"/api/image/{output_filename}",
            "user_id": "anonymous_user",  # For public endpoint
            "title": f"Replaced {garment_type} clothes - {original_image.filename}"
        }

        # Save metadata to a JSON file
        metadata_path = os.path.join(output_dir, f"{output_filename}.json")
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f)

        # Create debug images if requested
        debug_images = {}
        if return_debug:
            debug_visuals = create_debug_visuals(
                original_img,
                clothes_img,
                warped_cloth,
                composition_mask,
                final_img
            )
            debug_images = {
                'pipeline_steps': image_to_bytes(debug_visuals['pipeline_steps']),
                'composition_mask': image_to_bytes(debug_visuals['composition_mask'])
            }

        # Apply watermark to final result (with anonymous identifier for public endpoint)
        watermarked_img = add_watermark(final_img, "anonymous_user")

        # Convert final result to bytes
        output_bytes = image_to_bytes(watermarked_img)

        # Prepare response
        response_data = {
            "result_image": output_bytes.getvalue()
        }

        if return_debug:
            response_data["debug_masks"] = debug_images['composition_mask']
            response_data["warp_preview"] = debug_images['pipeline_steps']
            response_data["composition_mask"] = debug_images['composition_mask']

        # Return JSON response with image data
        from fastapi.responses import Response

        # Encode images as base64 for JSON response
        result_base64 = base64.b64encode(response_data["result_image"]).decode('utf-8')

        response_json = {
            "result_image": f"data:image/png;base64,{result_base64}",
            "status": "success",
            "message": "Clothes replacement completed successfully",
            "output_path": output_path,  # Include the output path for verification
            "replacement_quality": replacement_quality  # Include quality metrics
        }

        if return_debug:
            warp_base64 = base64.b64encode(response_data["warp_preview"]).decode('utf-8')
            mask_base64 = base64.b64encode(response_data["composition_mask"]).decode('utf-8')
            response_json.update({
                "debug_masks": f"data:image/png;base64,{mask_base64}",
                "warp_preview": f"data:image/png;base64,{warp_base64}",
                "composition_mask": f"data:image/png;base64,{mask_base64}"
            })

        # If return_cropped is True, create and return a cropped version of just the garment
        if return_cropped:
            print("Creating cropped garment image...")

            # Convert the final image to array for processing
            final_img_array = np.array(final_img)

            # Ensure composition mask is in the right format
            if len(composition_mask.shape) == 3:
                garment_mask_2d = composition_mask[:, :, 0]  # Take first channel
            else:
                garment_mask_2d = composition_mask

            # Find bounding box of the garment area
            coords = np.where(garment_mask_2d > 0.1)  # Use threshold to find garment pixels
            if len(coords[0]) > 0 and len(coords[1]) > 0:  # If garment mask has content
                y_min, y_max = coords[0].min(), coords[0].max()
                x_min, x_max = coords[1].min(), coords[1].max()

                # Add a small padding around the garment
                padding = max(int(0.05 * min(final_img.width, final_img.height)), 5)  # 5% padding or 5px min
                y_min = max(0, y_min - padding)
                y_max = min(final_img_array.shape[0], y_max + padding)
                x_min = max(0, x_min - padding)
                x_max = min(final_img_array.shape[1], x_max + padding)

                # Crop the image to the bounding box
                cropped_img_array = final_img_array[y_min:y_max, x_min:x_max]
                cropped_mask = garment_mask_2d[y_min:y_max, x_min:x_max]

                # Apply the mask to the cropped image to remove background outside the garment
                cropped_mask_3ch = np.stack([cropped_mask] * 3, axis=-1) if len(cropped_mask.shape) == 2 else cropped_mask
                cropped_result = (cropped_img_array * cropped_mask_3ch +
                                 (1 - cropped_mask_3ch) * np.array([255, 255, 255])).astype(np.uint8)  # White background

                # Convert back to PIL Image
                cropped_img = Image.fromarray(cropped_result, 'RGB')

                # Convert to bytes
                cropped_bytes = image_to_bytes(cropped_img)
                cropped_base64 = base64.b64encode(cropped_bytes.getvalue()).decode('utf-8')

                # Add cropped image to response
                response_json["cropped_garment"] = f"data:image/png;base64,{cropped_base64}"
                response_json["message"] = "Clothes replacement completed successfully with cropped garment"

        return response_json

    except Exception as e:
        import traceback
        raise HTTPException(status_code=500, detail=f"Error processing images: {str(e)}\n{traceback.format_exc()}")


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


def generate_precise_shirt_mask(original_img, keypoints, parsing_mask=None, garment_type="top"):
    """
    Generate a highly accurate pixel-level segmentation mask for ONLY the shirt/top.

    This function creates a precise mask that follows the natural contour of the shirt
    excluding face, neck, arms, pants, and background.
    """
    h, w = original_img.height, original_img.width
    precise_mask = np.zeros((h, w), dtype=np.float32)

    # Key point indices for pose estimation
    neck_idx, l_shoulder_idx, r_shoulder_idx = 1, 2, 5
    l_hip_idx, r_hip_idx = 8, 11

    # Extract key points with confidence > 0.1
    neck = keypoints[neck_idx] if neck_idx < len(keypoints) and keypoints[neck_idx][2] > 0.1 else None
    l_shoulder = keypoints[l_shoulder_idx] if l_shoulder_idx < len(keypoints) and keypoints[l_shoulder_idx][2] > 0.1 else None
    r_shoulder = keypoints[r_shoulder_idx] if r_shoulder_idx < len(keypoints) and keypoints[r_shoulder_idx][2] > 0.1 else None
    l_hip = keypoints[l_hip_idx] if l_hip_idx < len(keypoints) and keypoints[l_hip_idx][2] > 0.1 else None
    r_hip = keypoints[r_hip_idx] if r_hip_idx < len(keypoints) and keypoints[r_hip_idx][2] > 0.1 else None

    if neck is not None and l_shoulder is not None and r_shoulder is not None and (l_hip is not None or r_hip is not None):
        # Determine hip position
        if l_hip is not None and r_hip is not None:
            # Use average of both hips
            hip_x = (l_hip[0] + r_hip[0]) / 2
            hip_y = (l_hip[1] + r_hip[1]) / 2
        elif l_hip is not None:
            hip_x, hip_y = l_hip[0], l_hip[1]
        else:  # r_hip is not None
            hip_x, hip_y = r_hip[0], r_hip[1]

        # Create polygon points for torso (shirt area)
        # Start from neck, go to shoulders, then to hips
        points = []
        if neck is not None:
            points.append([int(neck[0]), int(neck[1])])  # Top center (neck)
        if r_shoulder is not None:
            points.append([int(r_shoulder[0]), int(r_shoulder[1])])  # Right shoulder
        if r_hip is not None:
            points.append([int(r_hip[0]), int(r_hip[1])])  # Right hip area
        if l_hip is not None:
            points.append([int(l_hip[0]), int(l_hip[1])])  # Left hip area
        if l_shoulder is not None:
            points.append([int(l_shoulder[0]), int(l_shoulder[1])])  # Left shoulder

        # Convert to numpy array
        if len(points) >= 3:  # Need at least 3 points to form a polygon
            pts = np.array(points, dtype=np.int32)
            # Ensure points are within image bounds
            pts[:, 0] = np.clip(pts[:, 0], 0, w-1)
            pts[:, 1] = np.clip(pts[:, 1], 0, h-1)
            # Draw filled polygon on mask for torso area
            cv2.fillPoly(precise_mask, [pts], 1)

    # Improve mask to exclude face/neck by defining a neck cutoff area
    if neck is not None:
        # Create a neck mask to exclude from the torso mask
        neck_mask = np.zeros((h, w), dtype=np.float32)
        neck_y_cutoff = int(neck[1] - 30)  # Add buffer above the neck
        if neck_y_cutoff > 0:
            neck_mask[:neck_y_cutoff, :] = 1  # Area above neck should be excluded

        # Exclude neck/face area from the torso mask
        precise_mask = np.where(neck_mask > 0.5, 0, precise_mask)

    # Also exclude lower body if we have hip points
    if l_hip is not None or r_hip is not None:
        hip_y_position = None
        if l_hip is not None and r_hip is not None:
            hip_y_position = (l_hip[1] + r_hip[1]) / 2
        elif l_hip is not None:
            hip_y_position = l_hip[1]
        elif r_hip is not None:
            hip_y_position = r_hip[1]

        if hip_y_position is not None:
            # Create lower body mask to exclude from torso
            lower_body_mask = np.zeros((h, w), dtype=np.float32)
            lower_body_start = int(hip_y_position + 20)  # Add buffer below hips
            if lower_body_start < h:
                lower_body_mask[lower_body_start:, :] = 1  # Area below hips should be excluded

            # Exclude lower body from the torso mask
            precise_mask = np.where(lower_body_mask > 0.5, 0, precise_mask)

    # Apply morphological operations to smooth the mask
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
    precise_mask = cv2.morphologyEx(precise_mask, cv2.MORPH_CLOSE, kernel)
    precise_mask = cv2.morphologyEx(precise_mask, cv2.MORPH_OPEN, kernel)

    # Use distance transform to create smooth transitions at edges
    dt = cv2.distanceTransform((1 - precise_mask).astype(np.uint8), cv2.DIST_L2, 3)
    dt = dt / dt.max() if dt.max() > 0 else dt
    dt_mask = 1 - dt  # Invert to have high values in the center of the shirt area

    # Apply Gaussian smoothing for boundary refinement
    dt_smoothed = cv2.GaussianBlur(dt_mask, (5, 5), 0)

    # Threshold to create binary mask (0 or 1)
    final_mask = (dt_smoothed > 0.3).astype(np.float32)  # Adjust threshold as needed

    return final_mask


def refine_shirt_mask_with_parsing(parsing_model, original_img, keypoints, garment_type="top"):
    """
    Generate a precise shirt mask by combining pose-based mask with parsing model results
    """
    # Get the precise mask based on pose estimation
    pose_based_mask = generate_precise_shirt_mask(original_img, keypoints, garment_type=garment_type)

    # Get parsing-based mask if available
    if parsing_model is not None:
        try:
            parsing_map = get_parsing_map_with_enhancement(parsing_model, original_img)
            # Get enhanced garment masks based on the specified garment type
            parsing_masks = get_enhanced_garment_masks(parsing_map, garment_type)

            # Combine with pose-based mask to get the best of both
            if 'top' in parsing_masks:
                parsing_shirt_mask = parsing_masks['top']

                # Combine the masks: use parsing mask where confident, pose mask elsewhere
                combined_mask = np.where(parsing_shirt_mask > 0.7, parsing_shirt_mask,
                                       np.where(pose_based_mask > 0.5, pose_based_mask, 0))

                # Apply additional refinement to ensure clean boundaries
                combined_mask = advanced_garment_mask_refinement(combined_mask, np.array(original_img))

                return combined_mask
        except:
            # If parsing fails, fall back to pose-based mask
            pass

    # If parsing isn't available or fails, return the pose-based mask
    refined_mask = advanced_garment_mask_refinement(pose_based_mask, np.array(original_img))
    return refined_mask


def create_torso_mask(image, keypoints):
    """
    Create a torso-shaped mask based on pose estimation keypoints
    """
    h, w = image.height, image.width

    # Initialize mask
    mask = np.zeros((h, w), dtype=np.uint8)

    # Key point indices
    neck_idx, l_shoulder_idx, r_shoulder_idx, l_hip_idx, r_hip_idx = 1, 2, 5, 8, 11

    # Extract key points with confidence > 0.1
    neck = keypoints[neck_idx] if neck_idx < len(keypoints) and keypoints[neck_idx][2] > 0.1 else None
    l_shoulder = keypoints[l_shoulder_idx] if l_shoulder_idx < len(keypoints) and keypoints[l_shoulder_idx][2] > 0.1 else None
    r_shoulder = keypoints[r_shoulder_idx] if r_shoulder_idx < len(keypoints) and keypoints[r_shoulder_idx][2] > 0.1 else None
    l_hip = keypoints[l_hip_idx] if l_hip_idx < len(keypoints) and keypoints[l_hip_idx][2] > 0.1 else None
    r_hip = keypoints[r_hip_idx] if r_hip_idx < len(keypoints) and keypoints[r_hip_idx][2] > 0.1 else None

    # If we have enough keypoints, create a polygon mask for the torso
    if neck is not None and l_shoulder is not None and r_shoulder is not None and (l_hip is not None or r_hip is not None):
        # Determine hip position
        if l_hip is not None and r_hip is not None:
            # Use average of both hips
            hip_x = (l_hip[0] + r_hip[0]) / 2
            hip_y = (l_hip[1] + r_hip[1]) / 2
        elif l_hip is not None:
            hip_x, hip_y = l_hip[0], l_hip[1]
        else:  # r_hip is not None
            hip_x, hip_y = r_hip[0], r_hip[1]

        # Create polygon points for torso (neck, shoulders, hips)
        points = []
        if neck is not None:
            points.append([int(neck[0]), int(neck[1])])
        if r_shoulder is not None:
            points.append([int(r_shoulder[0]), int(r_shoulder[1])])
        if r_hip is not None:
            points.append([int(r_hip[0]), int(r_hip[1])])
        if l_hip is not None:
            points.append([int(l_hip[0]), int(l_hip[1])])
        if l_shoulder is not None:
            points.append([int(l_shoulder[0]), int(l_shoulder[1])])

        # Convert to numpy array
        if len(points) >= 3:  # Need at least 3 points to form a polygon
            pts = np.array(points, dtype=np.int32)
            # Ensure points are within image bounds
            pts[:, 0] = np.clip(pts[:, 0], 0, w-1)
            pts[:, 1] = np.clip(pts[:, 1], 0, h-1)
            # Draw filled polygon on mask
            cv2.fillPoly(mask, [pts], 1)

    # If we don't have enough keypoints or the polygon creation failed, create a default torso mask
    if np.sum(mask) < 100:  # If the mask is too small
        print("Creating default torso mask based on image proportions")
        # Create a rectangular torso mask using image proportions
        torso_h_start = int(h * 0.25)  # Start from 25% height (neck area)
        torso_h_end = int(h * 0.7)    # End at 70% height (waist area)
        torso_w_start = int(w * 0.25)  # Start at 25% width
        torso_w_end = int(w * 0.75)    # End at 75% width
        mask[torso_h_start:torso_h_end, torso_w_start:torso_w_end] = 1

    # Apply morphological operations to expand the torso mask slightly for better coverage
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (10, 10))
    mask = cv2.dilate(mask, kernel, iterations=1)

    return mask.astype(np.float32)


def create_improved_lower_body_mask(image, keypoints):
    """
    Create an improved lower body mask based on pose estimation keypoints with better coverage
    """
    h, w = image.height, image.width

    # Initialize mask
    mask = np.zeros((h, w), dtype=np.uint8)

    # Key point indices for lower body
    l_hip_idx, r_hip_idx, l_knee_idx, r_knee_idx, l_ankle_idx, r_ankle_idx = 8, 11, 9, 12, 10, 13

    # Extract key points with confidence > 0.1
    l_hip = keypoints[l_hip_idx] if l_hip_idx < len(keypoints) and keypoints[l_hip_idx][2] > 0.1 else None
    r_hip = keypoints[r_hip_idx] if r_hip_idx < len(keypoints) and keypoints[r_hip_idx][2] > 0.1 else None
    l_knee = keypoints[l_knee_idx] if l_knee_idx < len(keypoints) and keypoints[l_knee_idx][2] > 0.1 else None
    r_knee = keypoints[r_knee_idx] if r_knee_idx < len(keypoints) and keypoints[r_knee_idx][2] > 0.1 else None
    l_ankle = keypoints[l_ankle_idx] if l_ankle_idx < len(keypoints) and keypoints[l_ankle_idx][2] > 0.1 else None
    r_ankle = keypoints[r_ankle_idx] if r_ankle_idx < len(keypoints) and keypoints[r_ankle_idx][2] > 0.1 else None

    # Create polygon mask for lower body (hips, knees, ankles)
    points = []
    if l_hip is not None:
        points.append([int(l_hip[0]), int(l_hip[1])])
    if l_knee is not None:
        points.append([int(l_knee[0]), int(l_knee[1])])
    if l_ankle is not None:
        points.append([int(l_ankle[0]), int(l_ankle[1])])
    if r_ankle is not None:
        points.append([int(r_ankle[0]), int(r_ankle[1])])
    if r_knee is not None:
        points.append([int(r_knee[0]), int(r_knee[1])])
    if r_hip is not None:
        points.append([int(r_hip[0]), int(r_hip[1])])

    # Convert to numpy array
    if len(points) >= 3:  # Need at least 3 points to form a polygon
        pts = np.array(points, dtype=np.int32)
        # Ensure points are within image bounds
        pts[:, 0] = np.clip(pts[:, 0], 0, w-1)
        pts[:, 1] = np.clip(pts[:, 1], 0, h-1)
        # Draw filled polygon on mask
        cv2.fillPoly(mask, [pts], 1)

    # If we don't have enough keypoints, create a default lower body mask
    if np.sum(mask) < 100:  # If the mask is too small
        print("Creating default lower body mask based on image proportions")
        # Create a rectangular lower body mask using image proportions
        lower_h_start = int(h * 0.4)  # Start from 40% height (hip area)
        lower_h_end = int(h * 0.95)   # End at 95% height (near ankles)
        lower_w_start = int(w * 0.25)  # Start at 25% width
        lower_w_end = int(w * 0.75)    # End at 75% width
        mask[lower_h_start:lower_h_end, lower_w_start:lower_w_end] = 1

    # Apply morphological operations to expand the lower body mask for better coverage
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (12, 12))
    mask = cv2.dilate(mask, kernel, iterations=1)

    return mask.astype(np.float32)


def create_lower_body_mask(image, keypoints):
    """
    Create a lower body mask based on pose estimation keypoints
    """
    # For backward compatibility, call the improved version
    return create_improved_lower_body_mask(image, keypoints)


def image_to_bytes(image):
    """Helper function to convert PIL image to bytes"""
    output_bytes = io.BytesIO()
    image.save(output_bytes, format="PNG")
    output_bytes.seek(0)
    return output_bytes

@app.post("/api/replace-background")
async def replace_background(
    file: UploadFile = File(..., description="Original image with subject"),
    background_image: UploadFile = File(..., description="Scenery/background image to replace with"),
    current_user: UserInDB = Depends(get_current_user_or_api_key)
):
    """
    Replace background of an image with a custom scenery/background image.

    Args:
        file: Original image file with the subject (PNG, JPG, etc.)
        background_image: Scenery/background image to replace with (PNG, JPG, etc.)

    Returns:
        Image with original subject and new background
    """
    try:
        # Read both uploaded files
        original_contents = await file.read()
        background_contents = await background_image.read()

        # Validate file type for original image
        if not original_contents[:4] in [b'\x89PNG', b'\xFF\xD8\xFF', b'GIF8', b'\x49\x49\x2A\x00', b'\x4D\x4D\x00\x2A', b'\x00\x00\x00\x0C']:
            file_ext = os.path.splitext(file.filename)[1].lower()
            allowed_exts = ['.png', '.jpg', '.jpeg', '.gif', '.bmp', '.tiff', '.webp']
            if file_ext not in allowed_exts:
                raise HTTPException(status_code=400, detail="Invalid file type for original image. Only image files are allowed")

        # Validate file type for background image
        if not background_contents[:4] in [b'\x89PNG', b'\xFF\xD8\xFF', b'GIF8', b'\x49\x49\x2A\x00', b'\x4D\x4D\x00\x2A', b'\x00\x00\x00\x0C']:
            bg_file_ext = os.path.splitext(background_image.filename)[1].lower()
            allowed_exts = ['.png', '.jpg', '.jpeg', '.gif', '.bmp', '.tiff', '.webp']
            if bg_file_ext not in allowed_exts:
                raise HTTPException(status_code=400, detail="Invalid file type for background image. Only image files are allowed")

        # Validate file sizes (max 10MB each)
        if len(original_contents) > 10 * 1024 * 1024:
            raise HTTPException(status_code=400, detail="Original file size exceeds 10MB limit")

        if len(background_contents) > 10 * 1024 * 1024:
            raise HTTPException(status_code=400, detail="Background file size exceeds 10MB limit")

        # Try to open images with PIL to validate they're valid image files
        try:
            original_img_check = Image.open(io.BytesIO(original_contents))
            original_img_check.verify()
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid or corrupted original image file")

        try:
            background_img_check = Image.open(io.BytesIO(background_contents))
            background_img_check.verify()
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid or corrupted background image file")

        # Reopen images after verification
        original_img_after_verify = Image.open(io.BytesIO(original_contents))

        # Remove background from the original image
        foreground_with_transparency = remove(original_contents, session=session)

        # Open both images
        foreground_img = Image.open(io.BytesIO(foreground_with_transparency))
        background_img = Image.open(io.BytesIO(background_contents)).convert("RGB")

        # Ensure foreground has alpha channel for transparency
        if foreground_img.mode != 'RGBA':
            foreground_img = foreground_img.convert('RGBA')

        # Resize background to match foreground if needed
        if foreground_img.size != background_img.size:
            background_img = background_img.resize(foreground_img.size, Image.Resampling.LANCZOS)

        # Create a new image with the background
        result_img = background_img.convert('RGBA')  # Convert to RGBA for proper alpha blending

        # Extract alpha channel as mask for pasting
        if len(foreground_img.split()) >= 4:
            alpha_mask = foreground_img.split()[3]  # Use alpha channel as mask
        else:
            # If no alpha channel exists, create a white mask (full opacity)
            alpha_mask = Image.new('L', foreground_img.size, 255)

        # Paste the foreground image with transparency onto the background
        result_img.paste(foreground_img, (0, 0), mask=alpha_mask)

        # Convert back to RGB before final saving (since background is RGB and subject is now composited)
        result_img = result_img.convert('RGB')

        # Save to the output directory
        output_dir = os.path.join(current_dir, "output")
        os.makedirs(output_dir, exist_ok=True)

        # Save the original uploaded image
        original_img = Image.open(io.BytesIO(original_contents))
        original_timestamp = int(time.time())
        original_filename = f"original_{original_timestamp}_{file.filename}"
        original_path = os.path.join(output_dir, original_filename)
        original_img.save(original_path)
        print(f"Saved original to {original_path}")

        # Generate a unique filename for processed result
        timestamp = int(time.time())
        output_filename = f"result_{timestamp}.png"
        output_path = os.path.join(output_dir, output_filename)
        result_img.save(output_path)
        print(f"Saved result to {output_path}")

        # Save metadata about this processed image
        metadata = {
            "id": output_filename,
            "input_filename": file.filename,
            "original_filename": original_filename,
            "operation": "replace-background",
            "timestamp": timestamp,
            "timestamp_formatted": time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(timestamp)),
            "original_path": f"/api/image/{original_filename}",
            "processed_path": f"/api/image/{output_filename}",
            "api_endpoint": f"/api/image/{output_filename}",
            "user_id": current_user.id,  # Add user ID to track
            "title": f"Replaced background - {file.filename}"
        }

        # Save metadata to a JSON file
        metadata_path = os.path.join(output_dir, f"{output_filename}.json")
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f)

        # Apply watermark with user ID for authenticated endpoint
        watermarked_img = add_watermark(result_img, current_user.id)

        # Save to bytes
        output_bytes = io.BytesIO()
        watermarked_img.save(output_bytes, format="PNG")
        output_bytes.seek(0)

        return StreamingResponse(
            output_bytes,
            media_type="image/png",
            headers={"Content-Disposition": "attachment; filename=background_replaced.png"}
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing images: {str(e)}")


@app.post("/api/public-replace-background")
async def public_replace_background(
    file: UploadFile = File(..., description="Original image with subject"),
    background_image: UploadFile = File(..., description="Scenery/background image to replace with")
):
    """
    Replace background of an image with a custom scenery/background image (public endpoint without authentication).

    Args:
        file: Original image file with the subject (PNG, JPG, etc.)
        background_image: Scenery/background image to replace with (PNG, JPG, etc.)

    Returns:
        Image with original subject and new background
    """
    try:
        # Read both uploaded files
        original_contents = await file.read()
        background_contents = await background_image.read()

        # Validate file type for original image
        if not original_contents[:4] in [b'\x89PNG', b'\xFF\xD8\xFF', b'GIF8', b'\x49\x49\x2A\x00', b'\x4D\x4D\x00\x2A', b'\x00\x00\x00\x0C']:
            file_ext = os.path.splitext(file.filename)[1].lower()
            allowed_exts = ['.png', '.jpg', '.jpeg', '.gif', '.bmp', '.tiff', '.webp']
            if file_ext not in allowed_exts:
                raise HTTPException(status_code=400, detail="Invalid file type for original image. Only image files are allowed")

        # Validate file type for background image
        if not background_contents[:4] in [b'\x89PNG', b'\xFF\xD8\xFF', b'GIF8', b'\x49\x49\x2A\x00', b'\x4D\x4D\x00\x2A', b'\x00\x00\x00\x0C']:
            bg_file_ext = os.path.splitext(background_image.filename)[1].lower()
            allowed_exts = ['.png', '.jpg', '.jpeg', '.gif', '.bmp', '.tiff', '.webp']
            if bg_file_ext not in allowed_exts:
                raise HTTPException(status_code=400, detail="Invalid file type for background image. Only image files are allowed")

        # Validate file sizes (max 10MB each)
        if len(original_contents) > 10 * 1024 * 1024:
            raise HTTPException(status_code=400, detail="Original file size exceeds 10MB limit")

        if len(background_contents) > 10 * 1024 * 1024:
            raise HTTPException(status_code=400, detail="Background file size exceeds 10MB limit")

        # Try to open images with PIL to validate they're valid image files
        try:
            original_img_check = Image.open(io.BytesIO(original_contents))
            original_img_check.verify()
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid or corrupted original image file")

        try:
            background_img_check = Image.open(io.BytesIO(background_contents))
            background_img_check.verify()
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid or corrupted background image file")

        # Reopen images after verification
        original_img_after_verify = Image.open(io.BytesIO(original_contents))

        # Remove background from the original image
        foreground_with_transparency = remove(original_contents, session=session)

        # Open both images
        foreground_img = Image.open(io.BytesIO(foreground_with_transparency))
        background_img = Image.open(io.BytesIO(background_contents)).convert("RGB")

        # Ensure foreground has alpha channel for transparency
        if foreground_img.mode != 'RGBA':
            foreground_img = foreground_img.convert('RGBA')

        # Resize background to match foreground if needed
        if foreground_img.size != background_img.size:
            background_img = background_img.resize(foreground_img.size, Image.Resampling.LANCZOS)

        # Create a new image with the background
        result_img = background_img.convert('RGBA')  # Convert to RGBA for proper alpha blending

        # Extract alpha channel as mask for pasting
        if len(foreground_img.split()) >= 4:
            alpha_mask = foreground_img.split()[3]  # Use alpha channel as mask
        else:
            # If no alpha channel exists, create a white mask (full opacity)
            alpha_mask = Image.new('L', foreground_img.size, 255)

        # Paste the foreground image with transparency onto the background
        result_img.paste(foreground_img, (0, 0), mask=alpha_mask)

        # Convert back to RGB before final saving (since background is RGB and subject is now composited)
        result_img = result_img.convert('RGB')

        # Apply watermark with anonymous identifier for public endpoint
        watermarked_img = add_watermark(result_img, "anonymous_user")

        # Save to bytes
        output_bytes = io.BytesIO()
        watermarked_img.save(output_bytes, format="PNG")
        output_bytes.seek(0)

        return StreamingResponse(
            output_bytes,
            media_type="image/png",
            headers={"Content-Disposition": "attachment; filename=background_replaced.png"}
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing images: {str(e)}")


# Authentication endpoints
@app.post("/auth/refresh")
async def refresh_token(request: RefreshTokenRequest):
    """Refresh access token using refresh token"""
    if not is_refresh_token_valid(request.refresh_token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Decode the refresh token to get user info
    try:
        payload = jwt.decode(request.refresh_token, SECRET_KEY, algorithms=[ALGORITHM])
        token_type = payload.get("type")
        if token_type != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type",
                headers={"WWW-Authenticate": "Bearer"},
            )

        email: str = payload.get("sub")
        if email is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Get user
    user = get_user(email=email)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Invalidate the old refresh token
    invalidate_refresh_token(request.refresh_token)

    # Create new tokens
    auth_response = create_auth_response(user)

    return {
        "access_token": auth_response.access_token,
        "refresh_token": auth_response.refresh_token,
        "token_type": auth_response.token_type
    }


@app.post("/auth/register")
async def register(user_data: UserRegister):
    """Register a new user"""
    try:
        user = create_user(user_data)
        # Create authentication response for auto-login after registration
        auth_response = create_auth_response(user)

        return {
            "message": "User registered successfully",
            "access_token": auth_response.access_token,
            "refresh_token": auth_response.refresh_token,
            "token_type": auth_response.token_type,
            "user": {
                "id": user.id,
                "email": user.email,
                "first_name": user.first_name,
                "last_name": user.last_name
            }
        }
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Registration failed: {str(e)}")


@app.post("/auth/login")
async def login(user_data: UserLogin):
    """Login user and return access and refresh tokens"""
    user = authenticate_user(user_data.email, user_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Create authentication response with both tokens
    auth_response = create_auth_response(user)

    return {
        "access_token": auth_response.access_token,
        "refresh_token": auth_response.refresh_token,
        "token_type": auth_response.token_type,
        "user": {
            "id": user.id,
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "is_pro": user.is_pro
        }
    }


@app.post("/auth/logout")
async def logout(authorization: HTTPAuthorizationCredentials = Depends(security)):
    """Logout user by invalidating refresh token"""
    try:
        # Extract token from authorization header
        token = authorization.credentials

        # Try to decode the token to check if it's an access token
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            token_type = payload.get("type")

            # If it's an access token, we can't directly invalidate it (it will expire)
            # But we can clear any associated refresh tokens if needed
            if token_type == "access":
                # For enhanced security, you might want to maintain a blacklist of access tokens
                pass
        except jwt.PyJWTError:
            pass

        return {"message": "Successfully logged out"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Logout failed: {str(e)}")


@app.get("/auth/me")
async def read_users_me(current_user: UserInDB = Depends(get_current_user)):
    """Get current user info"""
    return {
        "id": current_user.id,
        "email": current_user.email,
        "first_name": current_user.first_name,
        "last_name": current_user.last_name,
        "bio": current_user.bio,
        "profile_image": current_user.profile_image,
        "is_pro": current_user.is_pro,
        "subscription_end": current_user.subscription_end
    }


from pydantic import BaseModel

class ProfileUpdateRequest(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    bio: Optional[str] = None

@app.put("/auth/update_profile")
async def update_profile(
    profile_data: ProfileUpdateRequest,
    current_user: UserInDB = Depends(get_current_user)
):
    """Update user profile information"""
    try:
        success = update_user_profile(
            email=current_user.email,
            first_name=profile_data.first_name,
            last_name=profile_data.last_name,
            bio=profile_data.bio
        )

        if success:
            # Return updated user data
            updated_user = get_user(current_user.email)
            return {
                "message": "Profile updated successfully",
                "user": {
                    "id": updated_user.id,
                    "email": updated_user.email,
                    "first_name": updated_user.first_name or '',
                    "last_name": updated_user.last_name or '',
                    "bio": updated_user.bio or '',
                    "profile_image": updated_user.profile_image or '',
                    "is_pro": updated_user.is_pro,
                    "subscription_end": updated_user.subscription_end
                }
            }
        else:
            raise HTTPException(status_code=400, detail="Failed to update profile")
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Profile update failed: {str(e)}")


@app.post("/auth/upload_profile_image")
async def upload_profile_image(
    profile_image: UploadFile = File(...),
    current_user: UserInDB = Depends(get_current_user)
):
    """Upload and update user profile image"""
    try:
        # Validate file type
        if not profile_image.content_type.startswith("image/"):
            raise HTTPException(status_code=400, detail="File must be an image")

        # Validate file size (limit to 5MB)
        # Note: We need to be careful with file size validation as the file is already in memory
        # In a production app, we would validate before reading the contents
        contents = await profile_image.read()
        if len(contents) > 5 * 1024 * 1024:  # 5MB limit
            raise HTTPException(status_code=400, detail="File size exceeds 5MB limit")

        # Sanitize the filename to extract extension safely
        filename = profile_image.filename
        file_extension = os.path.splitext(filename)[1].lower()

        # Ensure the extension is valid
        if file_extension not in ['.jpg', '.jpeg', '.png', '.gif', '.webp']:
            raise HTTPException(status_code=400, detail="Invalid file type. Only JPG, PNG, GIF, and WebP are allowed")

        # Use the same uploads directory as defined for static files
        base_uploads_dir = os.path.join(os.path.dirname(__file__), "uploads")

        # Ensure upload directory exists
        os.makedirs(base_uploads_dir, exist_ok=True)

        # Generate unique filename
        unique_filename = f"{uuid.uuid4()}{file_extension}"
        file_path = os.path.join(base_uploads_dir, unique_filename)

        # Save file
        with open(file_path, "wb") as f:
            f.write(contents)

        # Generate URL for the uploaded image
        # Using relative path that will be served by the mounted static files
        image_url = f"/uploads/{unique_filename}"

        success = update_user_profile_image(
            email=current_user.email,
            profile_image_url=image_url
        )

        if success:
            # Return updated user data like the update_profile endpoint
            updated_user = get_user(current_user.email)
            return {
                "message": "Profile image updated successfully",
                "profile_image": image_url,
                "user": {
                    "id": updated_user.id,
                    "email": updated_user.email,
                    "first_name": updated_user.first_name or '',
                    "last_name": updated_user.last_name or '',
                    "bio": updated_user.bio or '',
                    "profile_image": updated_user.profile_image or '',
                    "is_pro": updated_user.is_pro,
                    "subscription_end": updated_user.subscription_end
                }
            }
        else:
            raise HTTPException(status_code=400, detail="Failed to update profile image")
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Profile image update failed: {str(e)}")


# Payment endpoints
@app.post("/payment/create-intent")
async def create_payment(
    payment_data: PaymentIntentCreate,
    current_user: UserInDB = Depends(get_current_user)
):
    """Create a payment intent for $1 pro membership"""
    try:
        # For pro membership, set amount to $1 (100 cents)
        if payment_data.description.lower().find("pro") != -1:
            payment_data.amount = 100  # $1.00 in cents

        intent_data = create_payment_intent(payment_data)
        return intent_data
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Payment creation failed: {str(e)}")


@app.post("/payment/subscription")
async def create_pro_subscription(
    subscription_data: SubscriptionCreate,
    current_user: UserInDB = Depends(get_current_user)
):
    """Create a pro subscription ($1)"""
    try:
        # Verify this is the pro plan (for $1)
        # In a real implementation, you would validate the price_id is for the pro plan
        subscription = create_subscription(subscription_data)

        # Update user in database to mark as pro
        # Calculate subscription end date (e.g. 30 days for demo)
        subscription_end = datetime.utcnow() + timedelta(days=30)
        update_user_subscription(current_user.email, True, subscription_end)

        return subscription
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Subscription creation failed: {str(e)}")


@app.get("/payment/verify/{payment_id}")
async def verify_payment(
    payment_id: str,
    current_user: UserInDB = Depends(get_current_user)
):
    """Verify payment status"""
    try:
        status_data = verify_payment_status(payment_id)
        return status_data
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Payment verification failed: {str(e)}")


# Update image processing endpoints to check for pro status
@app.post("/api/remove-background")
async def remove_background(
    file: UploadFile = File(...),
    current_user: UserInDB = Depends(get_current_user_or_api_key)
):
    """
    Remove background from an image. Pro users have higher limits.
    """
    # Check if user is pro and adjust limits accordingly
    max_size = 10 * 1024 * 1024 if current_user.is_pro else 5 * 1024 * 1024  # 10MB for pro, 5MB for free

    try:
        # Read the uploaded file
        contents = await file.read()

        # Validate file type by checking file signature
        if not contents[:4] in [b'\x89PNG', b'\xFF\xD8\xFF', b'GIF8', b'\x49\x49\x2A\x00', b'\x4D\x4D\x00\x2A', b'\x00\x00\x00\x0C']:
            # Not perfect but checks for common image formats: PNG, JPEG, GIF, TIFF, etc.
            # Use file extension as backup check as well
            file_ext = os.path.splitext(file.filename)[1].lower()
            allowed_exts = ['.png', '.jpg', '.jpeg', '.gif', '.bmp', '.tiff', '.webp']
            if file_ext not in allowed_exts:
                raise HTTPException(status_code=400, detail="Invalid file type. Only image files are allowed")

        # Validate file size
        if len(contents) > max_size:
            size_mb = max_size / (1024 * 1024)
            raise HTTPException(status_code=400, detail=f"File size exceeds {size_mb}MB limit")

        # Try to open image with PIL to validate it's a valid image file
        try:
            img = Image.open(io.BytesIO(contents))
            img.verify()  # Verify that it's a valid image
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid or corrupted image file")

        # Reopen image after verification
        img = Image.open(io.BytesIO(contents))

        # Process image with rembg
        output = remove(contents, session=session)

        # Open the result image to save to disk
        result_img = Image.open(io.BytesIO(output))

        # Save to the output directory
        output_dir = os.path.join(current_dir, "output")
        os.makedirs(output_dir, exist_ok=True)

        # Save the original uploaded image
        original_img = Image.open(io.BytesIO(contents))
        original_timestamp = int(time.time())
        original_filename = f"original_{original_timestamp}_{file.filename}"
        original_path = os.path.join(output_dir, original_filename)
        original_img.save(original_path)
        print(f"Saved original to {original_path}")

        # Generate a unique filename for processed result
        timestamp = int(time.time())
        output_filename = f"result_{timestamp}.png"
        output_path = os.path.join(output_dir, output_filename)
        result_img.save(output_path, format="PNG")
        print(f"Saved result to {output_path}")

        # Save metadata about this processed image
        metadata = {
            "id": output_filename,
            "input_filename": file.filename,
            "original_filename": original_filename,
            "operation": "remove-background",
            "timestamp": timestamp,
            "timestamp_formatted": time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(timestamp)),
            "original_path": f"/api/image/{original_filename}",
            "processed_path": f"/api/image/{output_filename}",
            "api_endpoint": f"/api/image/{output_filename}",
            "user_id": current_user.id,  # Add user ID to track
            "title": f"Removed background - {file.filename}"
        }

        # Save metadata to a JSON file
        metadata_path = os.path.join(output_dir, f"{output_filename}.json")
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f)

        # Add watermark with user ID for authenticated endpoint
        img_with_transparency = Image.open(io.BytesIO(output)).convert("RGBA")
        img_rgb = img_with_transparency.convert("RGB")
        watermarked_img = add_watermark(img_rgb, current_user.id)

        # Also save the watermarked version to disk
        watermarked_path = os.path.join(output_dir, f"result_{timestamp}_watermarked.png")
        watermarked_img.save(watermarked_path, format="PNG")

        # Return watermarked image as PNG
        output_bytes = io.BytesIO()
        watermarked_img.save(output_bytes, format="PNG")
        output_bytes.seek(0)

        return StreamingResponse(
            output_bytes,
            media_type="image/png",
            headers={"Content-Disposition": "attachment; filename=output.png"}
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing image: {str(e)}")


@app.post("/api/public-remove-background-full")
async def public_remove_background_full(
    file: UploadFile = File(...),
):
    """
    Remove background from an image. No authentication required.
    """
    # Fixed limit for public endpoint (5MB)
    max_size = 5 * 1024 * 1024  # 5MB for public users

    try:
        # Read the uploaded file
        contents = await file.read()

        # Validate file type by checking file signature
        if not contents[:4] in [b'\x89PNG', b'\xFF\xD8\xFF', b'GIF8', b'\x49\x49\x2A\x00', b'\x4D\x4D\x00\x2A', b'\x00\x00\x00\x0C']:
            # Not perfect but checks for common image formats: PNG, JPEG, GIF, TIFF, etc.
            # Use file extension as backup check as well
            file_ext = os.path.splitext(file.filename)[1].lower()
            allowed_exts = ['.png', '.jpg', '.jpeg', '.gif', '.bmp', '.tiff', '.webp']
            if file_ext not in allowed_exts:
                raise HTTPException(status_code=400, detail="Invalid file type. Only image files are allowed")

        # Validate file size
        if len(contents) > max_size:
            size_mb = max_size / (1024 * 1024)
            raise HTTPException(status_code=400, detail=f"File size exceeds {size_mb}MB limit")

        # Try to open image with PIL to validate it's a valid image file
        try:
            img = Image.open(io.BytesIO(contents))
            img.verify()  # Verify that it's a valid image
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid or corrupted image file")

        # Reopen image after verification
        img = Image.open(io.BytesIO(contents))

        # Process image with rembg
        output = remove(contents, session=session)

        # Open the result image
        result_img = Image.open(io.BytesIO(output))

        # Save to the output directory
        output_dir = os.path.join(current_dir, "output")
        os.makedirs(output_dir, exist_ok=True)

        # Save the original uploaded image
        original_img = Image.open(io.BytesIO(contents))
        original_timestamp = int(time.time())
        original_filename = f"original_{original_timestamp}_{file.filename}"
        original_path = os.path.join(output_dir, original_filename)
        original_img.save(original_path)
        print(f"Saved original to {original_path}")

        # Generate a unique filename for processed result
        timestamp = int(time.time())
        output_filename = f"result_{timestamp}.png"
        output_path = os.path.join(output_dir, output_filename)
        result_img.save(output_path, format="PNG")
        print(f"Saved result to {output_path}")

        # Save metadata about this processed image (using anonymous user ID)
        metadata = {
            "id": output_filename,
            "input_filename": file.filename,
            "original_filename": original_filename,
            "operation": "remove-background",
            "timestamp": timestamp,
            "timestamp_formatted": time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(timestamp)),
            "original_path": f"/api/image/{original_filename}",
            "processed_path": f"/api/image/{output_filename}",
            "api_endpoint": f"/api/image/{output_filename}",
            "user_id": "anonymous",  # Anonymous user ID for public endpoint
            "title": f"Removed background - {file.filename}"
        }

        # Save metadata to a JSON file
        metadata_path = os.path.join(output_dir, f"{output_filename}.json")
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f)

        # Add watermark with anonymous identifier for public endpoint
        img_with_transparency = Image.open(io.BytesIO(output)).convert("RGBA")
        img_rgb = img_with_transparency.convert("RGB")
        watermarked_img = add_watermark(img_rgb, "anonymous_user")

        # Also save the watermarked version to disk
        watermarked_path = os.path.join(output_dir, f"result_{timestamp}_watermarked.png")
        watermarked_img.save(watermarked_path, format="PNG")

        # Return watermarked image as PNG
        output_bytes = io.BytesIO()
        watermarked_img.save(output_bytes, format="PNG")
        output_bytes.seek(0)

        return StreamingResponse(
            output_bytes,
            media_type="image/png",
            headers={"Content-Disposition": "attachment; filename=output.png"}
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing image: {str(e)}")


@app.post("/api/change-background")
async def change_background(
    file: UploadFile = File(...),
    bg_color: Optional[str] = Form(None),  # Explicitly define as form field
    bg_color_query: Optional[str] = Query(None),  # Also accept as query param as backup
    quality: Optional[str] = Form("high"),  # Quality parameter: low, medium, high
    current_user: UserInDB = Depends(get_current_user_or_api_key)
):
    """
    Change background color in an image.
    First removes the background, then applies a new background color.

    Args:
        file: Image file (PNG, JPG, etc.)
        bg_color: Background color in hex format (default: "FFFFFF" for white)

    Returns:
        Image with new background color
    """
    # Check if user is pro and adjust limits accordingly
    max_size = 10 * 1024 * 1024 if current_user.is_pro else 5 * 1024 * 1024  # 10MB for pro, 5MB for free

    try:
        # Read the uploaded file
        contents = await file.read()

        # Validate file type by checking file signature
        if not contents[:4] in [b'\x89PNG', b'\xFF\xD8\xFF', b'GIF8', b'\x49\x49\x2A\x00', b'\x4D\x4D\x00\x2A', b'\x00\x00\x00\x0C']:
            # Not perfect but checks for common image formats: PNG, JPEG, GIF, TIFF, etc.
            # Use file extension as backup check as well
            file_ext = os.path.splitext(file.filename)[1].lower()
            allowed_exts = ['.png', '.jpg', '.jpeg', '.gif', '.bmp', '.tiff', '.webp']
            if file_ext not in allowed_exts:
                raise HTTPException(status_code=400, detail="Invalid file type. Only image files are allowed")

        # Validate file size
        if len(contents) > max_size:
            size_mb = max_size / (1024 * 1024)
            raise HTTPException(status_code=400, detail=f"File size exceeds {size_mb}MB limit")

        # Try to open image with PIL to validate it's a valid image file
        try:
            img = Image.open(io.BytesIO(contents))
            img.verify()  # Verify that it's a valid image
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid or corrupted image file")

        # Reopen image after verification
        img = Image.open(io.BytesIO(contents))

        print(f"DEBUG: Raw bg_color (form) parameter received: {repr(bg_color)}")  # Debug
        print(f"DEBUG: Raw bg_color_query (query) parameter received: {repr(bg_color_query)}")  # Debug

        # Parse background color from form data first, then query parameter as backup
        if bg_color is None or bg_color == "" or (isinstance(bg_color, str) and bg_color.strip() == ""):
            if bg_color_query is not None and bg_color_query != "" and not (isinstance(bg_color_query, str) and bg_color_query.strip() == ""):
                bg_hex = bg_color_query  # Use query parameter if form field is empty
                print(f"DEBUG: Using color from query parameter: {repr(bg_hex)}")  # Debug
            else:
                bg_hex = "FFFFFF"  # Default to white if both are empty
                print(f"DEBUG: Using default white because both form and query parameters were empty")  # Debug
        else:
            bg_hex = bg_color  # Use form parameter
            print(f"DEBUG: Using color from form parameter: {repr(bg_hex)}")  # Debug

        print(f"DEBUG: bg_hex after applying default: {repr(bg_hex)}")  # Debug

        # Ensure hex format is correct (remove any # and ensure 6 characters)
        bg_hex = bg_hex.replace('#', '')
        print(f"DEBUG: bg_hex after removing #: {repr(bg_hex)}")  # Debug

        if len(bg_hex) != 6:
            # If it's a shorter format like 'FFF', expand it to 'FFFFFF'
            if len(bg_hex) == 3:
                bg_hex = ''.join([c*2 for c in bg_hex])
                print(f"DEBUG: bg_hex after expanding 3-digit: {repr(bg_hex)}")  # Debug
            else:
                raise HTTPException(status_code=400, detail="bg_color must be 6-character hex value")

        try:
            bg_rgb = tuple(int(bg_hex[i:i+2], 16) for i in (0, 2, 4))
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid hex color format")

        print(f"Processing background change with color: #{bg_hex} -> RGB{bg_rgb}")
        print(f"DEBUG: Creating background with RGB: {bg_rgb}")  # More debug info

        # Remove background first
        removed_bg = remove(contents, session=session)

        # Open the image with transparent background
        img_with_transparency = Image.open(io.BytesIO(removed_bg)).convert("RGBA")
        print(f"DEBUG: Image converted to RGBA, size: {img_with_transparency.size}")  # Debug

        # Create new background image with specified color
        background = Image.new("RGB", img_with_transparency.size, bg_rgb)
        print(f"DEBUG: Created background with color {bg_rgb}, verifying: {background.getpixel((0,0))}")  # Debug

        # Get the alpha channel to use as mask for compositing
        alpha_channel = img_with_transparency.split()[-1]  # Get the alpha channel (usually the 4th channel in RGBA)
        print(f"DEBUG: Alpha channel type: {type(alpha_channel)}, mode: {alpha_channel.mode}, size: {alpha_channel.size}")  # Debug

        # Use PIL's Image.alpha_composite for proper alpha blending
        # Create an RGBA version of the solid color background
        bg_rgba = Image.new("RGBA", img_with_transparency.size, bg_rgb + (255,))  # Add alpha of 255 (opaque)

        # Composite the transparent image onto the colored background
        composited = Image.alpha_composite(bg_rgba, img_with_transparency)

        # Convert back to RGB since that's what we want to return
        background = composited.convert("RGB")
        print(f"DEBUG: After alpha compositing, corner pixel is: {background.getpixel((0,0))}")  # Verify result

        # Save to the output directory
        output_dir = os.path.join(current_dir, "output")
        os.makedirs(output_dir, exist_ok=True)

        # Save the original uploaded image
        original_img = Image.open(io.BytesIO(contents))
        original_timestamp = int(time.time())
        original_filename = f"original_{original_timestamp}_{file.filename}"
        original_path = os.path.join(output_dir, original_filename)
        original_img.save(original_path)
        print(f"Saved original to {original_path}")

        # Generate a unique filename for processed result
        timestamp = int(time.time())
        output_filename = f"result_{timestamp}_bg_changed_{bg_hex}.png"
        output_path = os.path.join(output_dir, output_filename)
        background.save(output_path)
        print(f"Saved result to {output_path}")

        # Save metadata about this processed image
        metadata = {
            "id": output_filename,
            "input_filename": file.filename,
            "original_filename": original_filename,
            "operation": "change-background",
            "bg_color": f"#{bg_hex}",
            "timestamp": timestamp,
            "timestamp_formatted": time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(timestamp)),
            "original_path": f"/api/image/{original_filename}",
            "processed_path": f"/api/image/{output_filename}",
            "api_endpoint": f"/api/image/{output_filename}",
            "user_id": current_user.id,  # Add user ID to track
            "title": f"Changed background to #{bg_hex} - {file.filename}"
        }

        # Save metadata to a JSON file
        metadata_path = os.path.join(output_dir, f"{output_filename}.json")
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f)

        # Add a unique watermark to the image
        watermarked_image = add_watermark(background, current_user.id if current_user else "anonymous")

        # Verify the background color before saving
        corner_pixel = watermarked_image.getpixel((0,0))
        print(f"DEBUG: Before saving, corner pixel is: {corner_pixel}, expected was: {bg_rgb}")

        # Save to bytes
        output_bytes = io.BytesIO()
        watermarked_image.save(output_bytes, format="PNG")
        output_bytes.seek(0)

        # Verify after reloading from bytes
        output_bytes.seek(0)
        test_image = Image.open(output_bytes)
        corner_pixel_after = test_image.getpixel((0,0))
        print(f"DEBUG: After saving/reloading, corner pixel is: {corner_pixel_after}")
        output_bytes.seek(0)

        return StreamingResponse(
            output_bytes,
            media_type="image/png",
            headers={"Content-Disposition": "attachment; filename=bg_changed.png"}
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing image: {str(e)}")


@app.post("/api/public-change-background-full")
async def public_change_background_full(
    file: UploadFile = File(...),
    bg_color: Optional[str] = Form(None),  # Explicitly define as form field
    bg_color_query: Optional[str] = Query(None),  # Also accept as query param as backup
    quality: Optional[str] = Form("high")  # Quality parameter: low, medium, high
):
    """
    Change background color in an image. No authentication required.
    First removes the background, then applies a new background color.

    Args:
        file: Image file (PNG, JPG, etc.)
        bg_color: Background color in hex format (default: "FFFFFF" for white)

    Returns:
        Image with new background color
    """
    # Fixed limit for public endpoint (5MB)
    max_size = 5 * 1024 * 1024  # 5MB for public users

    try:
        # Read the uploaded file
        contents = await file.read()

        # Validate file type by checking file signature
        if not contents[:4] in [b'\x89PNG', b'\xFF\xD8\xFF', b'GIF8', b'\x49\x49\x2A\x00', b'\x4D\x4D\x00\x2A', b'\x00\x00\x00\x0C']:
            # Not perfect but checks for common image formats: PNG, JPEG, GIF, TIFF, etc.
            # Use file extension as backup check as well
            file_ext = os.path.splitext(file.filename)[1].lower()
            allowed_exts = ['.png', '.jpg', '.jpeg', '.gif', '.bmp', '.tiff', '.webp']
            if file_ext not in allowed_exts:
                raise HTTPException(status_code=400, detail="Invalid file type. Only image files are allowed")

        # Validate file size
        if len(contents) > max_size:
            size_mb = max_size / (1024 * 1024)
            raise HTTPException(status_code=400, detail=f"File size exceeds {size_mb}MB limit")

        # Try to open image with PIL to validate it's a valid image file
        try:
            img = Image.open(io.BytesIO(contents))
            img.verify()  # Verify that it's a valid image
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid or corrupted image file")

        # Reopen image after verification
        img = Image.open(io.BytesIO(contents))

        print(f"DEBUG: Raw bg_color (form) parameter received: {repr(bg_color)}")  # Debug
        print(f"DEBUG: Raw bg_color_query (query) parameter received: {repr(bg_color_query)}")  # Debug

        # Parse background color from form data first, then query parameter as backup
        if bg_color is None or bg_color == "" or (isinstance(bg_color, str) and bg_color.strip() == ""):
            if bg_color_query is not None and bg_color_query != "" and not (isinstance(bg_color_query, str) and bg_color_query.strip() == ""):
                bg_hex = bg_color_query  # Use query parameter if form field is empty
                print(f"DEBUG: Using color from query parameter: {repr(bg_hex)}")  # Debug
            else:
                bg_hex = "FFFFFF"  # Default to white if both are empty
                print(f"DEBUG: Using default white because both form and query parameters were empty")  # Debug
        else:
            bg_hex = bg_color  # Use form parameter
            print(f"DEBUG: Using color from form parameter: {repr(bg_hex)}")  # Debug

        print(f"DEBUG: bg_hex after applying default: {repr(bg_hex)}")  # Debug

        # Ensure hex format is correct (remove any # and ensure 6 characters)
        bg_hex = bg_hex.replace('#', '')
        print(f"DEBUG: bg_hex after removing #: {repr(bg_hex)}")  # Debug

        if len(bg_hex) != 6:
            # If it's a shorter format like 'FFF', expand it to 'FFFFFF'
            if len(bg_hex) == 3:
                bg_hex = ''.join([c*2 for c in bg_hex])
                print(f"DEBUG: bg_hex after expanding 3-digit: {repr(bg_hex)}")  # Debug
            else:
                raise HTTPException(status_code=400, detail="bg_color must be 6-character hex value")

        try:
            bg_rgb = tuple(int(bg_hex[i:i+2], 16) for i in (0, 2, 4))
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid hex color format")

        print(f"Processing background change with color: #{bg_hex} -> RGB{bg_rgb}")
        print(f"DEBUG: Creating background with RGB: {bg_rgb}")  # More debug info

        # Remove background first
        removed_bg = remove(contents, session=session)

        # Open the image with transparent background
        img_with_transparency = Image.open(io.BytesIO(removed_bg)).convert("RGBA")
        print(f"DEBUG: Image converted to RGBA, size: {img_with_transparency.size}")  # Debug

        # Create new background image with specified color
        background = Image.new("RGB", img_with_transparency.size, bg_rgb)
        print(f"DEBUG: Created background with color {bg_rgb}, verifying: {background.getpixel((0,0))}")  # Debug

        # Get the alpha channel to use as mask for compositing
        alpha_channel = img_with_transparency.split()[-1]  # Get the alpha channel (usually the 4th channel in RGBA)
        print(f"DEBUG: Alpha channel type: {type(alpha_channel)}, mode: {alpha_channel.mode}, size: {alpha_channel.size}")  # Debug

        # Use PIL's Image.alpha_composite for proper alpha blending
        # Create an RGBA version of the solid color background
        bg_rgba = Image.new("RGBA", img_with_transparency.size, bg_rgb + (255,))  # Add alpha of 255 (opaque)

        # Composite the transparent image onto the colored background
        composited = Image.alpha_composite(bg_rgba, img_with_transparency)

        # Convert back to RGB since that's what we want to return
        background = composited.convert("RGB")
        print(f"DEBUG: After alpha compositing, corner pixel is: {background.getpixel((0,0))}")  # Verify result

        # Save to the output directory
        output_dir = os.path.join(current_dir, "output")
        os.makedirs(output_dir, exist_ok=True)

        # Save the original uploaded image
        original_img = Image.open(io.BytesIO(contents))
        original_timestamp = int(time.time())
        original_filename = f"original_{original_timestamp}_{file.filename}"
        original_path = os.path.join(output_dir, original_filename)
        original_img.save(original_path)
        print(f"Saved original to {original_path}")

        # Generate a unique filename for processed result
        timestamp = int(time.time())
        output_filename = f"result_{timestamp}_bg_changed_{bg_hex}.png"
        output_path = os.path.join(output_dir, output_filename)
        background.save(output_path)
        print(f"Saved result to {output_path}")

        # Save metadata about this processed image (using anonymous user ID)
        metadata = {
            "id": output_filename,
            "input_filename": file.filename,
            "original_filename": original_filename,
            "operation": "change-background",
            "bg_color": f"#{bg_hex}",
            "timestamp": timestamp,
            "timestamp_formatted": time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(timestamp)),
            "original_path": f"/api/image/{original_filename}",
            "processed_path": f"/api/image/{output_filename}",
            "api_endpoint": f"/api/image/{output_filename}",
            "user_id": "anonymous",  # Anonymous user ID for public endpoint
            "title": f"Changed background to #{bg_hex} - {file.filename}"
        }

        # Save metadata to a JSON file
        metadata_path = os.path.join(output_dir, f"{output_filename}.json")
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f)

        # Add a unique watermark with anonymous identifier for public endpoint
        watermarked_image = add_watermark(background, "anonymous_user")

        # Verify the background color before saving
        corner_pixel = watermarked_image.getpixel((0,0))
        print(f"DEBUG: Before saving, corner pixel is: {corner_pixel}, expected was: {bg_rgb}")

        # Save to bytes
        output_bytes = io.BytesIO()
        watermarked_image.save(output_bytes, format="PNG")
        output_bytes.seek(0)

        # Verify after reloading from bytes
        output_bytes.seek(0)
        test_image = Image.open(output_bytes)
        corner_pixel_after = test_image.getpixel((0,0))
        print(f"DEBUG: After saving/reloading, corner pixel is: {corner_pixel_after}")
        output_bytes.seek(0)

        return StreamingResponse(
            output_bytes,
            media_type="image/png",
            headers={"Content-Disposition": "attachment; filename=bg_changed.png"}
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing image: {str(e)}")


# Stripe checkout session endpoint
@app.post("/create-checkout-session")
async def create_checkout_session(
    current_user: UserInDB = Depends(get_current_user)
):
    """Create a Stripe checkout session for pro subscription"""
    try:
        # Create a checkout session using the Stripe library
        # This creates a payment session for $1 for the pro subscription
        session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            mode='payment',
            line_items=[{
                'price_data': {
                    'currency': 'usd',
                    'product_data': {
                        'name': 'Pro Membership',
                        'description': 'Access to premium image processing features'
                    },
                    'unit_amount': 100,  # $1.00 in cents
                },
                'quantity': 1,
            }],
            success_url=f"{os.getenv('FRONTEND_URL', 'https://hintergrundentfernen.ai')}/account?success=true",
            cancel_url=f"{os.getenv('FRONTEND_URL', 'https://hintergrundentfernen.ai')}/account?canceled=true",
            customer_email=current_user.email,
        )

        return {"id": session.id, "url": session.url}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Checkout session creation failed: {str(e)}")


# API Key endpoints
@app.post("/api/keys", dependencies=[Depends(get_current_user)])
async def create_api_key_endpoint(
    request: Request,
    current_user: UserInDB = Depends(get_current_user)
):
    """Create a new API key for the user"""
    try:
        body = await request.json()
        key_name = body.get("name", "Default API Key")

        api_key, api_key_id = create_api_key_for_user(current_user.id, key_name)
        return {
            "api_key": api_key,
            "api_key_id": api_key_id,
            "message": "API key generated successfully"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate API key: {str(e)}")


@app.get("/api/keys", dependencies=[Depends(get_current_user)])
async def list_api_keys(current_user: UserInDB = Depends(get_current_user)):
    """List all API keys for the user"""
    try:
        api_keys = get_api_keys_for_user(current_user.id)
        # Format response to hide the actual key and only show prefix
        formatted_keys = []
        for key in api_keys:
            formatted_keys.append({
                "id": key.id,
                "name": key.name,
                "key_prefix": key.key_prefix,
                "status": key.status,
                "created_at": key.created_at,
                "last_used_at": key.last_used_at,
                "permissions": key.permissions
            })
        return {"api_keys": formatted_keys}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve API keys: {str(e)}")


@app.post("/api/keys/revoke/{key_id}", dependencies=[Depends(get_current_user)])
async def revoke_api_key_endpoint(
    key_id: str,
    current_user: UserInDB = Depends(get_current_user)
):
    """Revoke an API key"""
    try:
        success = revoke_api_key(key_id, current_user.id)
        if success:
            return {"message": "API key revoked successfully"}
        else:
            raise HTTPException(status_code=404, detail="API key not found or already revoked")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to revoke API key: {str(e)}")


@app.delete("/api/keys/{key_id}", dependencies=[Depends(get_current_user)])
async def delete_api_key_endpoint(
    key_id: str,
    current_user: UserInDB = Depends(get_current_user)
):
    """Delete an API key"""
    try:
        success = delete_api_key(key_id, current_user.id)
        if success:
            return {"message": "API key deleted successfully"}
        else:
            raise HTTPException(status_code=404, detail="API key not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete API key: {str(e)}")


# Stripe webhook endpoint to handle successful payments
@app.post("/webhook")
async def stripe_webhook(request: Request):
    """Handle Stripe webhooks to update user subscription status after payment"""
    payload = await request.body()
    sig_header = request.headers.get('stripe-signature')

    try:
        # Verify webhook signature (you would need to set a webhook signing secret in your Stripe dashboard)
        event = stripe.Webhook.construct_event(
            payload, sig_header, os.getenv('STRIPE_WEBHOOK_SECRET', 'whsec_test_secret')
        )
    except ValueError:
        # Invalid payload
        raise HTTPException(status_code=400, detail="Invalid payload")
    except stripe.error.SignatureVerificationError:
        # Invalid signature
        raise HTTPException(status_code=400, detail="Invalid signature")

    # Handle the event
    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']

        # Get the customer email from the session
        customer_email = session.get('customer_details', {}).get('email') or session.get('customer_email')

        if customer_email:
            # Update the user's subscription status in the database
            subscription_end = datetime.utcnow() + timedelta(days=30)  # 30-day subscription
            update_user_subscription(customer_email, True, subscription_end)

    return {"success": True}


@app.post("/api/auto-agent")
async def auto_agent(
    image: UploadFile = File(...),
    instruction: str = Form(...),
    current_user: UserInDB = Depends(get_current_user_or_api_key)
):
    """
    Enhanced Auto agent endpoint that processes images based on user instructions using AI.
    The agent analyzes the instruction with AI and executes appropriate image processing operations.

    Args:
        image: Input image to process
        instruction: Natural language instruction for what to do with the image
        current_user: Authenticated user

    Returns:
        Processed image based on the instruction
    """
    try:
        # Read the uploaded image
        image_contents = await image.read()

        # Validate file type
        if not image_contents[:4] in [b'\x89PNG', b'\xFF\xD8\xFF', b'GIF8', b'\x49\x49\x2A\x00', b'\x4D\x4D\x00\x2A', b'\x00\x00\x00\x0C']:
            file_ext = os.path.splitext(image.filename)[1].lower()
            allowed_exts = ['.png', '.jpg', '.jpeg', '.gif', '.bmp', '.tiff', '.webp']
            if file_ext not in allowed_exts:
                raise HTTPException(status_code=400, detail="Invalid file type. Only image files are allowed")

        # Validate file size (max 10MB)
        if len(image_contents) > 10 * 1024 * 1024:
            raise HTTPException(status_code=400, detail="File size exceeds 10MB limit")

        # Try to open image with PIL to validate it's a valid image file
        try:
            img = Image.open(io.BytesIO(image_contents))
            img.verify()  # Verify that it's a valid image
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid or corrupted image file")

        # Reopen image after verification
        input_image = Image.open(io.BytesIO(image_contents)).convert("RGB")

        # Use AI to analyze the instruction and determine operations
        analysis_result = analyze_instruction_with_ai(instruction)
        operations = analysis_result.get("operations", [])

        if not operations:
            # If no operations identified, default to background removal
            operations = [{"type": "background_remove", "parameters": {}}]

        # Execute the operations on the image
        result_img = execute_operations(input_image, operations)

        # Add watermark with user ID
        watermarked_img = add_watermark(result_img, current_user.id)

        # Save to the output directory
        output_dir = os.path.join(current_dir, "output")
        os.makedirs(output_dir, exist_ok=True)

        # Save the original uploaded image
        original_img_original = Image.open(io.BytesIO(image_contents))
        original_timestamp = int(time.time())
        original_filename = f"auto_agent_original_{original_timestamp}_{image.filename}"
        original_path = os.path.join(output_dir, original_filename)
        original_img_original.save(original_path)
        print(f"Saved original to {original_path}")

        # Generate a unique filename for processed result
        output_filename = f"auto_agent_result_{original_timestamp}.png"
        output_path = os.path.join(output_dir, output_filename)
        watermarked_img.save(output_path)
        print(f"Saved result to {output_path}")

        # Save metadata about this processed image
        metadata = {
            "id": output_filename,
            "input_filename": original_filename,
            "instruction": instruction,
            "operations_performed": operations,  # Store the operations that were performed
            "operation": "auto-agent",
            "timestamp": original_timestamp,
            "timestamp_formatted": time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(original_timestamp)),
            "original_path": f"/api/image/{original_filename}",
            "processed_path": f"/api/image/{output_filename}",
            "api_endpoint": f"/api/image/{output_filename}",
            "user_id": current_user.id,
            "title": f"Auto Agent: {instruction[:50]}{'...' if len(instruction) > 50 else ''}",
            "ai_analysis": analysis_result  # Store the AI analysis result
        }

        # Save metadata to a JSON file
        metadata_path = os.path.join(output_dir, f"{output_filename}.json")
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f)

        # Save to bytes
        output_bytes = io.BytesIO()
        watermarked_img.save(output_bytes, format="PNG")
        output_bytes.seek(0)

        return StreamingResponse(
            output_bytes,
            media_type="image/png",
            headers={"Content-Disposition": "attachment; filename=auto_agent_output.png"}
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing auto agent request: {str(e)}")


@app.post("/api/public-auto-agent")
async def public_auto_agent(
    image: UploadFile = File(...),
    instruction: str = Form(...)
):
    """
    Enhanced Public auto agent endpoint that processes images based on user instructions using AI.
    The agent analyzes the instruction with AI and executes appropriate image processing operations.
    No authentication required.

    Args:
        image: Input image to process
        instruction: Natural language instruction for what to do with the image

    Returns:
        Processed image based on the instruction
    """
    try:
        # Read the uploaded image
        image_contents = await image.read()

        # Validate file type
        if not image_contents[:4] in [b'\x89PNG', b'\xFF\xD8\xFF', b'GIF8', b'\x49\x49\x2A\x00', b'\x4D\x4D\x00\x2A', b'\x00\x00\x00\x0C']:
            file_ext = os.path.splitext(image.filename)[1].lower()
            allowed_exts = ['.png', '.jpg', '.jpeg', '.gif', '.bmp', '.tiff', '.webp']
            if file_ext not in allowed_exts:
                raise HTTPException(status_code=400, detail="Invalid file type. Only image files are allowed")

        # Validate file size (max 10MB)
        if len(image_contents) > 10 * 1024 * 1024:
            raise HTTPException(status_code=400, detail="File size exceeds 10MB limit")

        # Try to open image with PIL to validate it's a valid image file
        try:
            img = Image.open(io.BytesIO(image_contents))
            img.verify()  # Verify that it's a valid image
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid or corrupted image file")

        # Reopen image after verification
        input_image = Image.open(io.BytesIO(image_contents)).convert("RGB")

        # Use AI to analyze the instruction and determine operations
        analysis_result = analyze_instruction_with_ai(instruction)
        operations = analysis_result.get("operations", [])

        if not operations:
            # If no operations identified, default to background removal
            operations = [{"type": "background_remove", "parameters": {}}]

        # Execute the operations on the image
        result_img = execute_operations(input_image, operations)

        # Add watermark with anonymous identifier for public endpoint
        watermarked_img = add_watermark(result_img, "anonymous_user")

        # Save to the output directory
        output_dir = os.path.join(current_dir, "output")
        os.makedirs(output_dir, exist_ok=True)

        # Save the original uploaded image
        original_img_original = Image.open(io.BytesIO(image_contents))
        original_timestamp = int(time.time())
        original_filename = f"public_auto_agent_original_{original_timestamp}_{image.filename}"
        original_path = os.path.join(output_dir, original_filename)
        original_img_original.save(original_path)
        print(f"Saved original to {original_path}")

        # Generate a unique filename for processed result
        output_filename = f"public_auto_agent_result_{original_timestamp}.png"
        output_path = os.path.join(output_dir, output_filename)
        watermarked_img.save(output_path)
        print(f"Saved result to {output_path}")

        # Save metadata about this processed image
        metadata = {
            "id": output_filename,
            "input_filename": original_filename,
            "instruction": instruction,
            "operations_performed": operations,  # Store the operations that were performed
            "operation": "public-auto-agent",
            "timestamp": original_timestamp,
            "timestamp_formatted": time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(original_timestamp)),
            "original_path": f"/api/image/{original_filename}",
            "processed_path": f"/api/image/{output_filename}",
            "api_endpoint": f"/api/image/{output_filename}",
            "user_id": "anonymous_user",
            "title": f"Public Auto Agent: {instruction[:50]}{'...' if len(instruction) > 50 else ''}",
            "ai_analysis": analysis_result  # Store the AI analysis result
        }

        # Save metadata to a JSON file
        metadata_path = os.path.join(output_dir, f"{output_filename}.json")
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f)

        # Save to bytes
        output_bytes = io.BytesIO()
        watermarked_img.save(output_bytes, format="PNG")
        output_bytes.seek(0)

        return StreamingResponse(
            output_bytes,
            media_type="image/png",
            headers={"Content-Disposition": "attachment; filename=public_auto_agent_output.png"}
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing public auto agent request: {str(e)}")


def enhance_image_quality(image: Image.Image) -> Image.Image:
    """
    Apply image enhancement to improve quality without sharpening
    """
    # Convert PIL image to numpy array for processing
    img_array = np.array(image)

    # 1. Enhance contrast using CLAHE (Contrast Limited Adaptive Histogram Equalization)
    if len(img_array.shape) == 3:
        # Convert to LAB color space for better contrast enhancement
        lab = cv2.cvtColor(img_array.astype(np.uint8), cv2.COLOR_RGB2LAB)
        l, a, b = cv2.split(lab)

        # Apply CLAHE to the L channel
        clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8,8))
        l = clahe.apply(l)

        # Merge the enhanced L channel back with A and B channels
        enhanced_lab = cv2.merge([l, a, b])
        enhanced = cv2.cvtColor(enhanced_lab, cv2.COLOR_LAB2RGB)
    else:
        # For grayscale images
        clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8,8))
        enhanced = clahe.apply(img_array.astype(np.uint8))

    # 2. Apply brightness and contrast adjustment
    # Convert back to PIL for using PIL's ImageEnhance
    enhanced_pil = Image.fromarray(enhanced.astype(np.uint8))

    # Enhance contrast
    contrast_enhancer = ImageEnhance.Contrast(enhanced_pil)
    enhanced_pil = contrast_enhancer.enhance(1.15)  # Slightly increase contrast

    # Enhance saturation
    saturation_enhancer = ImageEnhance.Color(enhanced_pil)
    enhanced_pil = saturation_enhancer.enhance(1.15)  # Slightly increase saturation

    # Enhance brightness slightly
    brightness_enhancer = ImageEnhance.Brightness(enhanced_pil)
    final_enhanced = brightness_enhancer.enhance(1.05)  # Slightly increase brightness

    return final_enhanced


@app.post("/api/enhance-image")
async def enhance_image_endpoint(
    image: UploadFile = File(...),
    strength: float = Form(1.0, description="Enhancement strength (0.5-2.0)"),
    sharpen_only: bool = Form(False, description="Apply only sharpening without other enhancements"),
    current_user: UserInDB = Depends(get_current_user_or_api_key)
):
    """
    Powerful image enhancement endpoint that improves image quality without sharpening by default.

    Args:
        image: Input image to enhance
        strength: Enhancement strength multiplier (0.5-2.0, default 1.0)
        sharpen_only: If true, only apply sharpening without other enhancements

    Returns:
        Enhanced image with improved quality (without sharpening unless sharpen_only is True)
    """
    try:
        # Read the uploaded image
        image_contents = await image.read()

        # Validate file type
        if not image_contents[:4] in [b'\x89PNG', b'\xFF\xD8\xFF', b'GIF8', b'\x49\x49\x2A\x00', b'\x4D\x4D\x00\x2A', b'\x00\x00\x00\x0C']:
            file_ext = os.path.splitext(image.filename)[1].lower()
            allowed_exts = ['.png', '.jpg', '.jpeg', '.gif', '.bmp', '.tiff', '.webp']
            if file_ext not in allowed_exts:
                raise HTTPException(status_code=400, detail="Invalid file type. Only image files are allowed")

        # Validate file size (max 10MB)
        if len(image_contents) > 10 * 1024 * 1024:
            raise HTTPException(status_code=400, detail="File size exceeds 10MB limit")

        # Try to open image with PIL to validate it's a valid image file
        try:
            img = Image.open(io.BytesIO(image_contents))
            img.verify()  # Verify that it's a valid image
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid or corrupted image file")

        # Reopen image after verification
        input_image = Image.open(io.BytesIO(image_contents)).convert("RGB")

        # Apply image enhancement based on parameters
        if sharpen_only:
            # Apply only sharpening
            enhanced_img = input_image.filter(ImageFilter.UnsharpMask(
                radius=2 * strength,
                percent=int(100 * strength),
                threshold=3
            ))
        else:
            # Apply full enhancement
            enhanced_img = enhance_image_quality(input_image)

            # Apply strength multiplier by blending with original
            if strength != 1.0:
                # Convert to numpy arrays for blending
                original_array = np.array(input_image).astype(np.float32)
                enhanced_array = np.array(enhanced_img).astype(np.float32)

                # Blend based on strength
                if strength > 1.0:
                    # If strength > 1.0, increase the effect by blending more of the enhanced image
                    blend_factor = min(strength, 2.0)  # Cap at 2.0
                    result_array = original_array * (1 - blend_factor * 0.5) + enhanced_array * (blend_factor * 0.5)
                else:
                    # If strength < 1.0, blend more with original
                    result_array = original_array * (1 - strength * 0.5) + enhanced_array * (strength * 0.5)

                result_array = np.clip(result_array, 0, 255).astype(np.uint8)
                enhanced_img = Image.fromarray(result_array, 'RGB')

        # Add watermark with user ID
        watermarked_img = add_watermark(enhanced_img, current_user.id)

        # Save to the output directory
        output_dir = os.path.join(current_dir, "output")
        os.makedirs(output_dir, exist_ok=True)

        # Save the original uploaded image
        original_img_original = Image.open(io.BytesIO(image_contents))
        original_timestamp = int(time.time())
        original_filename = f"enhance_original_{original_timestamp}_{image.filename}"
        original_path = os.path.join(output_dir, original_filename)
        original_img_original.save(original_path)
        print(f"Saved original to {original_path}")

        # Generate a unique filename for processed result
        output_filename = f"enhance_result_{original_timestamp}.png"
        output_path = os.path.join(output_dir, output_filename)
        watermarked_img.save(output_path)
        print(f"Saved result to {output_path}")

        # Save metadata about this processed image
        metadata = {
            "id": output_filename,
            "input_filename": original_filename,
            "operation": "enhance-image",
            "timestamp": original_timestamp,
            "timestamp_formatted": time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(original_timestamp)),
            "original_path": f"/api/image/{original_filename}",
            "processed_path": f"/api/image/{output_filename}",
            "api_endpoint": f"/api/image/{output_filename}",
            "user_id": current_user.id,
            "title": f"Enhanced Image: {image.filename}",
            "enhancement_params": {
                "strength": strength,
                "sharpen_only": sharpen_only
            }
        }

        # Save metadata to a JSON file
        metadata_path = os.path.join(output_dir, f"{output_filename}.json")
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f)

        # Save to bytes
        output_bytes = io.BytesIO()
        watermarked_img.save(output_bytes, format="PNG")
        output_bytes.seek(0)

        return StreamingResponse(
            output_bytes,
            media_type="image/png",
            headers={"Content-Disposition": "attachment; filename=enhanced_image.png"}
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing image enhancement request: {str(e)}")


@app.post("/api/public-enhance-image")
async def public_enhance_image_endpoint(
    image: UploadFile = File(...),
    strength: float = Form(1.0, description="Enhancement strength (0.5-2.0)"),
    sharpen_only: bool = Form(False, description="Apply only sharpening without other enhancements")
):
    """
    Powerful image enhancement endpoint (public version without authentication) that improves image quality without sharpening by default.

    Args:
        image: Input image to enhance
        strength: Enhancement strength multiplier (0.5-2.0, default 1.0)
        sharpen_only: If true, only apply sharpening without other enhancements

    Returns:
        Enhanced image with improved quality (without sharpening unless sharpen_only is True)
    """
    try:
        # Read the uploaded image
        image_contents = await image.read()

        # Validate file type
        if not image_contents[:4] in [b'\x89PNG', b'\xFF\xD8\xFF', b'GIF8', b'\x49\x49\x2A\x00', b'\x4D\x4D\x00\x2A', b'\x00\x00\x00\x0C']:
            file_ext = os.path.splitext(image.filename)[1].lower()
            allowed_exts = ['.png', '.jpg', '.jpeg', '.gif', '.bmp', '.tiff', '.webp']
            if file_ext not in allowed_exts:
                raise HTTPException(status_code=400, detail="Invalid file type. Only image files are allowed")

        # Validate file size (max 10MB)
        if len(image_contents) > 10 * 1024 * 1024:
            raise HTTPException(status_code=400, detail="File size exceeds 10MB limit")

        # Try to open image with PIL to validate it's a valid image file
        try:
            img = Image.open(io.BytesIO(image_contents))
            img.verify()  # Verify that it's a valid image
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid or corrupted image file")

        # Reopen image after verification
        input_image = Image.open(io.BytesIO(image_contents)).convert("RGB")

        # Apply image enhancement based on parameters
        if sharpen_only:
            # Apply only sharpening
            enhanced_img = input_image.filter(ImageFilter.UnsharpMask(
                radius=2 * strength,
                percent=int(100 * strength),
                threshold=3
            ))
        else:
            # Apply full enhancement
            enhanced_img = enhance_image_quality(input_image)

            # Apply strength multiplier by blending with original
            if strength != 1.0:
                # Convert to numpy arrays for blending
                original_array = np.array(input_image).astype(np.float32)
                enhanced_array = np.array(enhanced_img).astype(np.float32)

                # Blend based on strength
                if strength > 1.0:
                    # If strength > 1.0, increase the effect by blending more of the enhanced image
                    blend_factor = min(strength, 2.0)  # Cap at 2.0
                    result_array = original_array * (1 - blend_factor * 0.5) + enhanced_array * (blend_factor * 0.5)
                else:
                    # If strength < 1.0, blend more with original
                    result_array = original_array * (1 - strength * 0.5) + enhanced_array * (strength * 0.5)

                result_array = np.clip(result_array, 0, 255).astype(np.uint8)
                enhanced_img = Image.fromarray(result_array, 'RGB')

        # Add watermark with anonymous identifier for public endpoint
        watermarked_img = add_watermark(enhanced_img, "anonymous_user")

        # Save to the output directory
        output_dir = os.path.join(current_dir, "output")
        os.makedirs(output_dir, exist_ok=True)

        # Save the original uploaded image
        original_img_original = Image.open(io.BytesIO(image_contents))
        original_timestamp = int(time.time())
        original_filename = f"public_enhance_original_{original_timestamp}_{image.filename}"
        original_path = os.path.join(output_dir, original_filename)
        original_img_original.save(original_path)
        print(f"Saved original to {original_path}")

        # Generate a unique filename for processed result
        output_filename = f"public_enhance_result_{original_timestamp}.png"
        output_path = os.path.join(output_dir, output_filename)
        watermarked_img.save(output_path)
        print(f"Saved result to {output_path}")

        # Save metadata about this processed image
        metadata = {
            "id": output_filename,
            "input_filename": original_filename,
            "operation": "public-enhance-image",
            "timestamp": original_timestamp,
            "timestamp_formatted": time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(original_timestamp)),
            "original_path": f"/api/image/{original_filename}",
            "processed_path": f"/api/image/{output_filename}",
            "api_endpoint": f"/api/image/{output_filename}",
            "user_id": "anonymous_user",
            "title": f"Public Enhanced Image: {image.filename}",
            "enhancement_params": {
                "strength": strength,
                "sharpen_only": sharpen_only
            }
        }

        # Save metadata to a JSON file
        metadata_path = os.path.join(output_dir, f"{output_filename}.json")
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f)

        # Save to bytes
        output_bytes = io.BytesIO()
        watermarked_img.save(output_bytes, format="PNG")
        output_bytes.seek(0)

        return StreamingResponse(
            output_bytes,
            media_type="image/png",
            headers={"Content-Disposition": "attachment; filename=public_enhanced_image.png"}
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing public image enhancement request: {str(e)}")


def transform_to_passport_photo(image: Image.Image, bg_color: str = "blue") -> Image.Image:
    """
    Transform an image to passport photo size with colored background.
    Standard passport photo sizes:
    - US: 2x2 inches (51x51 mm)
    - EU/International: 35x45 mm
    - Common pixel size at 300 DPI: 600x600 pixels (2x2 inches)
    
    Args:
        image: PIL Image object
        bg_color: Background color ("blue", "white", "red", etc.)
    
    Returns:
        PIL Image object with passport photo dimensions and background
    """
    # Standard passport photo aspect ratio (35x45 mm ≈ 0.778)
    PASSPORT_WIDTH = 600  # pixels at 300 DPI
    PASSPORT_HEIGHT = 787  # pixels at 300 DPI (35x45mm ratio)
    
    # Convert background color string to RGB
    bg_colors = {
        "blue": (100, 149, 237),  # Cornflower blue - common for passport photos
        "white": (255, 255, 255),
        "red": (205, 92, 92),
        "gray": (211, 211, 211),
        "light-blue": (173, 216, 230),
    }
    bg_rgb = bg_colors.get(bg_color.lower(), (100, 149, 237))  # Default to blue
    
    # Convert to RGB if necessary
    if image.mode == 'RGBA':
        # Create white background and composite
        background = Image.new('RGB', image.size, bg_rgb)
        background.paste(image, mask=image.split()[3])  # Use alpha channel as mask
        image = background
    elif image.mode != 'RGB':
        image = image.convert('RGB')
    
    # Get original dimensions
    orig_width, orig_height = image.size
    orig_aspect = orig_width / orig_height
    passport_aspect = PASSPORT_WIDTH / PASSPORT_HEIGHT
    
    # Calculate crop box to maintain aspect ratio
    if orig_aspect > passport_aspect:
        # Image is wider than passport ratio - crop width
        new_width = int(orig_height * passport_aspect)
        left = (orig_width - new_width) // 2
        crop_box = (left, 0, left + new_width, orig_height)
    else:
        # Image is taller than passport ratio - crop height
        new_height = int(orig_width / passport_aspect)
        top = (orig_height - new_height) // 2
        crop_box = (0, top, orig_width, top + new_height)
    
    # Crop to passport aspect ratio
    image = image.crop(crop_box)
    
    # Resize to standard passport dimensions
    image = image.resize((PASSPORT_WIDTH, PASSPORT_HEIGHT), Image.Resampling.LANCZOS)
    
    return image


def remove_watermark_from_image(image: Image.Image) -> Image.Image:
    """
    Remove watermark from an image by detecting and inpainting the watermark region.
    This is a simplified implementation that tries to detect and remove the kite-shaped watermark.
    """
    # Convert PIL image to numpy array for processing
    img_array = np.array(image)

    # If image is in RGBA format, convert to RGB
    if len(img_array.shape) == 3 and img_array.shape[2] == 4:
        img_array = cv2.cvtColor(img_array, cv2.COLOR_RGBA2RGB)
    elif len(img_array.shape) == 2:  # Grayscale
        img_array = cv2.cvtColor(img_array, cv2.COLOR_GRAY2RGB)

    # Get image dimensions
    h, w = img_array.shape[:2]

    # Estimate watermark region based on our known watermark position (bottom-left corner)
    # The watermark is typically placed in the bottom-left corner with a padding of 20px
    padding = 20
    watermark_size = min(h, w) // 10  # Estimate watermark size based on image dimensions

    # Define the region where the watermark is likely to be
    watermark_region = (
        padding,  # x start
        h - padding - watermark_size,  # y start
        padding + watermark_size,  # x end
        h - padding  # y end
    )

    x_start, y_start, x_end, y_end = watermark_region

    # Ensure coordinates are within image bounds
    x_start = max(0, x_start)
    y_start = max(0, y_start)
    x_end = min(w, x_end)
    y_end = min(h, y_end)

    # Create a mask for the watermark region
    mask = np.zeros((h, w), dtype=np.uint8)
    mask[y_start:y_end, x_start:x_end] = 255

    # Use OpenCV's inpainting to remove the watermark
    # First, try to detect if there's actually a watermark by checking for dark regions
    roi = img_array[y_start:y_end, x_start:x_end]

    # Convert ROI to grayscale to detect dark areas
    roi_gray = cv2.cvtColor(roi, cv2.COLOR_RGB2GRAY)

    # Calculate mean intensity in the watermark region
    mean_intensity = np.mean(roi_gray)

    # If the region is significantly darker than the rest of the image, it might be a watermark
    # For now, we'll assume the watermark exists and try to inpaint the region
    try:
        # Create a more sophisticated mask by detecting dark regions
        _, binary_mask = cv2.threshold(roi_gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

        # Invert the mask since we want to inpaint dark regions
        binary_mask = 255 - binary_mask

        # Create the full mask for the entire image
        full_mask = np.zeros((h, w), dtype=np.uint8)
        full_mask[y_start:y_end, x_start:x_end] = binary_mask

        # Apply inpainting to remove the watermark
        inpainted = cv2.inpaint(
            img_array,
            full_mask,
            inpaintRadius=3,
            flags=cv2.INPAINT_TELEA
        )

        # Convert back to PIL Image
        result_img = Image.fromarray(inpainted, 'RGB')

        return result_img
    except Exception as e:
        print(f"Error in inpainting: {e}")
        # If inpainting fails, return the original image
        return image


@app.post("/api/watermark-removal")
async def remove_watermark(
    file: UploadFile = File(...),
    current_user: UserInDB = Depends(get_current_user_or_api_key)
):
    """
    Remove watermark from an image.
    This endpoint removes the kite-shaped watermark that was added to processed images.

    Args:
        file: Image file with watermark to be removed (PNG, JPG, etc.)

    Returns:
        Image with watermark removed
    """
    try:
        # Read the uploaded file
        contents = await file.read()

        # Validate file type by checking file signature
        if not contents[:4] in [b'\x89PNG', b'\xFF\xD8\xFF', b'GIF8', b'\x49\x49\x2A\x00', b'\x4D\x4D\x00\x2A', b'\x00\x00\x00\x0C']:
            # Use file extension as backup check as well
            file_ext = os.path.splitext(file.filename)[1].lower()
            allowed_exts = ['.png', '.jpg', '.jpeg', '.gif', '.bmp', '.tiff', '.webp']
            if file_ext not in allowed_exts:
                raise HTTPException(status_code=400, detail="Invalid file type. Only image files are allowed")

        # Validate file size (max 10MB)
        if len(contents) > 10 * 1024 * 1024:
            raise HTTPException(status_code=400, detail="File size exceeds 10MB limit")

        # Try to open image with PIL to validate it's a valid image file
        try:
            img = Image.open(io.BytesIO(contents))
            img.verify()  # Verify that it's a valid image
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid or corrupted image file")

        # Reopen image after verification
        img = Image.open(io.BytesIO(contents)).convert("RGB")

        # Remove watermark from the image
        result_img = remove_watermark_from_image(img)

        # Save to the output directory
        output_dir = os.path.join(current_dir, "output")
        os.makedirs(output_dir, exist_ok=True)

        # Save the original uploaded image
        original_img = Image.open(io.BytesIO(contents))
        original_timestamp = int(time.time())
        original_filename = f"watermark_original_{original_timestamp}_{file.filename}"
        original_path = os.path.join(output_dir, original_filename)
        original_img.save(original_path)
        print(f"Saved original to {original_path}")

        # Generate a unique filename for processed result
        output_filename = f"watermark_removed_{original_timestamp}.png"
        output_path = os.path.join(output_dir, output_filename)
        result_img.save(output_path, format="PNG")
        print(f"Saved result to {output_path}")

        # Save metadata about this processed image
        metadata = {
            "id": output_filename,
            "input_filename": file.filename,
            "original_filename": original_filename,
            "operation": "watermark-removal",
            "timestamp": original_timestamp,
            "timestamp_formatted": time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(original_timestamp)),
            "original_path": f"/api/image/{original_filename}",
            "processed_path": f"/api/image/{output_filename}",
            "api_endpoint": f"/api/image/{output_filename}",
            "user_id": current_user.id,  # Add user ID to track
            "title": f"Watermark removed - {file.filename}"
        }

        # Save metadata to a JSON file
        metadata_path = os.path.join(output_dir, f"{output_filename}.json")
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f)

        # Save to bytes
        output_bytes = io.BytesIO()
        result_img.save(output_bytes, format="PNG")
        output_bytes.seek(0)

        return StreamingResponse(
            output_bytes,
            media_type="image/png",
            headers={"Content-Disposition": "attachment; filename=watermark_removed.png"}
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing image: {str(e)}")


@app.post("/api/public-watermark-removal")
async def public_remove_watermark(
    file: UploadFile = File(...)
):
    """
    Remove watermark from an image (public endpoint without authentication).
    This endpoint removes the kite-shaped watermark that was added to processed images.

    Args:
        file: Image file with watermark to be removed (PNG, JPG, etc.)

    Returns:
        Image with watermark removed
    """
    try:
        # Read the uploaded file
        contents = await file.read()

        # Validate file type by checking file signature
        if not contents[:4] in [b'\x89PNG', b'\xFF\xD8\xFF', b'GIF8', b'\x49\x49\x2A\x00', b'\x4D\x4D\x00\x2A', b'\x00\x00\x00\x0C']:
            # Use file extension as backup check as well
            file_ext = os.path.splitext(file.filename)[1].lower()
            allowed_exts = ['.png', '.jpg', '.jpeg', '.gif', '.bmp', '.tiff', '.webp']
            if file_ext not in allowed_exts:
                raise HTTPException(status_code=400, detail="Invalid file type. Only image files are allowed")

        # Validate file size (max 10MB)
        if len(contents) > 10 * 1024 * 1024:
            raise HTTPException(status_code=400, detail="File size exceeds 10MB limit")

        # Try to open image with PIL to validate it's a valid image file
        try:
            img = Image.open(io.BytesIO(contents))
            img.verify()  # Verify that it's a valid image
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid or corrupted image file")

        # Reopen image after verification
        img = Image.open(io.BytesIO(contents)).convert("RGB")

        # Remove watermark from the image
        result_img = remove_watermark_from_image(img)

        # Save to the output directory
        output_dir = os.path.join(current_dir, "output")
        os.makedirs(output_dir, exist_ok=True)

        # Save the original uploaded image
        original_img = Image.open(io.BytesIO(contents))
        original_timestamp = int(time.time())
        original_filename = f"public_watermark_original_{original_timestamp}_{file.filename}"
        original_path = os.path.join(output_dir, original_filename)
        original_img.save(original_path)
        print(f"Saved original to {original_path}")

        # Generate a unique filename for processed result
        output_filename = f"public_watermark_removed_{original_timestamp}.png"
        output_path = os.path.join(output_dir, output_filename)
        result_img.save(output_path, format="PNG")
        print(f"Saved result to {output_path}")

        # Save metadata about this processed image
        metadata = {
            "id": output_filename,
            "input_filename": file.filename,
            "original_filename": original_filename,
            "operation": "public-watermark-removal",
            "timestamp": original_timestamp,
            "timestamp_formatted": time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(original_timestamp)),
            "original_path": f"/api/image/{original_filename}",
            "processed_path": f"/api/image/{output_filename}",
            "api_endpoint": f"/api/image/{output_filename}",
            "user_id": "anonymous_user",  # For public endpoint
            "title": f"Public Watermark removed - {file.filename}"
        }

        # Save metadata to a JSON file
        metadata_path = os.path.join(output_dir, f"{output_filename}.json")
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f)

        # Save to bytes
        output_bytes = io.BytesIO()
        result_img.save(output_bytes, format="PNG")
        output_bytes.seek(0)

        return StreamingResponse(
            output_bytes,
            media_type="image/png",
            headers={"Content-Disposition": "attachment; filename=public_watermark_removed.png"}
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing image: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
