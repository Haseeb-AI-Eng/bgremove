import React, { useState } from 'react';
import Joyride from 'react-joyride';
import { FaMapSigns } from 'react-icons/fa';

const TourGuide = () => {
  const [isTourOpen, setIsTourOpen] = useState(false);
  
  const steps = [
    {
      target: 'body',
      content: 'Welcome to our AI Background Removal Platform! Let me guide you through the key features.',
      placement: 'center',
      title: 'Welcome to Background Removal SaaS'
    },
    {
      target: '.hero-section',
      content: 'This is our hero section where you can see our main service - AI-powered background removal.',
      title: 'Hero Section'
    },
    {
      target: '.services-showcase',
      content: 'Explore our various AI-powered services including background removal, image enhancement, and more.',
      title: 'Services Showcase'
    },
    {
      target: '.before-after-demo',
      content: 'Try our interactive demo to see the background removal technology in action.',
      title: 'Before/After Demo'
    },
    {
      target: '.why-choose-section',
      content: 'Learn why our platform stands out with enterprise security, speed, and accuracy.',
      title: 'Why Choose Us'
    },
    {
      target: '.cta-section',
      content: 'Ready to get started? Sign up now to begin transforming your images!',
      title: 'Get Started'
    }
  ];

  const toggleTour = () => {
    setIsTourOpen(!isTourOpen);
  };

  const callback = (data) => {
    if (data.action === 'close' || data.status === 'finished') {
      setIsTourOpen(false);
    }
  };

  return (
    <>
      <button
        onClick={toggleTour}
        className="fixed bottom-6 right-6 z-50 bg-gradient-to-r from-indigo-600 to-purple-600 text-white p-4 rounded-full shadow-lg hover:from-indigo-700 hover:to-purple-700 transition-all"
        title="Start Tour"
      >
        <FaMapSigns className="text-xl" />
      </button>

      <Joyride
        steps={steps}
        run={isTourOpen}
        callback={callback}
        continuous
        showSkipButton
        showProgress
        hideCloseButton
        disableCloseOnEsc
        disableOverlayClose
        locale={{
          back: 'Back',
          close: 'Close',
          last: 'Finish',
          next: 'Next',
          skip: 'Skip'
        }}
        styles={{
          options: {
            primaryColor: '#4F46E5',
            zIndex: 10000,
          }
        }}
      />
    </>
  );
};

export default TourGuide;