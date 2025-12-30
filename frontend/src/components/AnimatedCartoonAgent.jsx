import React, { useState, useEffect, useRef } from 'react';
import { FaComment, FaRobot } from 'react-icons/fa';

const AnimatedCartoonAgent = ({ onPageGuidance }) => {
  const [position, setPosition] = useState({ x: 100, y: 100 });
  const [isBlinking, setIsBlinking] = useState(false);
  const [isSmiling, setIsSmiling] = useState(false);
  const [isMoving, setIsMoving] = useState(false);
  const [isVisible, setIsVisible] = useState(true);
  const [showSpeechBubble, setShowSpeechBubble] = useState(false);
  const [speechText, setSpeechText] = useState("Hi there! I'm your cartoon assistant!");
  
  const agentRef = useRef(null);
  const containerRef = useRef(null);
  const movementIntervalRef = useRef(null);
  const blinkIntervalRef = useRef(null);
  const smileIntervalRef = useRef(null);

  // Function to move the agent to a random position
  const moveAgent = () => {
    if (!containerRef.current) return;
    
    const containerRect = containerRef.current.getBoundingClientRect();
    const agentRect = agentRef.current?.getBoundingClientRect();
    
    if (!agentRect) return;
    
    const maxX = containerRect.width - agentRect.width - 20;
    const maxY = containerRect.height - agentRect.height - 20;
    
    const newX = Math.random() * maxX;
    const newY = Math.random() * maxY;
    
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
    const guidanceText = "Welcome to the Auto Agent page! I'm your cartoon assistant. This page allows you to upload an image and give natural language instructions. The AI will understand your request and perform the appropriate image processing tasks automatically. Just upload an image, describe what you want done, and watch the magic happen!";
    speak(guidanceText);
    if (onPageGuidance) onPageGuidance(guidanceText);
  };

  // Initialize animations
  useEffect(() => {
    // Movement animation - move agent around the page periodically
    movementIntervalRef.current = setInterval(() => {
      setIsMoving(true);
      moveAgent();
      
      // Reset moving state after animation completes
      setTimeout(() => {
        setIsMoving(false);
      }, 1000);
    }, 8000); // Move every 8 seconds

    // Blinking animation
    blinkIntervalRef.current = setInterval(() => {
      setIsBlinking(true);
      setTimeout(() => {
        setIsBlinking(false);
      }, 150); // Blink for 150ms
    }, 5000 + Math.random() * 3000); // Random blink interval between 5-8 seconds

    // Smiling animation
    smileIntervalRef.current = setInterval(() => {
      setIsSmiling(true);
      setTimeout(() => {
        setIsSmiling(false);
      }, 1000); // Smile for 1 second
    }, 10000 + Math.random() * 5000); // Random smile interval between 10-15 seconds

    // Initial positioning
    moveAgent();

    // Initial welcome message
    setTimeout(() => {
      speak("Hello! I'm your cartoon assistant. Click me for help with this page!");
    }, 1000);

    return () => {
      if (movementIntervalRef.current) clearInterval(movementIntervalRef.current);
      if (blinkIntervalRef.current) clearInterval(blinkIntervalRef.current);
      if (smileIntervalRef.current) clearInterval(smileIntervalRef.current);
    };
  }, []);

  // Handle click to provide guidance
  const handleAgentClick = () => {
    provideGuidance();
  };

  return (
    <div 
      ref={containerRef}
      className="fixed inset-0 pointer-events-none z-30 overflow-hidden"
      style={{ height: '100vh' }}
    >
      {/* Animated Cartoon Agent */}
      <div
        ref={agentRef}
        className={`absolute transition-all duration-1000 ease-in-out cursor-pointer pointer-events-auto ${
          isMoving ? 'transition-all duration-1000' : ''
        }`}
        style={{
          left: `${position.x}px`,
          top: `${position.y}px`,
          transform: isMoving ? 'scale(1.1)' : 'scale(1)',
        }}
        onClick={handleAgentClick}
      >
        {/* Speech bubble */}
        {showSpeechBubble && (
          <div 
            className="absolute -top-24 left-1/2 transform -translate-x-1/2 bg-white text-gray-800 px-4 py-2 rounded-lg shadow-lg z-40 min-w-max"
            style={{ maxWidth: '300px' }}
          >
            <div className="relative">
              {speechText}
              <div className="absolute bottom-0 left-1/2 transform -translate-x-1/2 translate-y-full w-0 h-0 border-l-8 border-r-8 border-t-8 border-l-transparent border-r-transparent border-t-white"></div>
            </div>
          </div>
        )}

        {/* Cartoon Agent Character */}
        <div className="relative">
          {/* Main body */}
          <div className="w-16 h-16 bg-gradient-to-br from-blue-400 to-purple-500 rounded-full flex items-center justify-center border-4 border-white shadow-xl relative overflow-hidden">
            {/* Shiny effect */}
            <div className="absolute inset-0 bg-gradient-to-tr from-white from-0% via-transparent via-50% to-transparent to-100% opacity-30 rounded-full"></div>
            
            {/* Eyes */}
            <div className="flex space-x-3 px-2 absolute top-4">
              <div className="w-3 h-3 bg-white rounded-full relative overflow-hidden">
                {isBlinking ? (
                  <div className="absolute inset-0 bg-black top-1/2 h-0.5"></div>
                ) : (
                  <div className="w-full h-full flex items-center justify-center">
                    <div className="w-1.5 h-1.5 bg-black rounded-full"></div>
                  </div>
                )}
              </div>
              <div className="w-3 h-3 bg-white rounded-full relative overflow-hidden">
                {isBlinking ? (
                  <div className="absolute inset-0 bg-black top-1/2 h-0.5"></div>
                ) : (
                  <div className="w-full h-full flex items-center justify-center">
                    <div className="w-1.5 h-1.5 bg-black rounded-full"></div>
                  </div>
                )}
              </div>
            </div>

            {/* Mouth - changes when smiling */}
            <div className={`absolute bottom-4 left-1/2 transform -translate-x-1/2 w-6 h-3 transition-all duration-300 ${
              isSmiling 
                ? 'bg-red-400 rounded-full' 
                : 'bg-red-400 rounded-t-full'
            }`}>
              {/* Smile curve when smiling */}
              {isSmiling && (
                <div className="absolute top-0.5 left-1/2 transform -translate-x-1/2 w-4 h-2 border-b-2 border-red-600 border-t-0 border-l-0 border-r-0 rounded-b-full"></div>
              )}
            </div>
          </div>

          {/* Floating effect */}
          <div className="absolute -bottom-2 left-1/2 transform -translate-x-1/2 w-8 h-2 bg-gray-300 rounded-full opacity-50 animate-bounce"></div>
        </div>
      </div>
    </div>
  );
};

export default AnimatedCartoonAgent;