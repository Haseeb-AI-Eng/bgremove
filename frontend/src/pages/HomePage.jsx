import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { useLanguage } from '../contexts/LanguageContext';
import { FaMagic, FaFileAlt, FaPalette, FaEye, FaRocket, FaShieldAlt, FaChartLine, FaGlobe, FaEraser } from 'react-icons/fa';
import ServiceCard from '../components/ServiceCard';
import ImageEditorModal from '../components/ImageEditorModal';

const HomePage = () => {
  const [imageEditorOpen, setImageEditorOpen] = useState(false);
  const [selectedImage, setSelectedImage] = useState(null);
  const { t } = useLanguage();

  const services = [
    {
      id: 1,
      title: t('imageProcessingSuite'),
      description: t('advancedBackgroundRemoval'),
      icon: <FaMagic className="text-3xl" />,
      path: '/services/image-processing',
      image: 'https://images.unsplash.com/photo-1529626455594-4ff0802cfb7e?ixlib=rb-4.0.3&ixid=M3wxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8fA%3D%3D&auto=format&fit=crop&w=1170&q=80',
      color: 'from-blue-500 to-purple-600'
    },
    {
      id: 2,
      title: t('imageUpscaler'),
      description: t('enhanceImageResolution'),
      icon: <FaFileAlt className="text-3xl" />,
      path: '#', // Will be handled by image editor
      image: 'https://images.unsplash.com/photo-1531297484001-80022131f5a1?ixlib=rb-4.0.3&ixid=M3wxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8fA%3D%3D&auto=format&fit=crop&w=1170&q=80',
      color: 'from-green-500 to-teal-600',
      isImageEditor: true // Flag to identify this service as using image editor
    },
    {
      id: 3,
      title: t('objectDetectionTool'),
      description: t('identifyAndLocate'),
      icon: <FaPalette className="text-3xl" />,
      path: '/services/object-detection',
      image: 'https://images.unsplash.com/photo-1519389950473-47ba0277781c?ixlib=rb-4.0.3&ixid=M3wxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8fA%3D%3D&auto=format&fit=crop&w=1170&q=80',
      color: 'from-pink-500 to-rose-600'
    },
    {
      id: 4,
      title: t('colorPaletteGenerator'),
      description: t('extractAndGenerate'),
      icon: <FaEye className="text-3xl" />,
      path: '/services/color-palette',
      image: 'https://images.unsplash.com/photo-1492724441997-5dc865305da7?ixlib=rb-4.0.3&ixid=M3wxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8fA%3D%3D&auto=format&fit=crop&w=1170&q=80',
      color: 'from-yellow-500 to-orange-600'
    },
    {
      id: 5,
      title: t('aiCvGenerator'),
      description: t('createProfessionalCvs'),
      icon: <FaRocket className="text-3xl" />,
      path: '/services/cv-generator',
      image: 'https://images.unsplash.com/photo-1551836022-deb4988cc6c0?ixlib=rb-4.0.3&ixid=M3wxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8fA%3D%3D&auto=format&fit=crop&w=1170&q=80',
      color: 'from-indigo-500 to-blue-600'
    }
  ];

  return (
    <div className="min-h-screen">
      {/* Hero Section */}
      <section className="relative min-h-screen flex items-center justify-center hero-section animated-gradient-bg">
        {/* Content */}
        <div className="container mx-auto px-4 relative z-10">
          <div className="text-center max-w-4xl mx-auto">
            <div className="inline-block mb-6">
              <div className="relative">
                <div className="absolute inset-0 bg-gradient-to-r from-cyan-400 via-purple-500 to-pink-500 rounded-2xl blur-xl opacity-50 animate-gradient-shift"></div>
                <div className="relative bg-white/10 backdrop-blur-sm p-6 rounded-2xl border border-white/20">
                  <FaEraser className="text-6xl text-white" />
                </div>
              </div>
            </div>
            <h1 className="text-4xl md:text-6xl font-bold mb-6 animate-fade-in">
              <span className="text-gray-100 font-semibold tracking-wide drop-shadow-2xl" style={{ textShadow: '2px 2px 4px rgba(0, 0, 0, 0.5), 0 0 20px rgba(255, 255, 255, 0.3)' }}>{t('imageProcessingSuite')}</span>
            </h1>
            <p className="text-xl md:text-2xl mb-8 max-w-3xl mx-auto text-white/90 font-light drop-shadow">
              {t('worldClassAISolutions')}
            </p>
            <Link
              to="/services/image-processing"
              className="bg-gradient-to-r from-rose-600 via-pink-600 to-rose-600 backdrop-blur-sm border-2 border-white/30 text-white px-8 py-4 rounded-lg text-lg font-semibold hover:from-rose-500 hover:via-pink-500 hover:to-rose-500 transition-all shadow-2xl hover:shadow-pink-500/60 hover:scale-105 inline-block"
            >
              {t('removeWatermark')}
            </Link>
          </div>
        </div>
      </section>

      {/* Trust Indicators */}
      <section className="py-12 bg-white">
        <div className="container mx-auto px-4">
          <div className="text-center mb-12">
            <h2 className="text-2xl md:text-3xl font-bold text-gray-900 mb-4">
              {t('exploreOurSuite')}
            </h2>
            <p className="text-gray-600 max-w-2xl mx-auto">
              {t('joinThousands')}
            </p>
          </div>

          <div className="grid grid-cols-2 md:grid-cols-4 gap-8">
            <div className="text-center">
              <div className="text-3xl font-bold text-indigo-600 mb-2">10K+</div>
              <div className="text-gray-600">{t('accounts')}</div>
            </div>
            <div className="text-center">
              <div className="text-3xl font-bold text-indigo-600 mb-2">5M+</div>
              <div className="text-gray-600">{t('imageProcessing')}</div>
            </div>
            <div className="text-center">
              <div className="text-3xl font-bold text-indigo-600 mb-2">99.9%</div>
              <div className="text-gray-600">{t('compliance')}</div>
            </div>
            <div className="text-center">
              <div className="text-3xl font-bold text-indigo-600 mb-2">24/7</div>
              <div className="text-gray-600">{t('support')}</div>
            </div>
          </div>
        </div>
      </section>

      {/* Features Section */}
      <section className="py-16 bg-gray-50">
        <div className="container mx-auto px-4">
          <div className="text-center mb-12">
            <h2 className="text-3xl md:text-4xl font-bold text-gray-900 mb-4">
              {t('serviceCategories')}
            </h2>
            <p className="text-gray-600 max-w-2xl mx-auto">
              {t('exploreOurSuite')}
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-8">
            <div className="bg-white p-6 rounded-xl shadow-sm hover:shadow-md transition-shadow">
              <div className="w-12 h-12 bg-gradient-to-r from-indigo-500 to-purple-600 rounded-lg flex items-center justify-center mb-4">
                <FaChartLine className="text-white text-xl" />
              </div>
              <h3 className="text-lg font-semibold text-gray-900 mb-2">{t('contentGeneration')}</h3>
              <p className="text-gray-600">{t('aiPoweredTools')}</p>
            </div>

            <div className="bg-white p-6 rounded-xl shadow-sm hover:shadow-md transition-shadow">
              <div className="w-12 h-12 bg-gradient-to-r from-green-500 to-teal-600 rounded-lg flex items-center justify-center mb-4">
                <FaGlobe className="text-white text-xl" />
              </div>
              <h3 className="text-lg font-semibold text-gray-900 mb-2">{t('imageProcessing')}</h3>
              <p className="text-gray-600">{t('advancedTools')}</p>
            </div>

            <div className="bg-white p-6 rounded-xl shadow-sm hover:shadow-md transition-shadow">
              <div className="w-12 h-12 bg-gradient-to-r from-pink-500 to-rose-600 rounded-lg flex items-center justify-center mb-4">
                <FaShieldAlt className="text-white text-xl" />
              </div>
              <h3 className="text-lg font-semibold text-gray-900 mb-2">{t('designTools')}</h3>
              <p className="text-gray-600">{t('creativeTools')}</p>
            </div>

            <div className="bg-white p-6 rounded-xl shadow-sm hover:shadow-md transition-shadow">
              <div className="w-12 h-12 bg-gradient-to-r from-yellow-500 to-orange-600 rounded-lg flex items-center justify-center mb-4">
                <FaRocket className="text-white text-xl" />
              </div>
              <h3 className="text-lg font-semibold text-gray-900 mb-2">{t('readyToGetStarted')}</h3>
              <p className="text-gray-600">{t('joinThousands')}</p>
            </div>
          </div>
        </div>
      </section>

      {/* Services Showcase */}
      <section className="py-16 services-showcase shiny-cards-container">
        <div className="container mx-auto px-4">
          <div className="text-center mb-12">
            <h2 className="text-3xl md:text-4xl font-bold text-white mb-4 drop-shadow-lg">
              {t('aiAutoAgent')}
            </h2>
            <p className="text-white/90 max-w-2xl mx-auto text-lg">
              {t('exploreOurSuite')}
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
            {services.map((service) => (
              <ServiceCard
                key={service.id}
                service={service}
                onClick={service.isImageEditor ? () => {
                  // Create a hidden file input to select an image
                  const input = document.createElement('input');
                  input.type = 'file';
                  input.accept = 'image/*';
                  input.onchange = (e) => {
                    const file = e.target.files[0];
                    if (file) {
                      const reader = new FileReader();
                      reader.onload = (event) => {
                        setSelectedImage(event.target.result);
                        setImageEditorOpen(true);
                      };
                      reader.readAsDataURL(file);
                    }
                  };
                  input.click();
                } : null}
              />
            ))}
          </div>

          <div className="text-center mt-12">
            <Link
              to="/services"
              className="inline-flex items-center px-6 py-3 border border-transparent text-base font-medium rounded-md text-white bg-gradient-to-r from-indigo-600 to-purple-600 hover:opacity-90 transition-opacity"
            >
              {t('allServices')}
            </Link>
          </div>
        </div>
      </section>

      {/* Before/After Demo Section */}
      <section className="py-16 bg-gray-50 before-after-demo">
        <div className="container mx-auto px-4">
          <div className="text-center mb-12">
            <h2 className="text-3xl md:text-4xl font-bold text-gray-900 mb-4">
              {t('explore')}
            </h2>
            <p className="text-gray-600 max-w-2xl mx-auto">
              {t('exploreOurSuite')}
            </p>
          </div>

          <div className="max-w-4xl mx-auto">
            <div className="bg-white p-6 rounded-xl shadow-lg">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="text-center">
                  <h3 className="font-semibold mb-2">{t('before')}</h3>
                  <img
                    src="https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?ixlib=rb-4.0.3&ixid=M3wxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8fA%3D%3D&auto=format&fit=crop&w=687&q=80"
                    alt="Before"
                    className="w-full h-64 object-cover rounded border"
                  />
                </div>
                <div className="text-center">
                  <h3 className="font-semibold mb-2">{t('after')}</h3>
                  <img
                    src="https://images.unsplash.com/photo-1607746882042-944635dfe10e?ixlib=rb-4.0.3&ixid=M3wxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8fA%3D%3D&auto=format&fit=crop&w=1170&q=80"
                    alt="After"
                    className="w-full h-64 object-cover rounded border"
                  />
                </div>
              </div>
              <div className="mt-4 text-center">
                <p className="text-gray-600">{t('beforeAfterComparison')}</p>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Branding / AI SaaS Section */}
      <section
        className="py-20 relative bg-cover bg-center bg-no-repeat why-choose-section"
        style={{
          backgroundImage: "url('https://images.unsplash.com/photo-1677442136019-21780ecad995?ixlib=rb-4.0.3&ixid=M3wxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8fA%3D%3D&auto=format&fit=crop&w=1170&q=80')"
        }}
      >
        {/* Semi-transparent dark gradient overlay */}
        <div className="absolute inset-0 bg-black bg-opacity-60 z-0"></div>

        <div className="container mx-auto px-4 relative z-10">
          <div className="text-center text-white">
            <h2 className="text-3xl md:text-4xl font-bold mb-4">{t('whyChoosePlatform')}</h2>
            <p className="text-xl mb-12 max-w-3xl mx-auto">
              {t('worldClassAISolutions')}
            </p>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
              <div className="bg-white bg-opacity-10 backdrop-blur-sm p-6 rounded-xl">
                <h3 className="text-xl font-semibold mb-2">{t('lightningFastProcessing')}</h3>
                <p>{t('getResultsInSeconds')}</p>
              </div>

              <div className="bg-white bg-opacity-10 backdrop-blur-sm p-6 rounded-xl">
                <h3 className="text-xl font-semibold mb-2">{t('enterpriseSecurity')}</h3>
                <p>{t('militaryGradeEncryption')}</p>
              </div>

              <div className="bg-white bg-opacity-10 backdrop-blur-sm p-6 rounded-xl">
                <h3 className="text-xl font-semibold mb-2">{t('accuracy')}</h3>
                <p>{t('precisionAI')}</p>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="py-16 bg-gradient-to-r from-indigo-600 to-purple-600 text-white cta-section">
        <div className="container mx-auto px-4 text-center">
          <h2 className="text-3xl md:text-4xl font-bold mb-4">
            {t('readyToGetStarted')}
          </h2>
          <p className="text-xl mb-8 max-w-2xl mx-auto">
            {t('joinThousands')}
          </p>
          <div className="flex flex-col sm:flex-row justify-center gap-4">
            <Link
              to="/signup"
              className="bg-white text-indigo-600 px-8 py-4 rounded-lg text-lg font-semibold hover:bg-gray-100 transition-colors"
            >
              {t('createFreeAccount')}
            </Link>
            <Link
              to="/pricing"
              className="bg-transparent border-2 border-white text-white px-8 py-4 rounded-lg text-lg font-semibold hover:bg-white hover:text-indigo-600 transition-colors"
            >
              {t('viewPricing')}
            </Link>
          </div>
        </div>
      </section>

      {/* Image Editor Modal */}
      <ImageEditorModal
        isOpen={imageEditorOpen}
        onClose={() => setImageEditorOpen(false)}
        imageSrc={selectedImage}
      />
    </div>
  );
};

export default HomePage;