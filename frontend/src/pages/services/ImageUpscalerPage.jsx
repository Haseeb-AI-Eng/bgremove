import React, { useState } from 'react';
import { FaUpload, FaExpand, FaDownload, FaEye } from 'react-icons/fa';
import toast from 'react-hot-toast';

const ImageUpscalerPage = () => {
  const [selectedFile, setSelectedFile] = useState(null);
  const [previewUrl, setPreviewUrl] = useState(null);
  const [resultUrl, setResultUrl] = useState(null);
  const [loading, setLoading] = useState(false);
  const [upscalingFactor, setUpscalingFactor] = useState(2);

  const handleFileChange = (e) => {
    const file = e.target.files[0];
    if (file) {
      setSelectedFile(file);
      setPreviewUrl(URL.createObjectURL(file));
      setResultUrl(null); // Reset result when new file is selected
    }
  };

  const handleUpscaleImage = async () => {
    if (!selectedFile) {
      toast.error('Please select an image first');
      return;
    }

    setLoading(true);

    try {
      // Simulate AI processing
      await new Promise(resolve => setTimeout(resolve, 2000));

      // For demo, we'll use the original image as the result
      // In a real app, this would be the upscaled image from the API
      setResultUrl(previewUrl);
      toast.success(`Image upscaled by ${upscalingFactor}x successfully!`);
    } catch (error) {
      toast.error('Error upscaling image');
    } finally {
      setLoading(false);
    }
  };

  const handleDownload = () => {
    if (resultUrl) {
      const link = document.createElement('a');
      link.href = resultUrl;
      link.download = `upscaled-image-${upscalingFactor}x.png`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 py-8">
      <div className="container mx-auto px-4">
        {/* Header */}
        <div className="text-center mb-8">
          <div className="w-16 h-16 bg-gradient-to-r from-indigo-500 to-blue-600 rounded-xl flex items-center justify-center mx-auto mb-4">
            <FaExpand className="text-white text-2xl" />
          </div>
          <h1 className="text-4xl font-bold text-gray-900 mb-4">Image Upscaler</h1>
          <p className="text-xl text-gray-600 max-w-3xl mx-auto">
            Enhance image resolution with AI-powered upscaling technology for crystal clear results.
          </p>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 max-w-6xl mx-auto">
          {/* Upload and Controls */}
          <div className="bg-white rounded-xl shadow-sm p-6">
            <h2 className="text-2xl font-semibold text-gray-900 mb-6">Upload Image</h2>
            
            {/* Upscaling Factor */}
            <div className="mb-6">
              <label className="block text-sm font-medium text-gray-700 mb-2">Upscaling Factor</label>
              <div className="grid grid-cols-3 gap-2">
                {[1, 2, 4].map((factor) => (
                  <label key={factor} className="flex items-center">
                    <input
                      type="radio"
                      name="upscalingFactor"
                      value={factor}
                      checked={upscalingFactor === factor}
                      onChange={(e) => setUpscalingFactor(parseInt(e.target.value))}
                      className="h-4 w-4 text-indigo-600 focus:ring-indigo-500 border-gray-300"
                    />
                    <span className="ml-2 text-sm text-gray-700">{factor}x</span>
                  </label>
                ))}
              </div>
            </div>

            {/* File Upload */}
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

            {/* Action Button */}
            <button
              onClick={handleUpscaleImage}
              disabled={loading || !selectedFile}
              className="btn btn-primary w-full"
            >
              {loading ? (
                <>
                  <span className="loading-spinner mr-2"></span>
                  Upscaling...
                </>
              ) : (
                `Upscale Image ${upscalingFactor}x`
              )}
            </button>
          </div>

          {/* Results */}
          <div className="bg-white rounded-xl shadow-sm p-6">
            <h2 className="text-2xl font-semibold text-gray-900 mb-6">Upscaled Result</h2>
            
            {resultUrl ? (
              <div className="space-y-6">
                <div>
                  <h3 className="text-lg font-medium text-gray-900 mb-2">Upscaled Image</h3>
                  <div className="border rounded-lg p-4 bg-gray-50 relative">
                    <img
                      src={resultUrl}
                      alt="Result"
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
                    className="btn btn-primary flex-1 min-w-[120px]">
                    <FaDownload className="mr-2" /> Download
                  </button>

                  <button className="btn btn-outline flex-1 min-w-[120px]">
                    <FaEye className="mr-2" /> Preview
                  </button>
                </div>
              </div>
            ) : (
              <div className="flex flex-col items-center justify-center h-64 border-2 border-dashed border-gray-300 rounded-lg">
                <FaExpand className="text-gray-400 text-4xl mb-4" />
                <p className="text-gray-500 text-center">
                  {selectedFile 
                    ? 'Click "Upscale Image" to enhance your image resolution' 
                    : 'Upload an image to start upscaling'
                  }
                </p>
              </div>
            )}
          </div>
        </div>

        {/* Features Section */}
        <div className="mt-16">
          <h2 className="text-3xl font-bold text-gray-900 text-center mb-12">AI-Powered Image Enhancement</h2>
          
          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            <div className="bg-white p-6 rounded-xl shadow-sm">
              <div className="w-12 h-12 bg-gradient-to-r from-blue-500 to-purple-600 rounded-lg flex items-center justify-center mb-4">
                <FaExpand className="text-white text-xl" />
              </div>
              <h3 className="text-lg font-semibold text-gray-900 mb-2">Super Resolution</h3>
              <p className="text-gray-600">
                Our AI models use advanced super-resolution techniques to enhance image details and clarity.
              </p>
            </div>
            
            <div className="bg-white p-6 rounded-xl shadow-sm">
              <div className="w-12 h-12 bg-gradient-to-r from-green-500 to-teal-600 rounded-lg flex items-center justify-center mb-4">
                <FaExpand className="text-white text-xl" />
              </div>
              <h3 className="text-lg font-semibold text-gray-900 mb-2">Noise Reduction</h3>
              <p className="text-gray-600">
                Advanced algorithms reduce noise and artifacts while preserving important image details.
              </p>
            </div>
            
            <div className="bg-white p-6 rounded-xl shadow-sm">
              <div className="w-12 h-12 bg-gradient-to-r from-pink-500 to-rose-600 rounded-lg flex items-center justify-center mb-4">
                <FaExpand className="text-white text-xl" />
              </div>
              <h3 className="text-lg font-semibold text-gray-900 mb-2">Detail Enhancement</h3>
              <p className="text-gray-600">
                AI-powered enhancement brings out fine details that may be lost in lower resolution images.
              </p>
            </div>
          </div>
        </div>

        {/* Comparison Section */}
        <div className="mt-16 bg-white rounded-xl shadow-sm p-8">
          <h2 className="text-3xl font-bold text-gray-900 text-center mb-8">Before & After Comparison</h2>
          
          <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
            <div className="text-center">
              <h3 className="text-xl font-semibold text-gray-900 mb-4">Original Image</h3>
              <div className="border-2 border-dashed border-gray-300 rounded-lg p-8">
                <div className="bg-gray-200 border-2 border-dashed rounded-xl w-full h-48 flex items-center justify-center">
                  <span className="text-gray-500">Original Image</span>
                </div>
              </div>
            </div>
            
            <div className="text-center">
              <h3 className="text-xl font-semibold text-gray-900 mb-4">Upscaled Image</h3>
              <div className="border-2 border-dashed border-gray-300 rounded-lg p-8">
                <div className="bg-gradient-to-r from-blue-500 to-purple-600 rounded-xl w-full h-48 flex items-center justify-center">
                  <span className="text-white font-medium">Enhanced & Upscaled</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ImageUpscalerPage;