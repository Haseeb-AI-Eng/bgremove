import React from 'react';
import { Routes, Route, useLocation } from 'react-router-dom';
import { AuthProvider } from './contexts/AuthContext';
import { ApiKeyProvider } from './contexts/ApiKeyContext';
import { LanguageProvider } from './contexts/LanguageContext';
import Layout from './components/Layout';
import DocumentTitle from './components/DocumentTitle';
import HomePage from './pages/HomePage';
import ServicesPage from './pages/ServicesPage';
import PricingPage from './pages/PricingPage';
import DashboardPage from './pages/DashboardPage';
import LoginPage from './pages/LoginPage';
import SignupPage from './pages/SignupPage';
import ImageProcessingPage from './pages/services/ImageProcessingPage';
import CvGeneratorPage from './pages/services/CvGeneratorPage';
import ColorPalettePage from './pages/services/ColorPalettePage';
import ObjectDetectionPage from './pages/services/ObjectDetectionPage';
import ImageUpscalerPage from './pages/services/ImageUpscalerPage';
import BackgroundBlurPage from './pages/services/BackgroundBlurPage';
import ImageEditingPage from './pages/services/ImageEditingPage';
import FaceDetectionPage from './pages/services/FaceDetectionPage';
import MetadataAnalyzerPage from './pages/services/MetadataAnalyzerPage';
import FormatConverterPage from './pages/services/FormatConverterPage';
import PaymentPage from './components/PaymentPage';
import TourGuide from './components/TourGuide';
import GalleryPage from './pages/GalleryPage';
import AutoAgentPage from './pages/AutoAgentPage';
import WatermarkRemovalPage from './pages/services/WatermarkRemovalPage';
import ImageEnhancementPage from './pages/services/ImageEnhancementPage';
import useScrollToTop from './hooks/useScrollToTop';
import './App.css';

// Component to handle scroll to top
const ScrollToTopHandler = () => {
  useScrollToTop();
  return null;
};

function App() {
  return (
    <LanguageProvider>
      <AuthProvider>
        <ApiKeyProvider>
          <DocumentTitle />
          <Layout>
            <ScrollToTopHandler />
            <Routes>
              <Route path="/" element={<HomePage />} />
              <Route path="/services" element={<ServicesPage />} />
              <Route path="/pricing" element={<PricingPage />} />
              <Route path="/dashboard" element={<DashboardPage />} />
              <Route path="/login" element={<LoginPage />} />
              <Route path="/signup" element={<SignupPage />} />
              <Route path="/gallery" element={<GalleryPage />} />
              <Route path="/payment" element={<PaymentPage />} />
              <Route path="/auto-agent" element={<AutoAgentPage />} />

              {/* Service Pages */}
              <Route path="/services/image-processing" element={<ImageProcessingPage />} />
              <Route path="/services/cv-generator" element={<CvGeneratorPage />} />
              <Route path="/services/color-palette" element={<ColorPalettePage />} />
              <Route path="/services/object-detection" element={<ObjectDetectionPage />} />
              <Route path="/services/image-upscaler" element={<ImageUpscalerPage />} />
              <Route path="/services/background-blur" element={<BackgroundBlurPage />} />
              <Route path="/services/image-editing" element={<ImageEditingPage />} />
              <Route path="/services/face-detection" element={<FaceDetectionPage />} />
              <Route path="/services/metadata-analyzer" element={<MetadataAnalyzerPage />} />
              <Route path="/services/format-converter" element={<FormatConverterPage />} />
              <Route path="/services/watermark-removal" element={<WatermarkRemovalPage />} />
              <Route path="/services/image-enhancement" element={<ImageEnhancementPage />} />
            </Routes>
            <TourGuide />
          </Layout>
        </ApiKeyProvider>
      </AuthProvider>
    </LanguageProvider>
  );
}

export default App;