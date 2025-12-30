import React, { useState, useEffect, useRef } from 'react';
import { FaComment, FaRobot, FaBolt, FaMagic, FaStar } from 'react-icons/fa';

const WalkingRobotAgent = ({ onPageGuidance }) => {
  const [position, setPosition] = useState({ x: 100, y: 100 });
  const [isBlinking, setIsBlinking] = useState(false);
  const [isWalking, setIsWalking] = useState(false);
  const [isVisible, setIsVisible] = useState(true);
  const [showSpeechBubble, setShowSpeechBubble] = useState(false);
  const [speechText, setSpeechText] = useState("Upload an image, describe your request");
  const [stepPhase, setStepPhase] = useState(0); // For alternating leg movements
  const [direction, setDirection] = useState('right'); // For walking direction

  const agentRef = useRef(null);
  const containerRef = useRef(null);
  const movementIntervalRef = useRef(null);
  const blinkIntervalRef = useRef(null);
  const walkAnimationRef = useRef(null);
  const speechIntervalRef = useRef(null);

  // Array of short, thought-like service-related messages
  const serviceMessages = [
    "Need background removal?",
    "Want AI image enhancement?",
    "Change image backgrounds?",
    "Remove unwanted objects?",
    "Enhance image quality?",
    "AI-powered editing?",
    "Change image colors?",
    "Make photos vibrant?",
    "Automatic enhancement?",
    "Creative photo effects?",
    "Upscale images?",
    "Easy photo editing?",
    "Convert image styles?",
    "Improve backgrounds?",
    "Quick image processing?",
    "Try our AI auto agent!",
    "One-click transforms!",
    "Simple professional editing!",
    "AI solutions!",
    "Future of processing!"
  ];

  // Function to move the agent to a new position with walking animation
  const moveAgent = () => {
    if (!containerRef.current) return;

    const containerRect = containerRef.current.getBoundingClientRect();
    const agentRect = agentRef.current?.getBoundingClientRect();

    if (!agentRect) return;

    // Calculate boundaries to ensure robot and speech bubble stay on screen
    const robotWidth = agentRect.width;
    const robotHeight = agentRect.height;
    const speechBubbleHeight = 112; // Approximate height of speech bubble with padding

    // Calculate max positions ensuring both robot and speech bubble stay on screen
    const maxX = window.innerWidth - robotWidth - 20;
    const maxY = window.innerHeight - robotHeight - speechBubbleHeight - 40; // Extra padding for speech bubble

    // Ensure we don't go above the navbar area
    const minY = 80; // Account for navbar height

    const newX = Math.max(20, Math.min(maxX, Math.random() * maxX));
    const newY = Math.max(minY, Math.min(maxY, Math.random() * (maxY - minY) + minY));

    // Determine direction for animation
    const currentX = position.x;
    setDirection(newX > currentX ? 'right' : 'left');

    setPosition({ x: newX, y: newY });
  };

  // Function to make the agent speak
  const speak = (text) => {
    setSpeechText(text);
    setShowSpeechBubble(true);

    // Auto-hide speech bubble after 5 seconds
    setTimeout(() => {
      setShowSpeechBubble(false);
    }, 5000);
  };

  // Function to provide guidance about the current page
  const provideGuidance = () => {
    const guidanceText = "Upload an image, describe your request";
    speak(guidanceText);
    if (onPageGuidance) onPageGuidance(guidanceText);
  };

  // Function to show random service messages
  const showRandomServiceMessage = () => {
    const randomIndex = Math.floor(Math.random() * serviceMessages.length);
    const message = serviceMessages[randomIndex];
    speak(message);
  };

  // Initialize animations
  useEffect(() => {
    // Walking animation - move agent around the page periodically
    movementIntervalRef.current = setInterval(() => {
      setIsWalking(true);
      moveAgent();

      // Reset walking state after animation completes
      setTimeout(() => {
        setIsWalking(false);
      }, 1000);
    }, 8000); // Move every 8 seconds

    // Blinking animation
    blinkIntervalRef.current = setInterval(() => {
      setIsBlinking(true);
      setTimeout(() => {
        setIsBlinking(false);
      }, 150); // Blink for 150ms
    }, 5000 + Math.random() * 3000); // Random blink interval between 5-8 seconds

    // Walking leg animation - alternate leg positions for walking effect
    walkAnimationRef.current = setInterval(() => {
      setStepPhase(prev => (prev + 1) % 2); // Alternate between 0 and 1
    }, 300); // Change leg position every 300ms for walking motion

    // Show random service messages periodically
    speechIntervalRef.current = setInterval(() => {
      showRandomServiceMessage();
    }, 12000); // Show a new message every 12 seconds

    // Initial positioning
    moveAgent();

    // Initial welcome message
    setTimeout(() => {
      speak("Upload an image, describe your request");
    }, 1000);

    return () => {
      if (movementIntervalRef.current) clearInterval(movementIntervalRef.current);
      if (blinkIntervalRef.current) clearInterval(blinkIntervalRef.current);
      if (walkAnimationRef.current) clearInterval(walkAnimationRef.current);
      if (speechIntervalRef.current) clearInterval(speechIntervalRef.current);
    };
  }, []);

  // Handle click to provide guidance
  const handleAgentClick = () => {
    provideGuidance();
  };

  return (
    <div
      ref={containerRef}
      className="fixed inset-0 pointer-events-none z-50 overflow-hidden"
      style={{ height: '100vh', zIndex: 9999 }}
    >
      {/* Animated Walking Robot Agent */}
      <div
        ref={agentRef}
        className={`absolute transition-all duration-1000 ease-in-out cursor-pointer pointer-events-auto ${
          isWalking ? 'transition-all duration-1000' : ''
        }`}
        style={{
          left: `${position.x}px`,
          top: `${position.y}px`,
          transform: isWalking ? `scale(1.1) ${direction === 'right' ? 'rotateY(0deg)' : 'rotateY(180deg)'}` : `rotateY(${direction === 'right' ? '0deg' : '180deg'})`,
          zIndex: 9999
        }}
        onClick={handleAgentClick}
      >
        {/* Thought bubble - Cloud shaped like robot thinking */}
        <div className="absolute -top-32 left-1/2 transform -translate-x-1/2 z-50" style={{ zIndex: 10000 }}>
          {showSpeechBubble && (
            <div
              className="thought-bubble text-gray-800 relative"
              style={{
                maxWidth: '280px',
                minWidth: '120px',
                fontSize: '0.9rem',
                display: 'inline-block'
              }}
            >
              <div className="flex items-start relative z-10">
                <FaStar className="text-yellow-400 mt-0.5 mr-2 flex-shrink-0" size={14} />
                <span>{speechText}</span>
              </div>
            </div>
          )}
        </div>

        {/* Walking Robot Character - Increased size */}
        <div className="relative scale-150"> {/* Scale up the entire robot to make it bigger */}
          {/* Main robot body */}
          <div className="w-16 h-16 bg-gradient-to-br from-blue-600 to-indigo-800 rounded-xl flex items-center justify-center border-4 border-blue-400 shadow-2xl relative overflow-hidden">
            {/* Robot texture/panel effect */}
            <div className="absolute inset-0 bg-gradient-to-tr from-blue-300 from-0% via-transparent via-50% to-transparent to-100% opacity-30 rounded-xl"></div>

            {/* Robot face/panel */}
            <div className="absolute inset-2 bg-gradient-to-b from-blue-100 to-blue-300 rounded-lg flex flex-col items-center justify-center">
              {/* Eyes */}
              <div className="flex space-x-3 mb-1">
                <div className="w-4 h-4 bg-cyan-300 rounded-full relative overflow-hidden">
                  {isBlinking ? (
                    <div className="absolute inset-0 bg-black top-1/2 h-0.5"></div>
                  ) : (
                    <div className="w-full h-full flex items-center justify-center">
                      <div className="w-2 h-2 bg-black rounded-full"></div>
                    </div>
                  )}
                </div>
                <div className="w-4 h-4 bg-cyan-300 rounded-full relative overflow-hidden">
                  {isBlinking ? (
                    <div className="absolute inset-0 bg-black top-1/2 h-0.5"></div>
                  ) : (
                    <div className="w-full h-full flex items-center justify-center">
                      <div className="w-2 h-2 bg-black rounded-full"></div>
                    </div>
                  )}
                </div>
              </div>

              {/* Mouth */}
              <div className="w-6 h-1.5 bg-gray-700 rounded-full"></div>
            </div>

            {/* Robot antenna */}
            <div className="absolute -top-3 left-1/2 transform -translate-x-1/2 w-1.5 h-4 bg-blue-400 rounded-t-full"></div>
            <div className="absolute -top-1 left-1/2 transform -translate-x-1/2 w-3 h-3 bg-red-500 rounded-full animate-pulse"></div>

            {/* Decorative elements */}
            <div className="absolute top-1 right-1 w-2 h-2 bg-green-400 rounded-full"></div>
            <div className="absolute top-1 left-1 w-2 h-2 bg-yellow-400 rounded-full"></div>
          </div>

          {/* Walking legs animation - alternate positions for realistic walking motion */}
          <div className="absolute -bottom-5 left-1/2 transform -translate-x-1/2 flex justify-center space-x-2">
            {/* Left leg - moves up when stepPhase is 0, down when stepPhase is 1 */}
            <div className={`w-3 h-6 bg-gradient-to-b from-blue-700 to-blue-900 rounded-b-full transition-transform duration-300 ${
              stepPhase === 0 ? 'transform -translate-y-1' : 'transform translate-y-0.5'
            }`}></div>

            {/* Right leg - moves down when stepPhase is 0, up when stepPhase is 1 */}
            <div className={`w-3 h-6 bg-gradient-to-b from-blue-700 to-blue-900 rounded-b-full transition-transform duration-300 ${
              stepPhase === 0 ? 'transform translate-y-0.5' : 'transform -translate-y-1'
            }`}></div>
          </div>

          {/* Walking motion effect - subtle ground interaction */}
          <div className="absolute -bottom-7 left-1/2 transform -translate-x-1/2 w-12 h-2 bg-gradient-to-r from-gray-400 to-gray-600 rounded-full opacity-50 animate-pulse"></div>
        </div>
      </div>
    </div>
  );
};

export default WalkingRobotAgent;