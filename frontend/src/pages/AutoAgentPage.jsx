import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { useNavigate } from 'react-router-dom';
import { useLanguage } from '../contexts/LanguageContext';
import { FiUpload, FiSend, FiImage, FiLoader, FiCheck, FiX, FiDownload } from 'react-icons/fi';
import { FaRobot } from 'react-icons/fa';
import toast from 'react-hot-toast';
import axios from 'axios';
import WalkingRobotAgent from '../components/WalkingRobotAgent';

const AutoAgentPage = () => {
  const navigate = useNavigate();
  const [selectedImage, setSelectedImage] = useState(null);
  const [imagePreview, setImagePreview] = useState(null);
  const [instruction, setInstruction] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [resultImage, setResultImage] = useState(null);
  const [isProcessing, setIsProcessing] = useState(false);
  const { t } = useLanguage();

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
      setResultImage(null); // Reset result when new image is selected
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!selectedImage) {
      toast.error('Please select an image first');
      return;
    }
    
    if (!instruction.trim()) {
      toast.error('Please enter an instruction');
      return;
    }

    setIsLoading(true);
    setIsProcessing(true);

    try {
      const formData = new FormData();
      formData.append('image', selectedImage);
      formData.append('instruction', instruction);

      // Use public auto agent endpoint for now (can be changed to authenticated version)
      const response = await axios.post(
        `${import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'}/api/public-auto-agent`,
        formData,
        {
          headers: {
            'Content-Type': 'multipart/form-data',
          },
          responseType: 'blob', // Important for handling binary image response
        }
      );

      // Convert the response to a URL for display
      const imageUrl = URL.createObjectURL(response.data);
      setResultImage(imageUrl);
      toast.success('Image processed successfully!');
    } catch (error) {
      console.error('Error processing image:', error);
      toast.error('Error processing image. Please try again.');
    } finally {
      setIsLoading(false);
      setIsProcessing(false);
    }
  };

  const resetForm = () => {
    setSelectedImage(null);
    setImagePreview(null);
    setInstruction('');
    setResultImage(null);
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 py-8 px-4">
      <div className="max-w-4xl mx-auto">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
          className="bg-white rounded-2xl shadow-xl p-6 md:p-8"
        >
          <div className="text-center mb-8">
            <h1 className="text-3xl md:text-4xl font-bold text-gray-800 mb-2">
              AI Auto Agent
            </h1>
            <p className="text-gray-600">
              Upload an image and give the AI natural language instructions. Our intelligent agent will analyze your request and perform the appropriate image processing tasks.
            </p>
          </div>

          <form onSubmit={handleSubmit} className="space-y-6">
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
                  {t('chooseFile')}
                </label>
              </div>
            </div>

            {/* Instruction Input */}
            <div className="space-y-4">
              <label className="block text-lg font-medium text-gray-700">
                {t('whatShouldAIDo')}
              </label>

              {/* Example instruction buttons */}
              <div className="flex flex-wrap gap-2 mb-3">
                {[
                  t('removeBackgroundExample'),
                  t('changeBackgroundExample'),
                  t('enhanceImageExample'),
                  t('vibrantColorsExample'),
                  t('changeBackgroundAndEnhanceExample')
                ].map((example, index) => (
                  <button
                    key={index}
                    type="button"
                    onClick={() => setInstruction(example)}
                    className="px-3 py-1.5 text-sm bg-indigo-100 text-indigo-700 rounded-lg hover:bg-indigo-200 transition-colors"
                  >
                    {example}
                  </button>
                ))}
              </div>

              <textarea
                value={instruction}
                onChange={(e) => setInstruction(e.target.value)}
                placeholder={t('instructionPlaceholder')}
                className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 min-h-32 resize-none"
                disabled={isLoading}
              />
              <p className="text-sm text-gray-500">
                {t('instructionDescription')}
              </p>
            </div>

            {/* Action Buttons */}
            <div className="flex flex-col sm:flex-row gap-4">
              <button
                type="submit"
                disabled={isLoading || !selectedImage || !instruction.trim()}
                className="flex-1 flex items-center justify-center px-6 py-3 bg-gradient-to-r from-indigo-600 to-purple-600 text-white rounded-lg hover:from-indigo-700 hover:to-purple-700 disabled:opacity-50 disabled:cursor-not-allowed transition-all"
              >
                {isLoading ? (
                  <>
                    <FiLoader className="animate-spin mr-2" />
                    {t('processing')}
                  </>
                ) : (
                  <>
                    <FiSend className="mr-2" />
                    {t('processWithAI')}
                  </>
                )}
              </button>
              
              <button
                type="button"
                onClick={resetForm}
                className="px-6 py-3 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 transition-colors"
              >
                {t('reset')}
              </button>
            </div>
          </form>

          {/* Result Section */}
          {isProcessing && (
            <div className="mt-8 p-6 bg-blue-50 rounded-xl text-center">
              <FiLoader className="w-8 h-8 text-blue-600 animate-spin mx-auto mb-4" />
              <p className="text-gray-700">{t('processingWithAI')}</p>
            </div>
          )}

          {resultImage && !isProcessing && (
            <div className="mt-8">
              <h2 className="text-xl font-semibold text-gray-800 mb-4 flex items-center">
                <FiCheck className="text-green-500 mr-2" />
                {t('result')}
              </h2>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div>
                  <h3 className="text-sm font-medium text-gray-500 mb-2">{t('original')}</h3>
                  <img
                    src={imagePreview}
                    alt="Original"
                    className="w-full h-auto rounded-lg border border-gray-200"
                  />
                </div>
                <div>
                  <h3 className="text-sm font-medium text-gray-500 mb-2">{t('processed')}</h3>
                  <img
                    src={resultImage}
                    alt="Processed"
                    className="w-full h-auto rounded-lg border border-gray-200"
                  />
                </div>
              </div>
              
              <div className="mt-6 flex justify-center">
                <a
                  href={resultImage}
                  download="auto-agent-result.png"
                  className="inline-flex items-center px-6 py-3 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors"
                >
                  <FiDownload className="mr-2" />
                  {t('downloadResult')}
                </a>
              </div>
            </div>
          )}
        </motion.div>

        {/* Walking Robot Agent */}
        <WalkingRobotAgent
          onPageGuidance={(text) => {
            // This could be used to trigger speech synthesis if needed
            console.log("Agent guidance:", text);
          }}
        />
      </div>
    </div>
  );
};

export default AutoAgentPage;