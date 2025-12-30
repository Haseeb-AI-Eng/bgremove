import React, { useState } from 'react';
import { FaUpload, FaDownload, FaMagic, FaTrash, FaEye, FaPalette } from 'react-icons/fa';
import toast from 'react-hot-toast';
import axios from 'axios';

const ImageProcessingPage = () => {
  const [selectedFile, setSelectedFile] = useState(null);
  const [selectedBackgroundFile, setSelectedBackgroundFile] = useState(null);
  const [previewUrl, setPreviewUrl] = useState(null);
  const [backgroundPreviewUrl, setBackgroundPreviewUrl] = useState(null);
  const [resultUrl, setResultUrl] = useState(null);
  const [loading, setLoading] = useState(false);
  const [processingType, setProcessingType] = useState('remove-background');
  const [backgroundColor, setBackgroundColor] = useState('#ffffff'); // Default to white

  const handleFileChange = (e) => {
    const file = e.target.files[0];
    if (file) {
      setSelectedFile(file);
      setPreviewUrl(URL.createObjectURL(file));
      setResultUrl(null); // Reset result when new file is selected
    }
  };

  const handleBackgroundFileChange = (e) => {
    const file = e.target.files[0];
    if (file) {
      setSelectedBackgroundFile(file);
      setBackgroundPreviewUrl(URL.createObjectURL(file));
      setResultUrl(null); // Reset result when new file is selected
    }
  };

  const handleProcessImage = async () => {
    if (!selectedFile) {
      toast.error('Please select an image first');
      return;
    }

    // For change-background-color, we need the color
    if (processingType === 'change-background' && !backgroundColor) {
      toast.error('Please select a background color');
      return;
    }

    // For replace-background, we need both images
    if (processingType === 'replace-background' && !selectedBackgroundFile) {
      toast.error('Please select a background image');
      return;
    }

    setLoading(true);

    try {
      const formData = new FormData();
      formData.append('file', selectedFile);

      let endpoint;
      switch (processingType) {
        case 'remove-background':
          endpoint = '/api/public-remove-background';
          break;
        case 'change-background':
          endpoint = '/api/public-change-background';
          formData.append('bg_color', backgroundColor.replace('#', '')); // Remove # from hex color
          break;
        case 'replace-background':
          formData.append('background_image', selectedBackgroundFile);
          endpoint = '/api/public-replace-background';
          break;
        case 'change-clothes':
          endpoint = '/api/public-change-clothes';
          break;
        case 'replace-clothes':
          endpoint = '/api/public-replace-clothes';
          break;
        default:
          endpoint = '/api/public-remove-background';
      }

      const response = await axios.post(endpoint, formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
        responseType: 'blob', // Important for handling binary image data
      });

      // Create a URL for the processed image blob
      const imageUrl = URL.createObjectURL(response.data);
      setResultUrl(imageUrl);
      toast.success('Image processed successfully!');
    } catch (error) {
      console.error('Error processing image:', error);
      toast.error(error.response?.data?.detail || 'Error processing image');
    } finally {
      setLoading(false);
    }
  };

  const handleDownload = () => {
    if (resultUrl) {
      const link = document.createElement('a');
      link.href = resultUrl;
      link.download = 'processed-image.png';
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
    }
  };

  const handleReset = () => {
    setSelectedFile(null);
    setSelectedBackgroundFile(null);
    setPreviewUrl(null);
    setBackgroundPreviewUrl(null);
    setResultUrl(null);
    document.getElementById('file-input').value = '';
    const backgroundFileInput = document.getElementById('background-file-input');
    if (backgroundFileInput) {
      backgroundFileInput.value = '';
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 py-8">
      <div className="container mx-auto px-4">
        {/* Header */}
        <div className="text-center mb-8">
          <div className="w-16 h-16 bg-gradient-to-r from-blue-500 to-purple-600 rounded-xl flex items-center justify-center mx-auto mb-4">
            <FaMagic className="text-white text-2xl" />
          </div>
          <h1 className="text-4xl font-bold text-gray-900 mb-4">Image Processing Suite</h1>
          <p className="text-xl text-gray-600 max-w-3xl mx-auto">
            Advanced image processing tools including background removal, enhancement, and manipulation.
          </p>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 max-w-6xl mx-auto">
          {/* Upload and Controls */}
          <div className="bg-white rounded-xl shadow-sm p-6">
            <h2 className="text-2xl font-semibold text-gray-900 mb-6">Upload Image</h2>
            
            {/* Processing Type Selection */}
            <div className="mb-6">
              <label className="block text-sm font-medium text-gray-700 mb-2">Processing Type</label>
              <div className="grid grid-cols-2 gap-2">
                {[
                  { value: 'remove-background', label: 'Remove Background' },
                  { value: 'change-background', label: 'Change Background Color' },
                  { value: 'replace-background', label: 'Replace Background' },
                  { value: 'change-clothes', label: 'Change Clothes Color' }
                ].map((option) => (
                  <label key={option.value} className="flex items-center">
                    <input
                      type="radio"
                      name="processingType"
                      value={option.value}
                      checked={processingType === option.value}
                      onChange={(e) => setProcessingType(e.target.value)}
                      className="h-4 w-4 text-indigo-600 focus:ring-indigo-500 border-gray-300"
                    />
                    <span className="ml-2 text-sm text-gray-700">{option.label}</span>
                  </label>
                ))}
              </div>
            </div>

            {/* Original Image Upload */}
            <div className="mb-6">
              <label className="block text-sm font-medium text-gray-700 mb-2">Upload Image</label>
              <div className="mt-1">
                <input
                  id="file-input"
                  type="file"
                  accept="image/*"
                  onChange={handleFileChange}
                  className="file-input"
                />
                <label htmlFor="file-input" className="file-label">
                  <FaUpload className="mr-2" />
                  {selectedFile ? selectedFile.name : 'Choose an image file'}
                </label>
              </div>
            </div>

            {/* Background Color Selection for Change Background Color */}
            {processingType === 'change-background' && (
              <div className="mb-6">
                <label className="block text-sm font-medium text-gray-700 mb-2">Select Background Color</label>
                <div className="flex items-center gap-4">
                  <input
                    type="color"
                    value={backgroundColor}
                    onChange={(e) => setBackgroundColor(e.target.value)}
                    className="w-12 h-12 border border-gray-300 rounded cursor-pointer"
                  />
                  <div className="flex-1">
                    <input
                      type="text"
                      value={backgroundColor}
                      onChange={(e) => setBackgroundColor(e.target.value)}
                      className="input-field w-full"
                      placeholder="#FFFFFF"
                    />
                  </div>
                </div>
              </div>
            )}

            {/* Background Image Upload for Replace Background */}
            {processingType === 'replace-background' && (
              <div className="mb-6">
                <label className="block text-sm font-medium text-gray-700 mb-2">Upload Background Image</label>
                <div className="mt-1">
                  <input
                    id="background-file-input"
                    type="file"
                    accept="image/*"
                    onChange={handleBackgroundFileChange}
                    className="file-input"
                  />
                  <label htmlFor="background-file-input" className="file-label">
                    <FaUpload className="mr-2" />
                    {selectedBackgroundFile ? selectedBackgroundFile.name : 'Choose a background image'}
                  </label>
                </div>

                {/* Background Preview */}
                {backgroundPreviewUrl && (
                  <div className="mt-4">
                    <h3 className="text-lg font-medium text-gray-900 mb-2">Background Preview</h3>
                    <div className="border rounded-lg p-4 bg-gray-50">
                      <img
                        src={backgroundPreviewUrl}
                        alt="Background Preview"
                        className="max-h-48 w-full object-contain rounded"
                      />
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* Preview */}
            {previewUrl && (
              <div className="mb-6">
                <h3 className="text-lg font-medium text-gray-900 mb-2">Preview</h3>
                <div className="border rounded-lg p-4 bg-gray-50">
                  <img
                    src={previewUrl}
                    alt="Preview"
                    className="max-h-48 w-full object-contain rounded"
                  />
                </div>
              </div>
            )}

            {/* Action Buttons */}
            <div className="flex flex-wrap gap-3">
              <button
                onClick={handleProcessImage}
                disabled={loading || !selectedFile ||
                         (processingType === 'change-background' && !backgroundColor) ||
                         (processingType === 'replace-background' && !selectedBackgroundFile)}
                className="btn btn-primary flex-1 min-w-[120px]"
              >
                {loading ? (
                  <>
                    <span className="loading-spinner mr-2"></span>
                    Processing...
                  </>
                ) : (
                  'Process Image'
                )}
              </button>

              {selectedFile && (
                <button
                  onClick={handleReset}
                  className="btn btn-outline flex-1 min-w-[120px]"
                >
                  <FaTrash className="mr-2" /> Reset
                </button>
              )}
            </div>
          </div>

          {/* Result Preview */}
          <div className="bg-white rounded-xl shadow-sm p-6">
            <h2 className="text-2xl font-semibold text-gray-900 mb-6">Result</h2>
            
            {resultUrl ? (
              <div className="space-y-6">
                <div>
                  <h3 className="text-lg font-medium text-gray-900 mb-2">Processed Image</h3>
                  <div className="border rounded-lg p-4 bg-gray-50 relative">
                    <img
                      src={resultUrl}
                      alt="Processed"
                      className="max-h-80 w-full object-contain rounded"
                    />
                    {/* Watermark */}
                    <div className="absolute bottom-2 right-2 bg-black bg-opacity-50 text-white text-xs px-2 py-1 rounded">
                      AI Processed
                    </div>
                  </div>
                </div>

                <div className="flex flex-wrap gap-3">
                  <button
                    onClick={handleDownload}
                    className="btn btn-primary flex-1 min-w-[120px]"
                  >
                    <FaDownload className="mr-2" /> Download
                  </button>

                  <button className="btn btn-outline flex-1 min-w-[120px]">
                    <FaEye className="mr-2" /> Preview
                  </button>
                </div>
              </div>
            ) : (
              <div className="flex flex-col items-center justify-center h-64 border-2 border-dashed border-gray-300 rounded-lg">
                <FaMagic className="text-gray-400 text-4xl mb-4" />
                <p className="text-gray-500 text-center">
                  {selectedFile
                    ? 'Click "Process Image" to see results'
                    : 'Upload an image to start processing'
                  }
                </p>
              </div>
            )}
          </div>
        </div>

        {/* Features Section */}
        <div className="mt-16">
          <h2 className="text-3xl font-bold text-gray-900 text-center mb-12">Advanced Image Processing Features</h2>
          
          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            <div className="bg-white p-6 rounded-xl shadow-sm">
              <div className="w-12 h-12 bg-gradient-to-r from-blue-500 to-purple-600 rounded-lg flex items-center justify-center mb-4">
                <FaMagic className="text-white text-xl" />
              </div>
              <h3 className="text-lg font-semibold text-gray-900 mb-2">Background Removal</h3>
              <p className="text-gray-600">
                Advanced AI-powered background removal with precision edge detection and transparency preservation.
              </p>
            </div>
            
            <div className="bg-white p-6 rounded-xl shadow-sm">
              <div className="w-12 h-12 bg-gradient-to-r from-green-500 to-teal-600 rounded-lg flex items-center justify-center mb-4">
                <FaMagic className="text-white text-xl" />
              </div>
              <h3 className="text-lg font-semibold text-gray-900 mb-2">Image Enhancement</h3>
              <p className="text-gray-600">
                Automatically enhance image quality with noise reduction, sharpening, and color correction.
              </p>
            </div>
            
            <div className="bg-white p-6 rounded-xl shadow-sm">
              <div className="w-12 h-12 bg-gradient-to-r from-pink-500 to-rose-600 rounded-lg flex items-center justify-center mb-4">
                <FaMagic className="text-white text-xl" />
              </div>
              <h3 className="text-lg font-semibold text-gray-900 mb-2">Color Adjustment</h3>
              <p className="text-gray-600">
                Fine-tune colors, brightness, contrast, and saturation with AI-powered recommendations.
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ImageProcessingPage;