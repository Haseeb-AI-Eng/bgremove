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
      icon: <FaEraser className="text-3xl" />,
      path: '/services/image-processing',
      image: 'https://images.unsplash.com/photo-1529626455594-4ff0802cfb7e?ixlib=rb-4.0.3&ixid=M3wxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8fA%3D%3D&auto=format&fit=crop&w=1170&q=80',
      color: 'from-blue-500 to-purple-600'
    },
    {
      id: 2,
      title: t('watermarkRemoval'),
      description: t('removeWatermarkDescription'),
      icon: <FaShieldAlt className="text-3xl" />,
      path: '/services/watermark-removal',
      image: 'https://images.unsplash.com/photo-1557683316-973673baf926?ixlib=rb-4.0.3&ixid=M3wxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8fA%3D%3D&auto=format&fit=crop&w=1170&q=80',
      color: 'from-red-500 to-rose-600'
    },
    {
      id: 3,
      title: t('imageUpscaler'),
      description: t('enhanceImageResolution'),
      icon: <FaRocket className="text-3xl" />,
      path: '#', // Will be handled by image editor
      image: 'https://images.unsplash.com/photo-1531297484001-80022131f5a1?ixlib=rb-4.0.3&ixid=M3wxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8fA%3D%3D&auto=format&fit=crop&w=1170&q=80',
      color: 'from-green-500 to-teal-600',
      isImageEditor: true
    },
    {
      id: 4,
      title: t('objectDetectionTool'),
      description: t('identifyAndLocate'),
      icon: <FaEye className="text-3xl" />,
      path: '/services/object-detection',
      image: 'https://images.unsplash.com/photo-1519389950473-47ba0277781c?ixlib=rb-4.0.3&ixid=M3wxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8fA%3D%3D&auto=format&fit=crop&w=1170&q=80',
      color: 'from-indigo-500 to-blue-600'
    }
  ];

  return (
    <div className="min-h-screen">
      {/* Hero Section */}
      <section className="relative min-h-screen flex items-center bg-slate-900 overflow-hidden">
        {/* Animated Background Elements */}
        <div className="absolute inset-0 z-0 overflow-hidden pointer-events-none">
          <div className="absolute top-[-10%] left-[-10%] w-[50%] h-[50%] bg-indigo-500/10 rounded-full blur-[140px] animate-pulse"></div>
          <div className="absolute bottom-[-10%] right-[-10%] w-[50%] h-[50%] bg-purple-500/10 rounded-full blur-[140px] animate-pulse" style={{ animationDelay: '2s' }}></div>
        </div>

        <div className="container mx-auto px-6 py-20 relative z-10">
          <div className="flex flex-col lg:flex-row items-center gap-12">
            {/* Left Column: Heading Content */}
            <div className="lg:w-1/2 text-left relative z-20">
              <div className="inline-block px-4 py-1.5 mb-6 rounded-full bg-indigo-500/10 border border-indigo-500/20 backdrop-blur-md">
                <span className="text-indigo-400 text-sm font-medium tracking-wider uppercase">{t('aiAutoAgent')}</span>
              </div>
              <h1 className="text-3xl md:text-5xl font-extrabold mb-6 leading-tight text-white tracking-tight">
                <span className="block text-transparent bg-clip-text bg-gradient-to-r from-blue-400 via-indigo-400 to-purple-500 animate-gradient-x p-1">
                  {t('seoTitle')}
                </span>
              </h1>
              <p className="text-[10px] md:text-xs text-slate-400 mb-10 max-w-lg leading-relaxed font-medium opacity-80 uppercase tracking-[0.2em]">
                {t('seoDescription')}
              </p>
              <div className="flex flex-wrap gap-4">
                <Link
                  to="/services/image-processing"
                  className="px-8 py-4 bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl font-bold transition-all transform hover:-translate-y-1 shadow-xl shadow-indigo-600/20"
                >
                  {t('getStarted')}
                </Link>
                <Link
                  to="/pricing"
                  className="px-8 py-4 bg-white/5 hover:bg-white/10 text-white border border-white/10 rounded-xl font-bold transition-all backdrop-blur-sm"
                >
                  {t('viewPricing')}
                </Link>
              </div>
            </div>

            {/* Right Column: Direct Services Box */}
            <div className="lg:w-1/2 w-full animate-float">
              <div className="relative group">
                <div className="absolute -inset-1 bg-gradient-to-r from-indigo-500 to-purple-600 rounded-3xl blur opacity-25 group-hover:opacity-40 transition duration-1000"></div>
                
                <div className="relative bg-slate-800/80 backdrop-blur-2xl border border-white/10 rounded-3xl p-8 shadow-2xl">
                  <div className="flex items-center justify-between mb-8">
                    <h3 className="text-2xl font-bold text-white">{t('allServices')}</h3>
                    <div className="flex space-x-2">
                      <div className="w-3 h-3 rounded-full bg-red-500/50"></div>
                      <div className="w-3 h-3 rounded-full bg-yellow-500/50"></div>
                      <div className="w-3 h-3 rounded-full bg-green-500/50"></div>
                    </div>
                  </div>

                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                    {services.map((service) => (
                      <div 
                        key={service.id}
                        className="p-4 bg-white/5 rounded-2xl border border-white/5 hover:bg-white/10 transition-all cursor-pointer group/item flex flex-col items-center text-center"
                        onClick={service.isImageEditor ? () => {
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
                        } : () => window.location.href = service.path}
                      >
                        <div className={`w-12 h-12 bg-gradient-to-br ${service.color} rounded-xl flex items-center justify-center mb-3 group-hover/item:scale-110 transition-transform shadow-lg`}>
                          <span className="text-white text-xl">{service.icon}</span>
                        </div>
                        <h4 className="text-white font-semibold text-[10px] mb-1">{service.title}</h4>
                        <p className="text-slate-400 text-[9px] line-clamp-1">{service.description}</p>
                      </div>
                    ))}
                  </div>

                  <div className="mt-8 pt-6 border-t border-white/5 text-center">
                    <Link to="/services" className="text-indigo-400 hover:text-indigo-300 text-sm font-medium transition-colors">
                      {t('explore')} {t('allServices')} →
                    </Link>
                  </div>
                </div>
              </div>
            </div>
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
            <div className="bg-white p-8 rounded-2xl shadow-premium border border-slate-100 hover:shadow-2xl transition-all duration-300">
              <div className="w-12 h-12 bg-gradient-to-r from-indigo-500 to-purple-600 rounded-lg flex items-center justify-center mb-4">
                <FaChartLine className="text-white text-xl" />
              </div>
              <h3 className="text-base font-semibold text-gray-900 mb-2">{t('contentGeneration')}</h3>
              <p className="text-gray-600">{t('aiPoweredTools')}</p>
            </div>

            <div className="bg-white p-8 rounded-2xl shadow-premium border border-slate-100 hover:shadow-2xl transition-all duration-300">
              <div className="w-12 h-12 bg-gradient-to-r from-green-500 to-teal-600 rounded-lg flex items-center justify-center mb-4">
                <FaGlobe className="text-white text-xl" />
              </div>
              <h3 className="text-base font-semibold text-gray-900 mb-2">{t('imageProcessing')}</h3>
              <p className="text-gray-600">{t('advancedTools')}</p>
            </div>

            <div className="bg-white p-8 rounded-2xl shadow-premium border border-slate-100 hover:shadow-2xl transition-all duration-300">
              <div className="w-12 h-12 bg-gradient-to-r from-pink-500 to-rose-600 rounded-lg flex items-center justify-center mb-4">
                <FaShieldAlt className="text-white text-xl" />
              </div>
              <h3 className="text-base font-semibold text-gray-900 mb-2">{t('designTools')}</h3>
              <p className="text-gray-600">{t('creativeTools')}</p>
            </div>

            <div className="bg-white p-8 rounded-2xl shadow-premium border border-slate-100 hover:shadow-2xl transition-all duration-300">
              <div className="w-12 h-12 bg-gradient-to-r from-yellow-500 to-orange-600 rounded-lg flex items-center justify-center mb-4">
                <FaRocket className="text-white text-xl" />
              </div>
              <h3 className="text-base font-semibold text-gray-900 mb-2">{t('readyToGetStarted')}</h3>
              <p className="text-gray-600">{t('joinThousands')}</p>
            </div>
          </div>
        </div>
      </section>

      {/* Services Showcase */}
      <section className="py-24 services-showcase shiny-cards-container relative overflow-hidden bg-slate-100">
        <div className="absolute inset-0 bg-grid-slate-200/50 [mask-image:radial-gradient(ellipse_at_center,white,transparent)]"></div>
        <div className="container mx-auto px-6 relative z-10">
          <div className="text-center mb-16">
            <h2 className="text-3xl md:text-5xl font-extrabold text-slate-900 mb-6 tracking-tight">
              {t('aiAutoAgent')}
            </h2>
            <div className="w-24 h-1.5 bg-indigo-600 mx-auto rounded-full mb-8"></div>
            <p className="text-slate-600 max-w-2xl mx-auto text-lg md:text-xl font-medium">
              {t('exploreOurSuite')}
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-10">
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
                    alt={t('altBefore')}
                    className="w-full h-64 object-cover rounded border"
                  />
                </div>
                <div className="text-center">
                  <h3 className="font-semibold mb-2">{t('after')}</h3>
                  <img
                    src="https://images.unsplash.com/photo-1607746882042-944635dfe10e?ixlib=rb-4.0.3&ixid=M3wxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8fA%3D%3D&auto=format&fit=crop&w=1170&q=80"
                    alt={t('altAfter')}
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
                <h3 className="text-lg font-semibold mb-2">{t('lightningFastProcessing')}</h3>
                <p>{t('getResultsInSeconds')}</p>
              </div>

              <div className="bg-white bg-opacity-10 backdrop-blur-sm p-6 rounded-xl">
                <h3 className="text-lg font-semibold mb-2">{t('enterpriseSecurity')}</h3>
                <p>{t('militaryGradeEncryption')}</p>
              </div>

              <div className="bg-white bg-opacity-10 backdrop-blur-sm p-6 rounded-xl">
                <h3 className="text-lg font-semibold mb-2">{t('accuracy')}</h3>
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

      {/* SEO Content Section */}
      <section className="py-20 bg-white" id="seo-content">
        <div className="container mx-auto px-6 max-w-4xl">
          <h2 className="text-2xl md:text-4xl font-extrabold text-slate-900 mb-10 border-b-4 border-indigo-600 pb-4 leading-tight">
            {t('seoContentH1')}
          </h2>
          
          <div className="prose prose-lg text-slate-600 leading-relaxed space-y-8">
            <p className="text-xl text-slate-700 font-medium italic border-l-4 border-indigo-500 pl-6 py-2 bg-slate-50 rounded-r-xl">
              {t('seoContentP1')}
            </p>

            <div className="space-y-6">
              <h3 className="text-2xl md:text-3xl font-bold text-slate-800 flex items-center gap-3">
                <span className="w-8 h-8 rounded-lg bg-indigo-100 text-indigo-600 flex items-center justify-center text-sm">01</span>
                {t('seoContentH2_1')}
              </h3>
              <p>
                {t('seoContentP2')}
              </p>
            </div>

            <div className="space-y-6">
              <h3 className="text-2xl md:text-3xl font-bold text-slate-800 flex items-center gap-3">
                <span className="w-8 h-8 rounded-lg bg-purple-100 text-purple-600 flex items-center justify-center text-sm">02</span>
                {t('seoContentH2_2')}
              </h3>
              <p>
                {t('seoContentP3')}
              </p>
            </div>

            <div className="mt-12 p-8 bg-gradient-to-br from-slate-900 to-indigo-950 rounded-3xl text-white shadow-2xl relative overflow-hidden group">
              <div className="absolute top-0 right-0 w-64 h-64 bg-white/5 rounded-full -mr-32 -mt-32 blur-3xl group-hover:bg-white/10 transition-colors"></div>
              <div className="relative z-10">
                <h4 className="text-2xl font-bold mb-4">{t('readyToGetStarted')}</h4>
                <p className="text-slate-300 mb-8 max-w-md">
                  {t('startUsingAIPowered')}
                </p>
                <Link 
                  to="/services/image-processing" 
                  className="inline-flex items-center px-6 py-3 bg-white text-indigo-950 rounded-xl font-bold hover:bg-slate-100 transition-all hover:scale-105 active:scale-95"
                >
                  {t('startProcessing')} →
                </Link>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* FAQ Section in German for SEO */}
      <section className="py-20 bg-white" id="faq">
        <div className="container mx-auto px-4">


          <div className="max-w-4xl mx-auto space-y-6">
            {t('faqs') && Array.isArray(t('faqs')) && t('faqs').map((faq, index) => (
              <div 
                key={index} 
                className="group bg-slate-50 rounded-2xl p-6 border border-slate-100 hover:border-indigo-200 hover:bg-white hover:shadow-xl transition-all duration-300"
              >
                <div className="flex gap-4">
                  <div className="flex-shrink-0 w-8 h-8 rounded-full bg-indigo-100 text-indigo-600 flex items-center justify-center font-bold">
                    {index + 1}
                  </div>
                  <div>
                    <h3 className="text-xl font-bold text-slate-900 mb-3 group-hover:text-indigo-600 transition-colors">
                      {faq.question}
                    </h3>
                    <p className="text-slate-600 leading-relaxed">
                      {faq.answer}
                    </p>
                  </div>
                </div>
              </div>
            ))}
          </div>

          {/* Keywords cloud for SEO */}
          <div className="mt-20 pt-10 border-t border-slate-100">
            <div className="flex flex-wrap justify-center gap-3">
              {t('keywords') && Array.isArray(t('keywords')) && t('keywords').map((keyword, index) => (
                <span 
                  key={index}
                  className="px-4 py-2 bg-slate-100 text-slate-500 rounded-full text-sm font-medium hover:bg-indigo-50 hover:text-indigo-600 transition-colors cursor-default"
                >
                  #{keyword}
                </span>
              ))}
            </div>
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