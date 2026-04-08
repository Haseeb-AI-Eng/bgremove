import React, { useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { FaBars, FaTimes, FaUser, FaLock, FaSignOutAlt, FaHome, FaWrench, FaTags, FaTachometerAlt, FaFileImage, FaRobot, FaGlobe, FaEraser, FaImage } from 'react-icons/fa';
import { useAuth } from '../contexts/AuthContext';
import { useLanguage } from '../contexts/LanguageContext';

const Layout = ({ children }) => {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const { user, logout, isAuthenticated } = useAuth();
  const { language, availableLanguages, t } = useLanguage();
  const location = useLocation();

  const navLinks = [
    { name: t('home'), path: '/', icon: <FaHome className="mr-2" /> },
    { name: t('services'), path: '/services', icon: <FaWrench className="mr-2" /> },
    { name: t('pricing'), path: '/pricing', icon: <FaTags className="mr-2" /> },
  ];

  const authLinks = isAuthenticated
    ? [
        { name: t('dashboard'), path: '/dashboard', icon: <FaTachometerAlt className="mr-2" /> },
        { name: t('apiDashboard'), path: '/dashboard', icon: <FaWrench className="mr-2" />, dashboardTab: 'api-keys' },
      ]
    : [
        { name: t('login'), path: '/login', icon: <FaLock className="mr-2" /> },
        { name: t('signUp'), path: '/signup', icon: <FaUser className="mr-2" /> },
      ];

  const isActive = (path) => location.pathname === path;

  // Get language flag based on current language
  const getLanguageFlag = (lang) => {
    switch(lang) {
      case 'en': return '🇺🇸';
      case 'es': return '🇪🇸';
      case 'de': return '🇩🇪';
      default: return '🌐';
    }
  };

  return (
    <div className="min-h-screen bg-slate-50">
      {/* Header */}
      <header className="sticky top-0 z-50 bg-white/80 backdrop-blur-md border-b border-slate-100 shadow-sm">
        <div className="container mx-auto px-4">
          <div className="flex justify-between items-center h-16">
            {/* Logo on the far left */}
            <Link to="/" className="flex items-center space-x-2 group">
              <div className="relative">
                <div className="absolute inset-0 bg-gradient-to-r from-cyan-400 via-purple-500 to-pink-500 rounded-lg blur-sm opacity-70 group-hover:opacity-100 transition-opacity"></div>
                <div className="relative bg-gradient-to-br from-cyan-500 via-purple-500 to-pink-500 p-2 rounded-lg">
                  <FaEraser className="text-white w-5 h-5" />
                </div>
              </div>
              <span className="text-xl font-bold bg-gradient-to-r from-indigo-600 to-purple-600 bg-clip-text text-transparent hidden md:block tracking-tight">
                {t('brandName')}
              </span>
            </Link>

            {/* Desktop Navigation in the middle */}
            <nav className="hidden md:flex items-center space-x-8 flex-grow mx-4">
              {navLinks.map((link) => (
                <Link
                  key={link.path}
                  to={link.path}
                  className={`flex items-center text-sm font-medium transition-colors duration-200 ${
                    isActive(link.path)
                      ? 'text-indigo-600'
                      : 'text-gray-600 hover:text-gray-900'
                  }`}
                >
                  {link.icon}
                  {link.name}
                </Link>
              ))}

              {isAuthenticated && (
                <>
                  <Link
                    to="/dashboard"
                    className={`flex items-center text-sm font-medium transition-colors duration-200 ${
                      isActive('/dashboard')
                        ? 'text-indigo-600'
                        : 'text-gray-600 hover:text-gray-900'
                    }`}
                  >
                    <FaTachometerAlt className="mr-2" />
                    {t('dashboard')}
                  </Link>
                  <Link
                    to="/dashboard?tab=api-keys"
                    className="flex items-center text-sm font-medium text-gray-600 hover:text-gray-900 transition-colors duration-200"
                  >
                    <FaWrench className="mr-2" />
                    {t('apiDashboard')}
                  </Link>
                </>
              )}

              {/* Language Switcher Removed */}
            </nav>

            {/* Auth Actions */}
            <div className="hidden md:flex items-center space-x-4">
              {!isAuthenticated ? (
                <>
                  <Link
                    to="/login"
                    className="text-sm font-medium text-gray-600 hover:text-gray-900 transition-colors"
                  >
                    {t('login')}
                  </Link>
                  <Link
                    to="/signup"
                    className="bg-gradient-to-r from-indigo-600 to-purple-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:opacity-90 transition-opacity"
                  >
                    {t('signUp')}
                  </Link>
                </>
              ) : (
                <div className="flex items-center space-x-4">
                  <span className="text-sm text-gray-600">
                    {t('hi')}, {user?.first_name || user?.email?.split('@')[0]}
                  </span>
                  {user?.is_pro && (
                    <span className="pro-badge text-xs px-2 py-1">{t('pro')}</span>
                  )}
                  <button
                    onClick={logout}
                    className="flex items-center text-sm font-medium text-gray-600 hover:text-gray-900 transition-colors"
                  >
                    <FaSignOutAlt className="mr-1" /> {t('logout')}
                  </button>
                </div>
              )}
            </div>


            {/* Mobile menu button */}
            <button
              className="md:hidden p-2 rounded-md text-gray-600 hover:text-gray-900 focus:outline-none"
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
            >
              {mobileMenuOpen ? <FaTimes size={20} /> : <FaBars size={20} />}
            </button>
          </div>
        </div>

        {/* Mobile Navigation */}
        {mobileMenuOpen && (
          <div className="md:hidden bg-white border-t">
            <div className="px-2 pt-2 pb-3 space-y-1">

              {navLinks.map((link) => (
                <Link
                  key={link.path}
                  to={link.path}
                  className={`block px-3 py-2 rounded-md text-base font-medium ${
                    isActive(link.path)
                      ? 'bg-indigo-50 text-indigo-600'
                      : 'text-gray-600 hover:bg-gray-50 hover:text-gray-900'
                  }`}
                  onClick={() => setMobileMenuOpen(false)}
                >
                  <span className="flex items-center">
                    {link.icon}
                    {link.name}
                  </span>
                </Link>
              ))}

              {authLinks.map((link) => {
                // Handle API Dashboard link separately since it has query parameters
                if (link.name === t('apiDashboard')) {
                  return (
                    <Link
                      key="api-dashboard"
                      to="/dashboard?tab=api-keys"
                      className="block px-3 py-2 rounded-md text-base font-medium text-gray-600 hover:bg-gray-50 hover:text-gray-900"
                      onClick={() => setMobileMenuOpen(false)}
                    >
                      <span className="flex items-center">
                        {link.icon}
                        {link.name}
                      </span>
                    </Link>
                  );
                }
                return (
                  <Link
                    key={link.path}
                    to={link.path}
                    className={`block px-3 py-2 rounded-md text-base font-medium ${
                      isActive(link.path)
                        ? 'bg-indigo-50 text-indigo-600'
                        : 'text-gray-600 hover:bg-gray-50 hover:text-gray-900'
                    }`}
                    onClick={() => setMobileMenuOpen(false)}
                  >
                    <span className="flex items-center">
                      {link.icon}
                      {link.name}
                    </span>
                  </Link>
                );
              })}

              {isAuthenticated && (
                <button
                  onClick={() => {
                    logout();
                    setMobileMenuOpen(false);
                  }}
                  className="block w-full text-left px-3 py-2 rounded-md text-base font-medium text-gray-600 hover:bg-gray-50 hover:text-gray-900"
                >
                  <span className="flex items-center">
                    <FaSignOutAlt className="mr-2" />
                    {t('logout')}
                  </span>
                </button>
              )}

              {/* Mobile Language Switcher Removed */}
            </div>
          </div>
        )}
      </header>

      {/* Main Content */}
      <main>{children}</main>

      {/* Footer */}
      <footer className="bg-slate-50 border-t border-slate-200 mt-24">
        <div className="container mx-auto px-4 py-12">
          <div className="grid grid-cols-1 md:grid-cols-4 gap-8">
            {/* Brand */}
            <div className="col-span-1 md:col-span-1">
              <div className="flex items-center space-x-2 mb-4">
                <div className="relative">
                  <div className="absolute inset-0 bg-gradient-to-r from-cyan-400 via-purple-500 to-pink-500 rounded-lg blur-sm opacity-70"></div>
                  <div className="relative bg-gradient-to-br from-cyan-500 via-purple-500 to-pink-500 p-2 rounded-lg">
                    <FaEraser className="text-white w-5 h-5" />
                  </div>
                </div>
                <span className="text-lg font-bold bg-gradient-to-r from-cyan-600 via-purple-600 to-pink-600 bg-clip-text text-transparent">{t('brandName')}</span>
              </div>
              <p className="text-gray-600 text-sm">
                {t('worldClassAISolutions')}
              </p>
            </div>

            {/* Services */}
            <div>
              <h3 className="text-sm font-semibold text-gray-900 uppercase tracking-wider mb-4">{t('servicesFooter')}</h3>
              <ul className="space-y-2">
                <li><Link to="/services/image-processing" className="text-gray-600 hover:text-indigo-600 text-sm transition-colors">{t('imageProcessing')}</Link></li>
                <li><Link to="/services/cv-generator" className="text-gray-600 hover:text-indigo-600 text-sm transition-colors">{t('aiCvGenerator')}</Link></li>
                <li><Link to="/services/color-palette" className="text-gray-600 hover:text-indigo-600 text-sm transition-colors">{t('colorPaletteGenerator')}</Link></li>
                <li><Link to="/services/object-detection" className="text-gray-600 hover:text-indigo-600 text-sm transition-colors">{t('objectDetectionTool')}</Link></li>
                <li><Link to="/services" className="text-gray-600 hover:text-indigo-600 text-sm transition-colors">{t('allServices')}</Link></li>
              </ul>
            </div>

            {/* Account */}
            <div>
              <h3 className="text-sm font-semibold text-gray-900 uppercase tracking-wider mb-4">{t('accountFooter')}</h3>
              <ul className="space-y-2">
                <li><Link to="/dashboard" className="text-gray-600 hover:text-indigo-600 text-sm transition-colors">{t('dashboardLink')}</Link></li>
                <li><Link to="/dashboard" className="text-gray-600 hover:text-indigo-600 text-sm transition-colors">{t('apiKeys')}</Link></li>
                <li><Link to="/pricing" className="text-gray-600 hover:text-indigo-600 text-sm transition-colors">{t('pricingLink')}</Link></li>
                {isAuthenticated ? (
                  <li><button onClick={logout} className="text-gray-600 hover:text-indigo-600 text-sm transition-colors">{t('logout')}</button></li>
                ) : (
                  <>
                    <li><Link to="/login" className="text-gray-600 hover:text-indigo-600 text-sm transition-colors">{t('login')}</Link></li>
                    <li><Link to="/signup" className="text-gray-600 hover:text-indigo-600 text-sm transition-colors">{t('signUp')}</Link></li>
                  </>
                )}
              </ul>
            </div>

            {/* Legal */}
            <div>
              <h3 className="text-sm font-semibold text-gray-900 uppercase tracking-wider mb-4">{t('legal')}</h3>
              <ul className="space-y-2">
                <li><a href="#" className="text-gray-600 hover:text-indigo-600 text-sm transition-colors">{t('privacyPolicy')}</a></li>
                <li><a href="#" className="text-gray-600 hover:text-indigo-600 text-sm transition-colors">{t('termsOfService')}</a></li>
                <li><a href="#" className="text-gray-600 hover:text-indigo-600 text-sm transition-colors">{t('security')}</a></li>
                <li><a href="#" className="text-gray-600 hover:text-indigo-600 text-sm transition-colors">{t('compliance')}</a></li>
              </ul>
            </div>
          </div>

          <div className="border-t mt-8 pt-8 text-center">
            <p className="text-gray-600 text-sm">
              © {new Date().getFullYear()} AI Platform. {t('allRightsReserved')}
            </p>
          </div>
        </div>
      </footer>
    </div>
  );
};

export default Layout;