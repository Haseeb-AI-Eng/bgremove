import React from 'react';
import { Link } from 'react-router-dom';
import { useLanguage } from '../contexts/LanguageContext';
import { FaShieldAlt } from 'react-icons/fa';

const WatermarkRemovalButton = ({ className = '', variant = 'default' }) => {
  const { t } = useLanguage();

  const baseClasses = 'flex items-center justify-center px-6 py-3 rounded-lg font-medium transition-all duration-200';
  
  const variantClasses = {
    default: 'bg-gradient-to-r from-red-500 to-pink-600 text-white hover:from-red-600 hover:to-pink-700 shadow-lg hover:shadow-xl transform hover:-translate-y-0.5',
    outline: 'border-2 border-red-500 text-red-600 hover:bg-red-50',
    ghost: 'text-red-600 hover:bg-red-50'
  };

  return (
    <Link 
      to="/services/watermark-removal" 
      className={`${baseClasses} ${variantClasses[variant]} ${className}`}
    >
      <FaShieldAlt className="mr-2" />
      {t('removeWatermark')}
    </Link>
  );
};

export default WatermarkRemovalButton;