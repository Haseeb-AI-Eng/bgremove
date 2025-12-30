import React, { useState, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { useAuth } from '../../contexts/AuthContext';
import { useLanguage } from '../../contexts/LanguageContext';
import { FaUpload, FaDownload, FaSpinner, FaShieldAlt, FaLock } from 'react-icons/fa';

const WatermarkRemovalPage = () => {
  const [selectedFile, setSelectedFile] = useState(null);
  const [previewUrl, setPreviewUrl] = useState(null);
  const [resultUrl, setResultUrl] = useState(null);
  const [isProcessing, setIsProcessing] = useState(false);
  const [error, setError] = useState(null);
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const fileInputRef = useRef(null);
  const { user, isAuthenticated: authStatus } = useAuth();
  const { t } = useLanguage();
  const navigate = useNavigate();

  // Check authentication status
  React.useEffect(() => {
    setIsAuthenticated(authStatus);
  }, [authStatus]);

  const handleFileChange = (event) => {
    const file = event.target.files[0];
    if (file) {
      if (file.size > 10 * 1024 * 1024) { // 10MB limit
        setError(t('fileTooLarge'));
        return;
      }

      const validTypes = ['image/jpeg', 'image/jpg', 'image/png', 'image/gif', 'image/webp'];
      if (!validTypes.includes(file.type)) {
        setError(t('invalidFileType'));
        return;
      }

      setSelectedFile(file);
      setPreviewUrl(URL.createObjectURL(file));
      setResultUrl(null);
      setError(null);
    }
  };

  const handleProcess = async () => {
    if (!selectedFile) {
      setError(t('pleaseSelectFile'));
      return;
    }

    if (!isAuthenticated) {
      setError(t('loginRequired'));
      navigate('/login');
      return;
    }

    setIsProcessing(true);
    setError(null);

    try {
      const formData = new FormData();
      formData.append('file', selectedFile);

      // Use axios to make the API call with proper authentication
      const response = await axios.post('/api/watermark-removal', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        },
        responseType: 'blob' // Important: specify that we expect a blob response
      });

      // Create a blob URL from the response
      const resultBlob = new Blob([response.data], { type: 'image/png' });
      const resultUrl = URL.createObjectURL(resultBlob);
      setResultUrl(resultUrl);
    } catch (err) {
      setError(t('errorProcessingImage'));
      console.error('Error processing image:', err);
    } finally {
      setIsProcessing(false);
    }
  };

  const handleDownload = () => {
    if (resultUrl) {
      const link = document.createElement('a');
      link.href = resultUrl;
      link.download = `watermark-removed-${Date.now()}.png`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
    }
  };

  const handleNewImage = () => {
    setSelectedFile(null);
    setPreviewUrl(null);
    setResultUrl(null);
    setError(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 py-8">
      <div className="container mx-auto px-4 max-w-4xl">
        <div className="text-center mb-8">
          <h1 className="text-3xl md:text-4xl font-bold text-gray-900 mb-4 flex items-center justify-center">
            <FaShieldAlt className="mr-3 text-red-500" />
            {t('watermarkRemoval')}
          </h1>
          <p className="text-lg text-gray-600">
            {t('removeWatermarkDescription')}
          </p>
        </div>

        {!isAuthenticated ? (
          <div className="bg-red-50 border border-red-200 rounded-lg p-6 mb-8 text-center">
            <FaLock className="text-red-500 text-3xl mx-auto mb-3" />
            <h3 className="text-xl font-semibold text-red-800 mb-2">{t('loginRequired')}</h3>
            <p className="text-red-700 mb-4">{t('loginToAccessWatermarkRemoval')}</p>
            <button
              onClick={() => navigate('/login')}
              className="bg-red-600 text-white px-6 py-2 rounded-lg font-medium hover:bg-red-700 transition-colors"
            >
              {t('login')}
            </button>
          </div>
        ) : (
          <div className="bg-white rounded-xl shadow-sm p-6 mb-8">
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
              {/* Upload Section */}
              <div>
                <h2 className="text-xl font-semibold text-gray-900 mb-4">{t('uploadImage')}</h2>
                
                <div className="border-2 border-dashed border-gray-300 rounded-lg p-8 text-center hover:border-indigo-400 transition-colors">
                  {previewUrl ? (
                    <div className="space-y-4">
                      <img
                        src={previewUrl}
                        alt="Preview"
                        className="max-h-64 mx-auto rounded-lg shadow-sm"
                      />
                      <button
                        onClick={() => fileInputRef.current?.click()}
                        className="text-indigo-600 hover:text-indigo-800 font-medium"
                      >
                        {t('chooseDifferentImage')}
                      </button>
                    </div>
                  ) : (
                    <div className="space-y-4">
                      <div className="mx-auto w-16 h-16 bg-gray-100 rounded-full flex items-center justify-center">
                        <FaUpload className="text-gray-400 text-2xl" />
                      </div>
                      <div>
                        <p className="text-gray-600 mb-2">{t('dragAndDrop')}</p>
                        <p className="text-sm text-gray-500 mb-4">{t('maxFileSize')}</p>
                        <button
                          onClick={() => fileInputRef.current?.click()}
                          className="bg-indigo-600 text-white px-4 py-2 rounded-lg font-medium hover:bg-indigo-700 transition-colors"
                        >
                          {t('browseFiles')}
                        </button>
                      </div>
                    </div>
                  )}
                  
                  <input
                    type="file"
                    ref={fileInputRef}
                    onChange={handleFileChange}
                    accept="image/*"
                    className="hidden"
                  />
                </div>

                {error && (
                  <div className="mt-4 p-3 bg-red-50 text-red-700 rounded-lg text-sm">
                    {error}
                  </div>
                )}

                <div className="mt-6 space-y-3">
                  <button
                    onClick={handleProcess}
                    disabled={!selectedFile || isProcessing}
                    className={`w-full flex items-center justify-center px-4 py-3 rounded-lg font-medium transition-colors ${
                      !selectedFile || isProcessing
                        ? 'bg-gray-300 text-gray-500 cursor-not-allowed'
                        : 'bg-gradient-to-r from-red-500 to-pink-600 text-white hover:opacity-90'
                    }`}
                  >
                    {isProcessing ? (
                      <>
                        <FaSpinner className="animate-spin mr-2" />
                        {t('processing')}
                      </>
                    ) : (
                      <>
                        <FaShieldAlt className="mr-2" />
                        {t('removeWatermark')}
                      </>
                    )}
                  </button>

                  {resultUrl && (
                    <div className="flex gap-3">
                      <button
                        onClick={handleDownload}
                        className="flex-1 flex items-center justify-center bg-green-600 text-white px-4 py-3 rounded-lg font-medium hover:bg-green-700 transition-colors"
                      >
                        <FaDownload className="mr-2" />
                        {t('download')}
                      </button>
                      <button
                        onClick={handleNewImage}
                        className="flex-1 flex items-center justify-center bg-gray-600 text-white px-4 py-3 rounded-lg font-medium hover:bg-gray-700 transition-colors"
                      >
                        {t('newImage')}
                      </button>
                    </div>
                  )}
                </div>
              </div>

              {/* Preview Section */}
              <div>
                <h2 className="text-xl font-semibold text-gray-900 mb-4">{t('result')}</h2>
                
                {resultUrl ? (
                  <div className="border border-gray-200 rounded-lg p-4">
                    <img
                      src={resultUrl}
                      alt="Result"
                      className="w-full h-auto rounded-lg"
                    />
                    <div className="mt-4 text-sm text-gray-600">
                      <p className="flex items-center">
                        <span className="w-3 h-3 bg-green-500 rounded-full mr-2"></span>
                        {t('watermarkSuccessfullyRemoved')}
                      </p>
                    </div>
                  </div>
                ) : (
                  <div className="border-2 border-dashed border-gray-300 rounded-lg p-12 text-center">
                    <div className="mx-auto w-16 h-16 bg-gray-100 rounded-full flex items-center justify-center mb-4">
                      <FaShieldAlt className="text-gray-400 text-2xl" />
                    </div>
                    <p className="text-gray-500">
                      {selectedFile ? t('processedImageWillAppear') : t('processImageToSeeResult')}
                    </p>
                  </div>
                )}
              </div>
            </div>
          </div>
        )}

        {/* How it works section */}
        <div className="bg-white rounded-xl shadow-sm p-6">
          <h2 className="text-2xl font-bold text-gray-900 mb-6">{t('howItWorks')}</h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div className="text-center">
              <div className="w-12 h-12 bg-indigo-100 rounded-full flex items-center justify-center mx-auto mb-4">
                <span className="text-indigo-600 font-bold">1</span>
              </div>
              <h3 className="font-semibold text-gray-900 mb-2">{t('uploadImage')}</h3>
              <p className="text-gray-600 text-sm">{t('uploadImageDescription')}</p>
            </div>
            <div className="text-center">
              <div className="w-12 h-12 bg-indigo-100 rounded-full flex items-center justify-center mx-auto mb-4">
                <span className="text-indigo-600 font-bold">2</span>
              </div>
              <h3 className="font-semibold text-gray-900 mb-2">{t('removeWatermark')}</h3>
              <p className="text-gray-600 text-sm">{t('removeWatermarkDescription')}</p>
            </div>
            <div className="text-center">
              <div className="w-12 h-12 bg-indigo-100 rounded-full flex items-center justify-center mx-auto mb-4">
                <span className="text-indigo-600 font-bold">3</span>
              </div>
              <h3 className="font-semibold text-gray-900 mb-2">{t('downloadResult')}</h3>
              <p className="text-gray-600 text-sm">{t('downloadResultDescription')}</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default WatermarkRemovalPage;