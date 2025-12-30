import React, { useState, useEffect, useRef } from 'react';
import { FaComment, FaTimes, FaPlay, FaPause, FaVolumeUp, FaRobot } from 'react-icons/fa';

const TalkingAgent = ({ isOpen, onClose, onPageChange }) => {
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [currentMessage, setCurrentMessage] = useState('');
  const [messages, setMessages] = useState([]);
  const [isMuted, setIsMuted] = useState(false);
  const [mouthOpen, setMouthOpen] = useState(false);
  
  const utteranceRef = useRef(null);
  const speechSynthesisRef = useRef(window.speechSynthesis);

  // Sample messages for website guidance
  const guidanceMessages = [
    {
      page: 'home',
      title: 'Welcome to the AI Platform!',
      message: 'Hello! I\'m your AI assistant. I\'m here to help you navigate our platform. On the home page, you can see various AI services like background removal, image enhancement, and more. Feel free to explore!'
    },
    {
      page: 'services',
      title: 'Services Page',
      message: 'This page showcases all our AI-powered services. You can use our background removal tool, image enhancement, and other image processing features. Each service is designed to make your work easier.'
    },
    {
      page: 'image-processing',
      title: 'Image Processing',
      message: 'Here you can remove backgrounds, change backgrounds, or replace clothes in images. Simply upload your image, select the processing type, and click process. The AI will do the rest!'
    },
    {
      page: 'auto-agent',
      title: 'Auto Agent',
      message: 'Welcome to the Auto Agent! This powerful feature allows you to give natural language instructions to process your images. Upload an image, describe what you want done, and our AI will automatically perform the requested operations. For example, try "Remove the background" or "Change background to blue". The AI understands complex instructions and can perform multiple operations at once!'
    },
    {
      page: 'gallery',
      title: 'Gallery',
      message: 'Your processed images are stored here. You can view, download, or manage your images. If you\'re not logged in, you\'ll see sample images to demonstrate our capabilities.'
    }
  ];

  // Function to speak a message
  const speakMessage = (message) => {
    if (isMuted || !message) return;

    // Cancel any ongoing speech
    speechSynthesisRef.current.cancel();
    
    // Create new utterance
    const utterance = new SpeechSynthesisUtterance(message);
    utterance.rate = 1.0; // Normal speaking rate
    utterance.pitch = 1.0; // Normal pitch
    utterance.volume = 1.0; // Normal volume
    
    // Animate mouth while speaking
    utterance.onstart = () => {
      setIsSpeaking(true);
      setMouthOpen(true);
      setCurrentMessage(message);
    };
    
    utterance.onend = () => {
      setIsSpeaking(false);
      setMouthOpen(false);
      setCurrentMessage('');
    };
    
    utterance.onerror = () => {
      setIsSpeaking(false);
      setMouthOpen(false);
      setCurrentMessage('');
    };
    
    // Start speaking
    speechSynthesisRef.current.speak(utterance);
    utteranceRef.current = utterance;
  };

  // Function to stop speaking
  const stopSpeaking = () => {
    speechSynthesisRef.current.cancel();
    setIsSpeaking(false);
    setMouthOpen(false);
    setCurrentMessage('');
  };

  // Function to toggle mute
  const toggleMute = () => {
    setIsMuted(!isMuted);
    if (!isMuted) {
      speechSynthesisRef.current.cancel();
      setIsSpeaking(false);
      setMouthOpen(false);
      setCurrentMessage('');
    }
  };

  // Function to provide guidance based on current page
  const provideGuidance = (page) => {
    const guidance = guidanceMessages.find(msg => msg.page === page);
    if (guidance) {
      speakMessage(guidance.message);
      setMessages(prev => [...prev, { text: guidance.title + ': ' + guidance.message, timestamp: new Date() }]);
    }
  };

  // Clean up on unmount
  useEffect(() => {
    return () => {
      if (speechSynthesisRef.current.speaking) {
        speechSynthesisRef.current.cancel();
      }
    };
  }, []);

  // Animation for mouth movement while speaking
  useEffect(() => {
    let interval;
    if (isSpeaking) {
      interval = setInterval(() => {
        setMouthOpen(prev => !prev);
      }, 300); // Toggle mouth every 300ms while speaking
    } else {
      setMouthOpen(false);
    }

    return () => {
      if (interval) clearInterval(interval);
    };
  }, [isSpeaking]);

  // Welcome message when agent opens
  useEffect(() => {
    if (isOpen && messages.length === 0) {
      setTimeout(() => {
        speakMessage("Hello! I'm your AI assistant. I'm here to help you navigate and use our platform. Click 'Guide Me' to learn about this page, or select a different page to learn about it.");
      }, 500);
    }
  }, [isOpen]);

  if (!isOpen) return null;

  return (
    <div className="fixed bottom-6 right-6 z-50 w-80">
      {/* Agent Card */}
      <div className="bg-gradient-to-br from-blue-500 to-purple-600 rounded-2xl shadow-xl overflow-hidden transform transition-all duration-300">
        {/* Header */}
        <div className="bg-black bg-opacity-20 px-4 py-3 flex justify-between items-center">
          <div className="flex items-center">
            <FaRobot className="text-white mr-2" />
            <h3 className="text-white font-semibold">AI Assistant</h3>
          </div>
          <button 
            onClick={onClose}
            className="text-white hover:text-gray-200 transition-colors"
          >
            <FaTimes />
          </button>
        </div>

        {/* Agent Character */}
        <div className="p-4 bg-white bg-opacity-10 flex items-center">
          <div className="relative">
            {/* Agent Avatar - Simple SVG Robot */}
            <div className="w-16 h-16 bg-gradient-to-br from-blue-300 to-purple-400 rounded-full flex items-center justify-center border-4 border-white shadow-lg">
              <div className="flex flex-col items-center">
                {/* Eyes */}
                <div className="flex space-x-2 mb-1">
                  <div className="w-2 h-2 bg-white rounded-full"></div>
                  <div className="w-2 h-2 bg-white rounded-full"></div>
                </div>
                {/* Mouth - changes when speaking */}
                <div className={`w-6 h-${mouthOpen ? '4' : '1'} bg-white rounded-full transition-all duration-200 ${mouthOpen ? 'bg-red-400' : ''}`}></div>
              </div>
            </div>
            
            {/* Status indicator */}
            {isSpeaking && (
              <div className="absolute -top-1 -right-1 w-4 h-4 bg-green-500 rounded-full border-2 border-white animate-pulse"></div>
            )}
          </div>

          <div className="ml-4 flex-1">
            <div className="bg-white bg-opacity-90 rounded-lg p-2 min-h-12">
              <p className="text-gray-800 text-sm">
                {currentMessage || "Hello! I'm your AI assistant. Click a button to learn more about this page."}
              </p>
            </div>
          </div>
        </div>

        {/* Controls */}
        <div className="bg-white bg-opacity-10 p-3">
          <div className="flex flex-wrap gap-2">
            <button
              onClick={() => provideGuidance('auto-agent')}
              className="flex-1 min-w-[100px] bg-white bg-opacity-20 hover:bg-opacity-30 text-white py-2 px-3 rounded-lg text-sm transition-colors flex items-center justify-center"
            >
              <FaComment className="mr-1" /> Guide Me
            </button>
            
            <button
              onClick={toggleMute}
              className={`min-w-[40px] py-2 px-3 rounded-lg text-sm transition-colors flex items-center justify-center ${isMuted ? 'bg-red-500' : 'bg-white bg-opacity-20 hover:bg-opacity-30'} text-white`}
            >
              <FaVolumeUp className={isMuted ? 'text-gray-300' : ''} />
            </button>
            
            {isSpeaking && (
              <button
                onClick={stopSpeaking}
                className="min-w-[40px] bg-red-500 hover:bg-red-600 text-white py-2 px-3 rounded-lg text-sm transition-colors flex items-center justify-center"
              >
                <FaTimes />
              </button>
            )}
          </div>
          
          {/* Quick navigation */}
          <div className="mt-3 grid grid-cols-2 gap-2">
            <button
              onClick={() => {
                onPageChange('home');
                provideGuidance('home');
              }}
              className="bg-white bg-opacity-20 hover:bg-opacity-30 text-white py-1.5 px-2 rounded text-xs transition-colors"
            >
              Home
            </button>
            <button
              onClick={() => {
                onPageChange('services');
                provideGuidance('services');
              }}
              className="bg-white bg-opacity-20 hover:bg-opacity-30 text-white py-1.5 px-2 rounded text-xs transition-colors"
            >
              Services
            </button>
            <button
              onClick={() => {
                onPageChange('image-processing');
                provideGuidance('image-processing');
              }}
              className="bg-white bg-opacity-20 hover:bg-opacity-30 text-white py-1.5 px-2 rounded text-xs transition-colors"
            >
              Image Processing
            </button>
            <button
              onClick={() => {
                onPageChange('gallery');
                provideGuidance('gallery');
              }}
              className="bg-white bg-opacity-20 hover:bg-opacity-30 text-white py-1.5 px-2 rounded text-xs transition-colors"
            >
              Gallery
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default TalkingAgent;