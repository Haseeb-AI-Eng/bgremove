# Image Processing API

A FastAPI-based REST API for image processing with three powerful endpoints: background removal, clothing color change, and background color change.

## Features

The API provides three main endpoints for image manipulation:

1. **Remove Background** - Removes the background from images using AI-powered segmentation, returning a PNG with transparent background.
2. **Change Clothes** - Shifts the color of clothing in images by modifying the hue channel in HSV color space.
3. **Change Background** - Removes the background and replaces it with a solid color of your choice.

## Installation

### Prerequisites

- Python 3.10 or higher
- pip package manager

### Setup

Navigate to the app directory and create a virtual environment:

```bash
cd app
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

## Running the Server

Start the FastAPI server:

```bash
source venv/bin/activate  # Activate virtual environment if not already active
python main.py
```

The server will start on `https://hintergrundentfernen.ai`

Access the interactive API documentation at `https://hintergrundentfernen.ai/docs`

## API Endpoints

### 1. Health Check

**Endpoint:** `GET /health`

**Description:** Check if the API is running and healthy.

**Response:**
```json
{
  "status": "healthy"
}
```

### 2. Remove Background

**Endpoint:** `POST /api/remove-background`

**Description:** Remove the background from an image and return a PNG with transparent background.

**Parameters:**
- `file` (required): Image file (PNG, JPG, JPEG, etc.)

**Request Example:**
```bash
curl -X POST "https://hintergrundentfernen.ai/api/remove-background" \
  -H "accept: image/png" \
  -F "file=@/path/to/image.jpg"
```

**Response:** PNG image with transparent background

**Response Headers:**
```
Content-Type: image/png
Content-Disposition: attachment; filename=output.png
```

### 3. Change Clothes

**Endpoint:** `POST /api/change-clothes`

**Description:** Change the color of clothing in an image by shifting the hue.

**Parameters:**
- `file` (required): Image file (PNG, JPG, JPEG, etc.)
- `color_shift` (optional): Hue shift value from 0 to 180 (default: 60)

**Request Example:**
```bash
curl -X POST "https://hintergrundentfernen.ai/api/change-clothes" \
  -H "accept: image/png" \
  -F "file=@/path/to/image.jpg" \
  -F "color_shift=90"
```

**Response:** PNG image with modified clothing color

**Response Headers:**
```
Content-Type: image/png
Content-Disposition: attachment; filename=clothes_changed.png
```

**Color Shift Values:**
- `0-30`: Subtle shifts (red to orange)
- `30-60`: Moderate shifts (orange to yellow)
- `60-90`: Significant shifts (yellow to green)
- `90-120`: Major shifts (green to cyan)
- `120-150`: Dramatic shifts (cyan to blue)
- `150-180`: Extreme shifts (blue to magenta)

### 4. Change Background

**Endpoint:** `POST /api/change-background`

**Description:** Remove background and replace it with a solid color.

**Parameters:**
- `file` (required): Image file (PNG, JPG, JPEG, etc.)
- `bg_color` (optional): Background color in hex format without '#' (default: "FFFFFF" for white)

**Request Example:**
```bash
curl -X POST "https://hintergrundentfernen.ai/api/change-background" \
  -H "accept: image/png" \
  -F "file=@/path/to/image.jpg" \
  -F "bg_color=FF0000"
```

**Response:** PNG image with new background color

**Response Headers:**
```
Content-Type: image/png
Content-Disposition: attachment; filename=bg_changed.png
```

**Common Color Codes:**
- `FFFFFF` - White
- `000000` - Black
- `FF0000` - Red
- `00FF00` - Green
- `0000FF` - Blue
- `FFFF00` - Yellow
- `FF00FF` - Magenta
- `00FFFF` - Cyan

## Usage Examples

### Python Example

```python
import requests

# Remove background
with open('image.jpg', 'rb') as f:
    files = {'file': f}
    response = requests.post('https://hintergrundentfernen.ai/api/remove-background', files=files)
    with open('output.png', 'wb') as out:
        out.write(response.content)

# Change clothes color
with open('image.jpg', 'rb') as f:
    files = {'file': f}
    data = {'color_shift': '90'}
    response = requests.post('https://hintergrundentfernen.ai/api/change-clothes', files=files, data=data)
    with open('clothes_changed.png', 'wb') as out:
        out.write(response.content)

# Change background color
with open('image.jpg', 'rb') as f:
    files = {'file': f}
    data = {'bg_color': 'FF0000'}
    response = requests.post('https://hintergrundentfernen.ai/api/change-background', files=files, data=data)
    with open('bg_changed.png', 'wb') as out:
        out.write(response.content)
```

### JavaScript/Fetch Example

```javascript
// Remove background
const formData = new FormData();
formData.append('file', fileInput.files[0]);

const response = await fetch('https://hintergrundentfernen.ai/api/remove-background', {
  method: 'POST',
  body: formData
});

const blob = await response.blob();
const url = window.URL.createObjectURL(blob);
const img = document.createElement('img');
img.src = url;
document.body.appendChild(img);

// Change clothes
const formData2 = new FormData();
formData2.append('file', fileInput.files[0]);
formData2.append('color_shift', '90');

const response2 = await fetch('https://hintergrundentfernen.ai/api/change-clothes', {
  method: 'POST',
  body: formData2
});

// Change background
const formData3 = new FormData();
formData3.append('file', fileInput.files[0]);
formData3.append('bg_color', 'FF0000');

const response3 = await fetch('https://hintergrundentfernen.ai/api/change-background', {
  method: 'POST',
  body: formData3
});
```

## Error Handling

The API returns appropriate HTTP status codes and error messages:

| Status Code | Description |
|-------------|-------------|
| 200 | Success |
| 400 | Bad request (invalid parameters or file size) |
| 500 | Internal server error |

**Error Response Example:**
```json
{
  "detail": "File size exceeds 10MB limit"
}
```

## Constraints

- **File Size Limit:** Maximum 10MB per image
- **Supported Formats:** PNG, JPG, JPEG, BMP, WEBP, and other common image formats
- **Processing Time:** 2-5 seconds per image depending on size and complexity
- **Color Shift Range:** 0-180 (HSV hue range)
- **Background Color:** 6-character hexadecimal format

## Performance Notes

- The first request may take longer as the background removal model is loaded into memory
- Subsequent requests will be faster due to model caching
- For production use, consider implementing request queuing and async processing

## Architecture

The API uses the following libraries:

- **FastAPI:** Modern web framework for building APIs
- **Uvicorn:** ASGI web server
- **rembg:** AI-powered background removal using ONNX models
- **Pillow:** Image processing library
- **OpenCV:** Computer vision library for color manipulation
- **NumPy:** Numerical computing library

## Troubleshooting

### Issue: "rembg model not found"
**Solution:** The model will be automatically downloaded on first use. Ensure you have internet connectivity.

### Issue: "Out of memory"
**Solution:** Reduce image size or restart the server. Consider implementing image resizing in preprocessing.

### Issue: "CORS errors"
**Solution:** The API includes CORS middleware enabled for all origins. If issues persist, check your client's request headers.

## Future Enhancements

Potential improvements for future versions:

1. Integration with FASHN AI API for advanced virtual try-on
2. Batch image processing
3. Webhook support for async processing
4. Image caching and optimization
5. Authentication and rate limiting
6. Advanced clothing detection and segmentation
7. Multiple background options (gradients, patterns, images)
8. Image resizing and quality optimization

## License

This project is open source and available under the MIT License.

## Support

For issues, questions, or feature requests, please refer to the project documentation or create an issue in the repository.
