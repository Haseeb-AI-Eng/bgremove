import React from 'react';
import { Link } from 'react-router-dom';
import { useLanguage } from '../contexts/LanguageContext';
import { FaMagic, FaFileAlt, FaPalette, FaEye, FaRocket, FaShieldAlt, FaImage, FaCameraRetro, FaUser, FaInfoCircle, FaFileExport, FaCrop } from 'react-icons/fa';
import ServiceCard from '../components/ServiceCard';

const ServicesPage = () => {
  const { t } = useLanguage();

  const services = [
    {
      id: 1,
      title: t('imageProcessingSuite'),
      description: t('advancedBackgroundRemoval'),
      icon: <FaMagic className="text-3xl" />,
      path: '/services/image-processing',
      color: 'from-blue-500 to-purple-600'
    },
    {
      id: 2,
      title: t('aiCvGenerator'),
      description: t('createProfessionalCvs'),
      icon: <FaFileAlt className="text-3xl" />,
      path: '/services/cv-generator',
      color: 'from-green-500 to-teal-600'
    },
    {
      id: 3,
      title: t('colorPaletteGenerator'),
      description: t('extractAndGenerate'),
      icon: <FaPalette className="text-3xl" />,
      path: '/services/color-palette',
      color: 'from-pink-500 to-rose-600'
    },
    {
      id: 4,
      title: t('objectDetectionTool'),
      description: t('identifyAndLocate'),
      icon: <FaEye className="text-3xl" />,
      path: '/services/object-detection',
      color: 'from-yellow-500 to-orange-600'
    },
    {
      id: 5,
      title: t('imageUpscaler'),
      description: t('enhanceImageResolution'),
      icon: <FaRocket className="text-3xl" />,
      path: '/services/image-upscaler',
      color: 'from-indigo-500 to-blue-600'
    },
    {
      id: 6,
      title: t('backgroundBlur'),
      description: t('applyProfessionalPortrait'),
      icon: <FaCameraRetro className="text-3xl" />,
      path: '/services/background-blur',
      color: 'from-purple-500 to-indigo-600'
    },
    {
      id: 7,
      title: t('imageEditingSuite'),
      description: t('advancedImageEditing'),
      icon: <FaCrop className="text-3xl" />,
      path: '/services/image-editing',
      color: 'from-purple-500 to-indigo-600'
    },
    {
      id: 8,
      title: t('faceDetection'),
      description: t('detectFacesAndAutomatically'),
      icon: <FaUser className="text-3xl" />,
      path: '/services/face-detection',
      color: 'from-red-500 to-pink-600'
    },
    {
      id: 9,
      title: t('imageMetadataAnalyzer'),
      description: t('extractDetailedExif'),
      icon: <FaInfoCircle className="text-3xl" />,
      path: '/services/metadata-analyzer',
      color: 'from-cyan-500 to-blue-600'
    },
    {
      id: 10,
      title: t('formatConverter'),
      description: t('convertBetweenImage'),
      icon: <FaFileExport className="text-3xl" />,
      path: '/services/format-converter',
      color: 'from-emerald-500 to-teal-600'
    },
    {
      id: 11,
      title: t('aiAutoAgent'),
      description: t('uploadImageAndTell'),
      icon: <FaMagic className="text-3xl" />,
      path: '/auto-agent',
      color: 'from-indigo-600 to-purple-700'
    },
    {
      id: 12,
      title: t('watermarkRemoval'),
      description: t('removeWatermarkDescription'),
      icon: <FaShieldAlt className="text-3xl" />,
      path: '/services/watermark-removal',
      color: 'from-red-500 to-pink-600'
    },
    {
      id: 13,
      title: t('imageUpscaler'),
      description: t('enhanceImageResolution'),
      icon: <FaMagic className="text-3xl" />,
      path: '/services/image-enhancement',
      color: 'from-yellow-500 to-orange-600'
    }
  ];

  return (
    <div className="min-h-screen bg-gray-50 py-12">
      <div className="container mx-auto px-4">
        {/* Header */}
        <div className="text-center mb-12">
          <h1 className="text-4xl md:text-5xl font-bold text-gray-900 mb-4">
            {t('imageProcessingSuite')}
          </h1>
          <p className="text-xl text-gray-600 max-w-3xl mx-auto">
            {t('exploreOurSuite')}
          </p>
        </div>

        {/* Services Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8 mb-12">
          {services.map((service) => (
            <ServiceCard key={service.id} service={service} />
          ))}
        </div>

        {/* Service Categories */}
        <div className="bg-white rounded-xl shadow-sm p-8 mb-12">
          <h2 className="text-2xl font-bold text-gray-900 mb-6">{t('serviceCategories')}</h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div className="border border-gray-200 rounded-lg p-6">
              <div className="w-12 h-12 bg-gradient-to-r from-blue-500 to-purple-600 rounded-lg flex items-center justify-center mb-4">
                <FaImage className="text-white text-xl" />
              </div>
              <h3 className="text-lg font-semibold text-gray-900 mb-2">{t('imageProcessing')}</h3>
              <p className="text-gray-600 mb-4">{t('advancedTools')}</p>
              <Link to="/services/image-processing" className="text-indigo-600 font-medium hover:underline">
                {t('explore')}
              </Link>
            </div>

            <div className="border border-gray-200 rounded-lg p-6">
              <div className="w-12 h-12 bg-gradient-to-r from-green-500 to-teal-600 rounded-lg flex items-center justify-center mb-4">
                <FaFileAlt className="text-white text-xl" />
              </div>
              <h3 className="text-lg font-semibold text-gray-900 mb-2">{t('contentGeneration')}</h3>
              <p className="text-gray-600 mb-4">{t('aiPoweredTools')}</p>
              <Link to="/services/cv-generator" className="text-indigo-600 font-medium hover:underline">
                {t('explore')}
              </Link>
            </div>

            <div className="border border-gray-200 rounded-lg p-6">
              <div className="w-12 h-12 bg-gradient-to-r from-pink-500 to-rose-600 rounded-lg flex items-center justify-center mb-4">
                <FaPalette className="text-white text-xl" />
              </div>
              <h3 className="text-lg font-semibold text-gray-900 mb-2">{t('designTools')}</h3>
              <p className="text-gray-600 mb-4">{t('creativeTools')}</p>
              <Link to="/services/color-palette" className="text-indigo-600 font-medium hover:underline">
                {t('explore')}
              </Link>
            </div>
          </div>
        </div>

        {/* CTA Section */}
        <div className="bg-gradient-to-r from-indigo-600 to-purple-600 rounded-xl text-white p-8 text-center">
          <h2 className="text-2xl md:text-3xl font-bold mb-4">{t('readyToGetStarted')}</h2>
          <p className="text-lg mb-6 max-w-2xl mx-auto">
            {t('joinThousands')}
          </p>
          <div className="flex flex-col sm:flex-row justify-center gap-4">
            <Link
              to="/signup"
              className="bg-white text-indigo-600 px-6 py-3 rounded-lg font-semibold hover:bg-gray-100 transition-colors"
            >
              {t('createFreeAccount')}
            </Link>
            <Link
              to="/pricing"
              className="bg-transparent border-2 border-white text-white px-6 py-3 rounded-lg font-semibold hover:bg-white hover:text-indigo-600 transition-colors"
            >
              {t('viewPricing')}
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ServicesPage;