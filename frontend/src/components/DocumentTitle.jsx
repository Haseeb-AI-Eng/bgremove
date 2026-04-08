import { useEffect } from 'react';
import { useLocation } from 'react-router-dom';
import { useLanguage } from '../contexts/LanguageContext';

const DocumentTitle = () => {
  const location = useLocation();
  const { t } = useLanguage();

  useEffect(() => {
    // Define page titles and descriptions using translations
    const updateMetadata = () => {
      const brandName = t('brandName');
      let title = brandName;
      let description = t('seoDescription');

      switch(location.pathname) {
        case '/':
          title = t('seoTitle');
          description = t('seoDescription');
          break;
        case '/services':
          title = `${t('services')} - ${brandName}`;
          break;
        case '/pricing':
          title = `${t('pricing')} - ${brandName}`;
          break;
        case '/dashboard':
          title = `${t('dashboard')} - ${brandName}`;
          break;
        case '/login':
          title = `${t('login')} - ${brandName}`;
          break;
        case '/signup':
          title = `${t('signUp')} - ${brandName}`;
          break;
        case '/gallery':
          title = `${t('gallery')} - ${brandName}`;
          break;
        case '/auto-agent':
          title = `${t('aiAutoAgentTitle')} - ${brandName}`;
          break;
        case '/payment':
          title = `Zahlung - ${brandName}`;
          break;
        case '/services/image-processing':
          title = `${t('imageProcessing')} - ${brandName}`;
          break;
        case '/services/cv-generator':
          title = `${t('aiCvGenerator')} - ${brandName}`;
          break;
        case '/services/color-palette':
          title = `${t('colorPaletteGenerator')} - ${brandName}`;
          break;
        case '/services/object-detection':
          title = `${t('objectDetectionTool')} - ${brandName}`;
          break;
        case '/services/image-upscaler':
          title = `${t('imageUpscaler')} - ${brandName}`;
          break;
        case '/services/background-blur':
          title = `${t('backgroundBlur')} - ${brandName}`;
          break;
        case '/services/image-editing':
          title = `${t('imageEditingSuite')} - ${brandName}`;
          break;
        case '/services/face-detection':
          title = `${t('faceDetection')} - ${brandName}`;
          break;
        case '/services/metadata-analyzer':
          title = `${t('imageMetadataAnalyzer')} - ${brandName}`;
          break;
        case '/services/format-converter':
          title = `${t('formatConverter')} - ${brandName}`;
          break;
        case '/services/watermark-removal':
          title = `${t('watermarkRemoval')} - ${brandName}`;
          break;
        case '/services/image-enhancement':
          title = `${t('quality')} - ${brandName}`;
          break;
        default:
          title = brandName;
      }

      document.title = title;
      
      // Update meta description
      const metaDescription = document.querySelector('meta[name="description"]');
      if (metaDescription) {
        metaDescription.setAttribute('content', description);
      } else {
        const meta = document.createElement('meta');
        meta.name = 'description';
        meta.content = description;
        document.head.appendChild(meta);
      }
    };

    updateMetadata();
  }, [location, t]);

  return null;
};

export default DocumentTitle;