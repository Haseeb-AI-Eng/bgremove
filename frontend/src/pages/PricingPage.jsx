import React from 'react';
import { Link } from 'react-router-dom';
import { useLanguage } from '../contexts/LanguageContext';
import { FaCheck, FaTimes, FaCrown, FaRocket, FaUser, FaUsers, FaChartLine } from 'react-icons/fa';

const PricingPage = () => {
  const { t } = useLanguage();

  const plans = [
    {
      name: t('free'),
      price: '$0',
      period: t('forever'),
      description: t('perfectForGettingStarted'),
      features: [
        { name: t('basicImageProcessing'), included: true },
        { name: t('apiCallsPerDay'), included: true },
        { name: t('standardSupport'), included: true },
        { name: t('aiCvGenerator'), included: true },
        { name: t('colorPaletteTool'), included: true },
        { name: t('backgroundRemoval'), included: true },
        { name: t('proFeatures'), included: false },
        { name: t('prioritySupport'), included: false },
        { name: t('unlimitedApiCalls'), included: false }
      ],
      cta: t('getStarted'),
      mostPopular: false,
      color: 'gray'
    },
    {
      name: t('pro'),
      price: '$1',
      period: t('perMonth'),
      description: t('idealForProfessionals'),
      features: [
        { name: t('allFreeFeatures'), included: true },
        { name: t('unlimitedApiCalls'), included: true },
        { name: t('prioritySupport'), included: true },
        { name: t('advancedImageProcessing'), included: true },
        { name: t('aiUpscaler'), included: true },
        { name: t('faceDetection'), included: true },
        { name: t('objectDetection'), included: true },
        { name: t('metadataAnalyzer'), included: true },
        { name: t('formatConverter'), included: true }
      ],
      cta: t('upgradeToPro'),
      mostPopular: true,
      color: 'indigo'
    },
    {
      name: t('enterprise'),
      price: t('custom'),
      period: '',
      description: t('forLargeTeams'),
      features: [
        { name: t('allProFeatures'), included: true },
        { name: t('customApiLimits'), included: true },
        { name: t('dedicatedSupport'), included: true },
        { name: t('customIntegrations'), included: true },
        { name: t('slaGuarantee'), included: true },
        { name: t('teamManagement'), included: true },
        { name: t('advancedAnalytics'), included: true },
        { name: t('whiteLabelOptions'), included: true },
        { name: t('customAiModels'), included: true }
      ],
      cta: t('contactSales'),
      mostPopular: false,
      color: 'purple'
    }
  ];

  const getColorClasses = (color, type) => {
    switch (color) {
      case 'indigo':
        return type === 'bg' ? 'bg-gradient-to-r from-indigo-600 to-purple-600' : 
               type === 'border' ? 'border-indigo-200' : 
               'text-indigo-600';
      case 'purple':
        return type === 'bg' ? 'bg-gradient-to-r from-purple-600 to-pink-600' : 
               type === 'border' ? 'border-purple-200' : 
               'text-purple-600';
      default:
        return type === 'bg' ? 'bg-gray-100' : 
               type === 'border' ? 'border-gray-200' : 
               'text-gray-600';
    }
  };

  return (
    <div className="min-h-screen bg-slate-50 py-20">
      <div className="container mx-auto px-4">
        {/* Header */}
        <div className="text-center mb-12">
          <h1 className="text-4xl md:text-5xl font-bold text-gray-900 mb-4">
            {t('pricing')}
          </h1>
          <p className="text-xl text-gray-600 max-w-3xl mx-auto">
            {t('choosePlanThatFits')}
          </p>
        </div>

        {/* Pricing Cards */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-8 max-w-6xl mx-auto">
          {plans.map((plan, index) => (
            <div
              key={index}
              className={`relative rounded-3xl p-8 transition-all duration-300 ${
                plan.mostPopular 
                  ? 'bg-white border-2 border-indigo-500 shadow-premium scale-105 z-10' 
                  : 'bg-white border border-slate-200 shadow-md hover:shadow-xl'
              }`}
            >
              {plan.mostPopular && (
                <div className={`${getColorClasses(plan.color, 'bg')} text-white text-xs font-semibold px-4 py-1 rounded-full absolute top-0 left-1/2 transform -translate-x-1/2 -translate-y-1/2`}>
                  {t('mostPopular')}
                </div>
              )}
              
              <div className="text-center">
                <h3 className="text-2xl font-bold text-gray-900 mb-2">{plan.name}</h3>
                <div className="mb-4">
                  <span className="text-4xl font-bold text-gray-900">{plan.price}</span>
                  {plan.period && <span className="text-gray-600">/{plan.period}</span>}
                </div>
                <p className="text-gray-600 mb-8">{plan.description}</p>
                
                <Link
                  to={plan.name === t('pro') ? '/payment' : plan.name === t('enterprise') ? '/contact' : '/signup'}
                  className={`btn w-full ${
                    plan.mostPopular
                      ? 'btn-primary'
                      : 'btn-secondary opacity-90'
                  }`}
                >
                  {plan.cta}
                </Link>
              </div>

              <ul className="mt-8 space-y-4">
                {plan.features.map((feature, featureIndex) => (
                  <li key={featureIndex} className="flex items-start">
                    {feature.included ? (
                      <FaCheck className={`${getColorClasses(plan.color)} mt-1 mr-3 flex-shrink-0`} />
                    ) : (
                      <FaTimes className="text-gray-400 mt-1 mr-3 flex-shrink-0" />
                    )}
                    <span className={feature.included ? 'text-gray-700' : 'text-gray-400'}>
                      {feature.name}
                    </span>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>

        {/* Feature Comparison */}
        <div className="mt-16 bg-white rounded-xl shadow-sm p-8">
          <h2 className="text-2xl font-bold text-gray-900 mb-8 text-center">{t('featureComparison')}</h2>

          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-gray-200">
                  <th className="text-left py-4 px-4 font-semibold text-gray-900">{t('feature')}</th>
                  <th className="text-center py-4 px-4 font-semibold text-gray-900">{t('free')}</th>
                  <th className="text-center py-4 px-4 font-semibold text-gray-900">{t('pro')}</th>
                  <th className="text-center py-4 px-4 font-semibold text-gray-900">{t('enterprise')}</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200">
                <tr>
                  <td className="py-4 px-4 font-medium text-gray-900">{t('apiCallsPerDay')}</td>
                  <td className="py-4 px-4 text-center text-gray-600">50</td>
                  <td className="py-4 px-4 text-center text-gray-600">{t('unlimited')}</td>
                  <td className="py-4 px-4 text-center text-gray-600">{t('custom')}</td>
                </tr>
                <tr>
                  <td className="py-4 px-4 font-medium text-gray-900">{t('imageProcessing')}</td>
                  <td className="py-4 px-4 text-center"><FaCheck className="text-green-500 mx-auto" /></td>
                  <td className="py-4 px-4 text-center"><FaCheck className="text-green-500 mx-auto" /></td>
                  <td className="py-4 px-4 text-center"><FaCheck className="text-green-500 mx-auto" /></td>
                </tr>
                <tr>
                  <td className="py-4 px-4 font-medium text-gray-900">{t('aiCvGenerator')}</td>
                  <td className="py-4 px-4 text-center"><FaCheck className="text-green-500 mx-auto" /></td>
                  <td className="py-4 px-4 text-center"><FaCheck className="text-green-500 mx-auto" /></td>
                  <td className="py-4 px-4 text-center"><FaCheck className="text-green-500 mx-auto" /></td>
                </tr>
                <tr>
                  <td className="py-4 px-4 font-medium text-gray-900">{t('advancedTools')}</td>
                  <td className="py-4 px-4 text-center text-gray-400">{t('limited')}</td>
                  <td className="py-4 px-4 text-center"><FaCheck className="text-green-500 mx-auto" /></td>
                  <td className="py-4 px-4 text-center"><FaCheck className="text-green-500 mx-auto" /></td>
                </tr>
                <tr>
                  <td className="py-4 px-4 font-medium text-gray-900">{t('support')}</td>
                  <td className="py-4 px-4 text-center text-gray-600">{t('standardSupport')}</td>
                  <td className="py-4 px-4 text-center text-gray-600">{t('prioritySupport')}</td>
                  <td className="py-4 px-4 text-center text-gray-600">{t('dedicatedSupport')}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>

        {/* CTA Section */}
        <div className="mt-16 bg-gradient-to-r from-indigo-600 to-purple-600 rounded-xl text-white p-8 text-center">
          <h2 className="text-2xl md:text-3xl font-bold mb-4">{t('readyToTransform')}</h2>
          <p className="text-lg mb-6 max-w-2xl mx-auto">
            {t('joinThousands')}
          </p>
          <div className="flex flex-col sm:flex-row justify-center gap-4">
            <Link
              to="/signup"
              className="bg-white text-indigo-600 px-6 py-3 rounded-lg font-semibold hover:bg-gray-100 transition-colors"
            >
              {t('startFreeTrial')}
            </Link>
            <Link
              to="/services"
              className="bg-transparent border-2 border-white text-white px-6 py-3 rounded-lg font-semibold hover:bg-white hover:text-indigo-600 transition-colors"
            >
              {t('exploreServices')}
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
};

export default PricingPage;