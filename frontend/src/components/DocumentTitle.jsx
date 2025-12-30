import { useEffect } from 'react';
import { useLocation } from 'react-router-dom';
import { useLanguage } from '../contexts/LanguageContext';

const DocumentTitle = () => {
  const location = useLocation();
  const { t } = useLanguage();

  useEffect(() => {
    // Define page titles using the brand name from translations
    const getPageTitle = () => {
      const brandName = t('brandName');
      switch(location.pathname) {
        case '/':
          return brandName;
        case '/services':
          return `Services - ${brandName}`;
        case '/pricing':
          return `Pricing - ${brandName}`;
        case '/dashboard':
          return `Dashboard - ${brandName}`;
        case '/login':
          return `Login - ${brandName}`;
        case '/signup':
          return `Sign Up - ${brandName}`;
        case '/gallery':
          return `Gallery - ${brandName}`;
        case '/auto-agent':
          return `Auto Agent - ${brandName}`;
        case '/payment':
          return `Payment - ${brandName}`;
        case '/services/image-processing':
          return `Image Processing - ${brandName}`;
        case '/services/cv-generator':
          return `CV Generator - ${brandName}`;
        case '/services/color-palette':
          return `Color Palette - ${brandName}`;
        case '/services/object-detection':
          return `Object Detection - ${brandName}`;
        case '/services/image-upscaler':
          return `Image Upscaler - ${brandName}`;
        case '/services/background-blur':
          return `Background Blur - ${brandName}`;
        case '/services/image-editing':
          return `Image Editing - ${brandName}`;
        case '/services/face-detection':
          return `Face Detection - ${brandName}`;
        case '/services/metadata-analyzer':
          return `Metadata Analyzer - ${brandName}`;
        case '/services/format-converter':
          return `Format Converter - ${brandName}`;
        case '/services/watermark-removal':
          return `Watermark Removal - ${brandName}`;
        case '/services/image-enhancement':
          return `Image Enhancement - ${brandName}`;
        default:
          return brandName;
      }
    };

    document.title = getPageTitle();
  }, [location, t]);

  return null;
};

export default DocumentTitle;