import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { useLanguage } from '../contexts/LanguageContext';
import { useAuth } from '../contexts/AuthContext';
import toast from 'react-hot-toast';
import axios from 'axios';

const GalleryPage = () => {
  const { user, isAuthenticated, loading } = useAuth();
  const [images, setImages] = useState([]);
  const [loadingImages, setLoadingImages] = useState(false);
  const [activeTab, setActiveTab] = useState('all');
  const { t } = useLanguage();

  const operations = [
    { key: 'all', label: t('allImages') },
    { key: 'remove-background', label: t('backgroundRemoval') },
    { key: 'change-background', label: t('backgroundChange') },
    { key: 'replace-background', label: t('backgroundReplace') },
    { key: 'change-clothes', label: t('clothesChange') },
    { key: 'replace-clothes', label: t('clothesReplace') }
  ];

  useEffect(() => {
    if (isAuthenticated) {
      fetchGalleryImages();
    }
  }, [isAuthenticated, activeTab]);

  const fetchGalleryImages = async () => {
    if (!isAuthenticated) return;

    setLoadingImages(true);
    try {
      let url = '/api/gallery/images';
      if (activeTab !== 'all') {
        url = `/api/gallery/images/${activeTab}`;
      }

      const response = await axios.get(url);
      setImages(response.data.images || []);
    } catch (error) {
      console.error('Error fetching gallery images:', error);
      toast.error('Failed to load gallery images');
    } finally {
      setLoadingImages(false);
    }
  };

  // Mock images for non-authenticated users
  const mockImages = [
    {
      id: 'mock1',
      filename: 'sample1.png',
      path: 'https://images.unsplash.com/photo-1529626455594-4ff0802cfb7e?ixlib=rb-4.0.3&ixid=M3wxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8fA%3D%3D&auto=format&fit=crop&w=687&q=80',
      timestamp: '2023-05-15 14:30:00',
      operation: 'remove-background',
      title: 'Background Removed Sample 1'
    },
    {
      id: 'mock2',
      filename: 'sample2.png',
      path: 'https://images.unsplash.com/photo-1492724441997-5dc865305da7?ixlib=rb-4.0.3&ixid=M3wxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8fA%3D%3D&auto=format&fit=crop&w=1170&q=80',
      timestamp: '2023-05-16 10:15:00',
      operation: 'change-background',
      title: 'Background Changed Sample 2'
    },
    {
      id: 'mock3',
      filename: 'sample3.png',
      path: 'https://images.unsplash.com/photo-1531297484001-80022131f5a1?ixlib=rb-4.0.3&ixid=M3wxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8fA%3D%3D&auto=format&fit=crop&w=1170&q=80',
      timestamp: '2023-05-17 09:45:00',
      operation: 'remove-background',
      title: 'Background Removed Sample 3'
    }
  ];

  const getOperationLabel = (operation) => {
    const op = operations.find(op => op.key === operation);
    return op ? op.label : operation;
  };

  const displayedImages = isAuthenticated ? images : mockImages;

  return (
    <div className="min-h-screen bg-gray-50 py-8">
      <div className="container mx-auto px-4">
        {/* Header */}
        <div className="text-center mb-12">
          <h1 className="text-3xl md:text-4xl font-bold text-gray-900 mb-4">
            {isAuthenticated ? 'Your Gallery' : 'Image Gallery'}
          </h1>
          <p className="text-gray-600 max-w-2xl mx-auto">
            {isAuthenticated 
              ? 'View and manage your processed images' 
              : 'Explore examples of our image processing capabilities'}
          </p>
        </div>

        {/* Login Prompt for Non-Authenticated Users */}
        {!isAuthenticated && (
          <div className="bg-blue-50 border border-blue-200 rounded-lg p-6 mb-8 text-center">
            <h3 className="text-lg font-semibold text-blue-800 mb-2">{t('saveYourWork')}</h3>
            <p className="text-blue-700 mb-4">
              {t('createAccountToSave')}
            </p>
            <div className="flex justify-center gap-4">
              <Link
                to="/login"
                className="bg-indigo-600 text-white px-6 py-2 rounded-lg font-medium hover:bg-indigo-700 transition-colors"
              >
                {t('login')}
              </Link>
              <Link
                to="/signup"
                className="bg-white text-indigo-600 border border-indigo-600 px-6 py-2 rounded-lg font-medium hover:bg-indigo-50 transition-colors"
              >
                {t('signUp')}
              </Link>
            </div>
          </div>
        )}

        {/* Tabs for Authenticated Users */}
        {isAuthenticated && (
          <div className="mb-8">
            <div className="flex flex-wrap gap-2 justify-center">
              {operations.map((op) => (
                <button
                  key={op.key}
                  className={`px-4 py-2 rounded-full text-sm font-medium transition-colors ${
                    activeTab === op.key
                      ? 'bg-indigo-600 text-white'
                      : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
                  }`}
                  onClick={() => setActiveTab(op.key)}
                >
                  {op.label}
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Gallery Loading State */}
        {loadingImages && (
          <div className="flex justify-center py-12">
            <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-indigo-600"></div>
          </div>
        )}

        {/* Gallery Content */}
        {!loadingImages && (
          <div>
            {displayedImages.length > 0 ? (
              <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-6">
                {displayedImages.map((image) => (
                  <div key={image.id} className="bg-white rounded-xl shadow-sm overflow-hidden hover:shadow-md transition-shadow">
                    <div className="aspect-square bg-gray-100 flex items-center justify-center p-4">
                      <img
                        src={image.path.startsWith('http') ? image.path : image.path}
                        alt={image.title}
                        className="w-full h-full object-contain rounded-lg"
                        onError={(e) => {
                          e.target.src = 'https://placehold.co/300x300?text=Image+Not+Found';
                        }}
                      />
                    </div>
                    <div className="p-4">
                      <h3 className="font-medium text-gray-900 truncate">{image.title}</h3>
                      <div className="mt-2 flex justify-between items-center text-sm text-gray-500">
                        <span>{new Date(image.timestamp).toLocaleDateString()}</span>
                        <span className="bg-gray-100 px-2 py-1 rounded text-xs">
                          {getOperationLabel(image.operation)}
                        </span>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-center py-12">
                <div className="text-gray-400 mb-4">{t('noImagesFound')}</div>
                <p className="text-gray-600 mb-6">
                  {isAuthenticated
                    ? t('processImagesToSee')
                    : t('tryServicesToSee')}
                </p>
                <Link
                  to="/services"
                  className="inline-flex items-center px-6 py-3 border border-transparent text-base font-medium rounded-md text-white bg-gradient-to-r from-indigo-600 to-purple-600 hover:opacity-90 transition-opacity"
                >
                  {t('tryOurServices')}
                </Link>
              </div>
            )}
          </div>
        )}

        {/* Call to Action for Non-Authenticated Users */}
        {!isAuthenticated && (
          <div className="mt-12 bg-gradient-to-r from-indigo-600 to-purple-600 rounded-xl text-white p-8 text-center">
            <h2 className="text-2xl md:text-3xl font-bold mb-4">{t('readyToProcess')}</h2>
            <p className="text-lg mb-6 max-w-2xl mx-auto">
              {t('startUsingAIPowered')}
            </p>
            <div className="flex flex-col sm:flex-row justify-center gap-4">
              <Link
                to="/services"
                className="bg-white text-indigo-600 px-8 py-4 rounded-lg text-lg font-semibold hover:bg-gray-100 transition-colors"
              >
                {t('startProcessing')}
              </Link>
              <Link
                to="/signup"
                className="bg-transparent border-2 border-white text-white px-8 py-4 rounded-lg text-lg font-semibold hover:bg-white hover:text-indigo-600 transition-colors"
              >
                {t('createAccount')}
              </Link>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default GalleryPage;