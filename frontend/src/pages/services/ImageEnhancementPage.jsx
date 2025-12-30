import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { FiUpload, FiSliders, FiImage, FiLoader, FiCheck, FiX, FiDownload, FiSun, FiSettings } from 'react-icons/fi';
import toast from 'react-hot-toast';
import axios from 'axios';

const ImageEnhancementPage = () => {
  const [selectedImage, setSelectedImage] = useState(null);
  const [imagePreview, setImagePreview] = useState(null);
  const [enhancedImage, setEnhancedImage] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [strength, setStrength] = useState(1.0);
  const [sharpenOnly, setSharpenOnly] = useState(false);

  const handleImageChange = (e) => {
    const file = e.target.files[0];
    if (file) {
      if (!file.type.match('image.*')) {
        toast.error('Please select a valid image file');
        return;
      }

      setSelectedImage(file);
      const reader = new FileReader();
      reader.onloadend = () => {
        setImagePreview(reader.result);
      };
      reader.readAsDataURL(file);
      setEnhancedImage(null); // Reset result when new image is selected
    }
  };

  const handleEnhance = async () => {
    if (!selectedImage) {
      toast.error('Please select an image first');
      return;
    }

    setIsLoading(true);

    try {
      const formData = new FormData();
      formData.append('image', selectedImage);
      formData.append('strength', strength);
      formData.append('sharpen_only', sharpenOnly);

      const response = await axios.post(
        `${import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'}/api/public-enhance-image`,
        formData,
        {
          headers: {
            'Content-Type': 'multipart/form-data',
          },
          responseType: 'blob',
        }
      );

      // Convert the response to a URL for display
      const imageUrl = URL.createObjectURL(response.data);
      setEnhancedImage(imageUrl);
      toast.success('Image enhanced successfully!');
    } catch (error) {
      console.error('Error enhancing image:', error);
      toast.error('Error enhancing image. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };

  const resetForm = () => {
    setSelectedImage(null);
    setImagePreview(null);
    setEnhancedImage(null);
    setStrength(1.0);
    setSharpenOnly(false);
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 py-8 px-4">
      <div className="max-w-6xl mx-auto">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
          className="bg-white rounded-2xl shadow-xl p-6 md:p-8"
        >
          <div className="text-center mb-8">
            <h1 className="text-3xl md:text-4xl font-bold text-gray-800 mb-2 flex items-center justify-center">
              <FiSun className="mr-3 text-yellow-500" />
              AI Image Enhancement
            </h1>
            <p className="text-gray-600">
              Upload your image and apply powerful AI-powered enhancement and sharpening to dramatically improve image quality.
            </p>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
            {/* Upload and Settings Panel */}
            <div className="space-y-6">
              {/* Image Upload Section */}
              <div className="space-y-4">
                <label className="block text-lg font-medium text-gray-700">
                  Upload Image
                </label>

                <div className="border-2 border-dashed border-gray-300 rounded-xl p-8 text-center hover:border-indigo-400 transition-colors">
                  {imagePreview ? (
                    <div className="flex flex-col items-center">
                      <img
                        src={imagePreview}
                        alt="Preview"
                        className="max-h-64 object-contain rounded-lg mb-4"
                      />
                      <p className="text-sm text-gray-500 mb-2">
                        {selectedImage?.name} ({(selectedImage?.size / 1024 / 1024).toFixed(2)} MB)
                      </p>
                      <button
                        type="button"
                        onClick={() => setSelectedImage(null)}
                        className="text-red-500 hover:text-red-700 flex items-center"
                      >
                        <FiX className="mr-1" /> Remove
                      </button>
                    </div>
                  ) : (
                    <div className="flex flex-col items-center">
                      <FiImage className="w-12 h-12 text-gray-400 mb-4" />
                      <p className="text-gray-600 mb-2">Click to upload an image</p>
                      <p className="text-sm text-gray-500">PNG, JPG, JPEG (Max 10MB)</p>
                    </div>
                  )}

                  <input
                    type="file"
                    accept="image/*"
                    onChange={handleImageChange}
                    className="hidden"
                    id="image-upload"
                  />
                  <label
                    htmlFor="image-upload"
                    className="inline-flex items-center px-6 py-3 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 cursor-pointer transition-colors mt-4"
                  >
                    <FiUpload className="mr-2" />
                    Choose File
                  </label>
                </div>
              </div>

              {/* Enhancement Settings */}
              <div className="space-y-4">
                <h3 className="text-lg font-medium text-gray-700 flex items-center">
                  <FiSliders className="mr-2 text-indigo-600" />
                  Enhancement Settings
                </h3>

                <div className="space-y-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Enhancement Strength: {strength.toFixed(1)}
                    </label>
                    <input
                      type="range"
                      min="0.5"
                      max="2.0"
                      step="0.1"
                      value={strength}
                      onChange={(e) => setStrength(parseFloat(e.target.value))}
                      className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer slider"
                      disabled={isLoading}
                    />
                    <div className="flex justify-between text-xs text-gray-500 mt-1">
                      <span>Mild</span>
                      <span>Standard</span>
                      <span>Strong</span>
                    </div>
                  </div>

                  <div className="flex items-center">
                    <input
                      type="checkbox"
                      id="sharpen-only"
                      checked={sharpenOnly}
                      onChange={(e) => setSharpenOnly(e.target.checked)}
                      className="w-4 h-4 text-indigo-600 border-gray-300 rounded focus:ring-indigo-500"
                      disabled={isLoading}
                    />
                    <label htmlFor="sharpen-only" className="ml-2 block text-sm text-gray-700">
                      Sharpness only (faster processing)
                    </label>
                  </div>
                </div>
              </div>

              {/* Action Buttons */}
              <div className="flex flex-col sm:flex-row gap-4">
                <button
                  onClick={handleEnhance}
                  disabled={isLoading || !selectedImage}
                  className="flex-1 flex items-center justify-center px-6 py-3 bg-gradient-to-r from-indigo-600 to-purple-600 text-white rounded-lg hover:from-indigo-700 hover:to-purple-700 disabled:opacity-50 disabled:cursor-not-allowed transition-all"
                >
                  {isLoading ? (
                    <>
                      <FiLoader className="animate-spin mr-2" />
                      Enhancing...
                    </>
                  ) : (
                    <>
                      <FiSun className="mr-2" />
                      Enhance Image
                    </>
                  )}
                </button>

                <button
                  type="button"
                  onClick={resetForm}
                  className="px-6 py-3 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 transition-colors"
                >
                  Reset
                </button>
              </div>
            </div>

            {/* Results Panel */}
            <div className="space-y-6">
              <h3 className="text-lg font-medium text-gray-700">Results</h3>

              {isLoading && (
                <div className="p-8 bg-blue-50 rounded-xl text-center">
                  <FiLoader className="w-8 h-8 text-blue-600 animate-spin mx-auto mb-4" />
                  <p className="text-gray-700">Enhancing your image with AI...</p>
                  <p className="text-sm text-gray-500 mt-2">Applying advanced sharpening and quality enhancement</p>
                </div>
              )}

              {!isLoading && imagePreview && !enhancedImage && (
                <div className="p-8 bg-gray-50 rounded-xl text-center">
                  <FiSettings className="w-12 h-12 text-gray-400 mx-auto mb-4" />
                  <p className="text-gray-600">Upload an image and click "Enhance Image" to see the results</p>
                </div>
              )}

              {enhancedImage && (
                <div className="space-y-6">
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div className="text-center">
                      <h4 className="text-sm font-medium text-gray-500 mb-2">Original</h4>
                      <img
                        src={imagePreview}
                        alt="Original"
                        className="w-full h-auto rounded-lg border border-gray-200"
                      />
                    </div>
                    <div className="text-center">
                      <h4 className="text-sm font-medium text-gray-500 mb-2">Enhanced</h4>
                      <img
                        src={enhancedImage}
                        alt="Enhanced"
                        className="w-full h-auto rounded-lg border border-gray-200"
                      />
                    </div>
                  </div>

                  <div className="flex justify-center">
                    <a
                      href={enhancedImage}
                      download="enhanced-image.png"
                      className="inline-flex items-center px-6 py-3 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors"
                    >
                      <FiDownload className="mr-2" />
                      Download Enhanced Image
                    </a>
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* Features Section */}
          <div className="mt-12">
            <h2 className="text-2xl font-bold text-gray-800 mb-6 text-center">Advanced Image Enhancement Features</h2>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              <div className="bg-gradient-to-br from-blue-50 to-indigo-50 p-6 rounded-xl">
                <div className="w-12 h-12 bg-indigo-100 rounded-lg flex items-center justify-center mb-4">
                  <FiSun className="w-6 h-6 text-indigo-600" />
                </div>
                <h3 className="text-lg font-semibold text-gray-800 mb-2">AI-Powered Enhancement</h3>
                <p className="text-gray-600">Advanced algorithms that intelligently enhance image quality while preserving details.</p>
              </div>
              
              <div className="bg-gradient-to-br from-purple-50 to-pink-50 p-6 rounded-xl">
                <div className="w-12 h-12 bg-purple-100 rounded-lg flex items-center justify-center mb-4">
                  <FiSettings className="w-6 h-6 text-purple-600" />
                </div>
                <h3 className="text-lg font-semibold text-gray-800 mb-2">Adjustable Strength</h3>
                <p className="text-gray-600">Fine-tune enhancement strength from subtle to dramatic improvements.</p>
              </div>
              
              <div className="bg-gradient-to-br from-green-50 to-teal-50 p-6 rounded-xl">
                <div className="w-12 h-12 bg-green-100 rounded-lg flex items-center justify-center mb-4">
                  <FiSliders className="w-6 h-6 text-green-600" />
                </div>
                <h3 className="text-lg font-semibold text-gray-800 mb-2">Multiple Options</h3>
                <p className="text-gray-600">Choose between full enhancement or sharpness-only processing.</p>
              </div>
            </div>
          </div>
        </motion.div>
      </div>
    </div>
  );
};

export default ImageEnhancementPage;