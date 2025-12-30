import React, { useState, useRef, useEffect } from 'react';
import { FaCrop, FaExpandArrowsAlt, FaRedo, FaDownload, FaTimes, FaUndo, FaRedoAlt } from 'react-icons/fa';

const ImageEditorModal = ({ isOpen, onClose, imageSrc }) => {
  const [image, setImage] = useState(null);
  const [originalImage, setOriginalImage] = useState(null);
  const [rotation, setRotation] = useState(0);
  const [scale, setScale] = useState(1);
  const [position, setPosition] = useState({ x: 0, y: 0 });
  const [isDragging, setIsDragging] = useState(false);
  const [dragStart, setDragStart] = useState({ x: 0, y: 0 });
  const [mode, setMode] = useState('move'); // 'move', 'crop'
  const [cropStart, setCropStart] = useState(null);
  const [cropEnd, setCropEnd] = useState(null);
  const [isCropping, setIsCropping] = useState(false);
  
  const canvasRef = useRef(null);
  const imageRef = useRef(null);
  const containerRef = useRef(null);

  // Load image when imageSrc changes
  useEffect(() => {
    if (imageSrc) {
      const img = new Image();
      img.crossOrigin = 'Anonymous';
      img.onload = () => {
        setImage(img);
        setOriginalImage(img);
        setRotation(0);
        setScale(1);
        setPosition({ x: 0, y: 0 });
      };
      img.src = imageSrc;
    }
  }, [imageSrc]);

  // Handle mouse events for dragging
  const handleMouseDown = (e) => {
    if (mode === 'move') {
      setIsDragging(true);
      setDragStart({
        x: e.clientX - position.x,
        y: e.clientY - position.y
      });
    } else if (mode === 'crop') {
      setIsCropping(true);
      const rect = containerRef.current.getBoundingClientRect();
      const x = e.clientX - rect.left;
      const y = e.clientY - rect.top;
      setCropStart({ x, y });
      setCropEnd({ x, y });
    }
  };

  const handleMouseMove = (e) => {
    if (isDragging && mode === 'move') {
      const rect = containerRef.current.getBoundingClientRect();
      const x = e.clientX - dragStart.x;
      const y = e.clientY - dragStart.y;
      
      // Boundary checks to keep image within container
      const maxX = rect.width / 2;
      const maxY = rect.height / 2;
      
      setPosition({
        x: Math.max(-maxX, Math.min(maxX, x)),
        y: Math.max(-maxY, Math.min(maxY, y))
      });
    } else if (isCropping && mode === 'crop' && cropStart) {
      const rect = containerRef.current.getBoundingClientRect();
      const x = e.clientX - rect.left;
      const y = e.clientY - rect.top;
      setCropEnd({ x, y });
    }
  };

  const handleMouseUp = () => {
    setIsDragging(false);
    if (isCropping) {
      setIsCropping(false);
    }
  };

  const rotateImage = (direction) => {
    const newRotation = direction === 'left' ? rotation - 90 : rotation + 90;
    setRotation(newRotation % 360);
  };

  const resizeImage = (direction) => {
    const factor = direction === 'in' ? 1.1 : 0.9;
    setScale(prev => Math.max(0.1, Math.min(3, prev * factor)));
  };

  const resetImage = () => {
    setRotation(0);
    setScale(1);
    setPosition({ x: 0, y: 0 });
    setCropStart(null);
    setCropEnd(null);
  };

  const applyCrop = () => {
    if (!image || !cropStart || !cropEnd) return;

    const containerRect = containerRef.current.getBoundingClientRect();
    const containerWidth = containerRect.width;
    const containerHeight = containerRect.height;

    // Calculate the crop coordinates relative to the displayed image
    const imgDisplayWidth = image.width * scale;
    const imgDisplayHeight = image.height * scale;

    // Calculate where the image is positioned in the container
    const imgLeft = (containerWidth - imgDisplayWidth) / 2 + position.x;
    const imgTop = (containerHeight - imgDisplayHeight) / 2 + position.y;

    // Adjust crop coordinates to be relative to the image
    const adjustedStartX = cropStart.x - imgLeft;
    const adjustedStartY = cropStart.y - imgTop;
    const adjustedEndX = cropEnd.x - imgLeft;
    const adjustedEndY = cropEnd.y - imgTop;

    // Calculate crop coordinates in original image space
    const originalX = adjustedStartX / scale;
    const originalY = adjustedStartY / scale;
    const originalWidth = Math.abs(adjustedEndX - adjustedStartX) / scale;
    const originalHeight = Math.abs(adjustedEndY - adjustedStartY) / scale;

    // Ensure coordinates are within image bounds
    const safeX = Math.max(0, Math.min(image.width, originalX));
    const safeY = Math.max(0, Math.min(image.height, originalY));
    const safeWidth = Math.min(image.width - safeX, originalWidth);
    const safeHeight = Math.min(image.height - safeY, originalHeight);

    if (safeWidth <= 0 || safeHeight <= 0) return;

    const canvas = document.createElement('canvas');
    const ctx = canvas.getContext('2d');

    canvas.width = safeWidth;
    canvas.height = safeHeight;

    // Draw cropped portion from original image
    ctx.drawImage(
      image,
      safeX, safeY, safeWidth, safeHeight,
      0, 0, safeWidth, safeHeight
    );

    // Update image with cropped version
    const newImage = new Image();
    newImage.src = canvas.toDataURL('image/png');
    newImage.onload = () => {
      setImage(newImage);
      setOriginalImage(newImage);
      setCropStart(null);
      setCropEnd(null);
      setPosition({ x: 0, y: 0 });
      setScale(1);
      setRotation(0);
    };
  };

  const addWatermark = (canvas, ctx) => {
    // Add a sophisticated watermark similar to backend
    const watermarkSize = Math.min(canvas.width, canvas.height) / 8; // Scale watermark with image size
    const padding = 20;

    // Draw a dark kite-shaped watermark in the bottom-left corner
    ctx.save();

    // Set up for drawing the kite shape
    ctx.fillStyle = 'rgba(15, 15, 25, 0.85)'; // Super dark fill
    ctx.strokeStyle = 'rgba(140, 140, 160, 0.9)'; // Brighter outline
    ctx.lineWidth = 3;

    // Calculate kite position in bottom-left
    const centerX = padding + watermarkSize / 3;
    const centerY = canvas.height - padding - watermarkSize / 3;

    // Define kite shape points
    const topY = centerY - watermarkSize / 2;
    const bottomY = centerY + watermarkSize / 2;
    const leftX = centerX - watermarkSize / 3;
    const rightX = centerX + watermarkSize / 3;

    // Draw the kite shape
    ctx.beginPath();
    ctx.moveTo(centerX, topY);      // Top point
    ctx.lineTo(rightX, centerY);    // Right point
    ctx.lineTo(centerX, bottomY);   // Bottom point
    ctx.lineTo(leftX, centerY);     // Left point
    ctx.closePath();

    ctx.fill();
    ctx.stroke();

    // Add inner highlight for glossy effect
    ctx.fillStyle = 'rgba(250, 250, 255, 0.6)';
    ctx.beginPath();
    ctx.moveTo(centerX, topY + 3);
    ctx.lineTo(rightX - 3, centerY);
    ctx.lineTo(centerX, bottomY - 3);
    ctx.lineTo(leftX + 3, centerY);
    ctx.closePath();
    ctx.fill();

    // Add a small text identifier (using first 2 chars of a unique ID)
    const uniqueId = Math.random().toString(36).substring(2, 4).toUpperCase();
    ctx.font = `${Math.max(8, watermarkSize / 5)}px Arial`;
    ctx.fillStyle = 'rgba(250, 250, 255, 0.9)';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillText(uniqueId, rightX - watermarkSize / 6, centerY + 5);

    ctx.restore();
  };

  const downloadImage = () => {
    if (!image) return;

    // Calculate appropriate canvas size based on transformations
    const canvas = document.createElement('canvas');
    const ctx = canvas.getContext('2d');

    // Calculate the bounding box of the transformed image
    const imgWidth = image.width * scale;
    const imgHeight = image.height * scale;

    // Calculate rotated dimensions
    const rad = rotation * Math.PI / 180;
    const sin = Math.abs(Math.sin(rad));
    const cos = Math.abs(Math.cos(rad));

    const newWidth = imgWidth * cos + imgHeight * sin;
    const newHeight = imgWidth * sin + imgHeight * cos;

    // Set canvas size to fit the rotated image
    canvas.width = Math.ceil(newWidth);
    canvas.height = Math.ceil(newHeight);

    // Apply transformations
    ctx.save();

    // Move to center of canvas
    ctx.translate(canvas.width / 2, canvas.height / 2);

    // Apply rotation
    ctx.rotate((rotation * Math.PI) / 180);

    // Apply scale
    ctx.scale(scale, scale);

    // Draw image centered
    ctx.drawImage(
      image,
      -image.width / 2,
      -image.height / 2,
      image.width,
      image.height
    );

    ctx.restore();

    // Add watermark
    addWatermark(canvas, ctx);

    // Create download link
    const link = document.createElement('a');
    link.download = 'edited-image.png';
    link.href = canvas.toDataURL('image/png');
    link.click();
  };

  if (!isOpen || !image) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-75 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-xl w-full max-w-6xl h-5/6 flex flex-col">
        {/* Header */}
        <div className="flex justify-between items-center p-4 border-b">
          <h2 className="text-xl font-semibold">Image Editor</h2>
          <button 
            onClick={onClose}
            className="text-gray-500 hover:text-gray-700"
          >
            <FaTimes size={20} />
          </button>
        </div>

        {/* Toolbar */}
        <div className="p-4 border-b flex flex-wrap gap-2">
          <button
            onClick={() => setMode('move')}
            className={`flex items-center px-3 py-2 rounded ${
              mode === 'move' ? 'bg-indigo-600 text-white' : 'bg-gray-200 text-gray-700'
            }`}
          >
            <FaExpandArrowsAlt className="mr-2" /> Move
          </button>
          
          <button
            onClick={() => setMode('crop')}
            className={`flex items-center px-3 py-2 rounded ${
              mode === 'crop' ? 'bg-indigo-600 text-white' : 'bg-gray-200 text-gray-700'
            }`}
          >
            <FaCrop className="mr-2" /> Crop
          </button>

          {mode === 'crop' && cropStart && cropEnd && (
            <button
              onClick={applyCrop}
              className="flex items-center px-3 py-2 bg-green-600 text-white rounded hover:bg-green-700"
            >
              Apply Crop
            </button>
          )}

          <button
            onClick={() => rotateImage('left')}
            className="flex items-center px-3 py-2 bg-gray-200 text-gray-700 rounded hover:bg-gray-300"
          >
            <FaUndo className="mr-2" /> Rotate Left
          </button>
          
          <button
            onClick={() => rotateImage('right')}
            className="flex items-center px-3 py-2 bg-gray-200 text-gray-700 rounded hover:bg-gray-300"
          >
            <FaRedoAlt className="mr-2" /> Rotate Right
          </button>
          
          <button
            onClick={() => resizeImage('in')}
            className="flex items-center px-3 py-2 bg-gray-200 text-gray-700 rounded hover:bg-gray-300"
          >
            <span className="mr-2">+</span> Zoom In
          </button>
          
          <button
            onClick={() => resizeImage('out')}
            className="flex items-center px-3 py-2 bg-gray-200 text-gray-700 rounded hover:bg-gray-300"
          >
            <span className="mr-2">-</span> Zoom Out
          </button>
          
          <button
            onClick={resetImage}
            className="flex items-center px-3 py-2 bg-gray-200 text-gray-700 rounded hover:bg-gray-300"
          >
            <FaRedo className="mr-2" /> Reset
          </button>
          
          <button
            onClick={downloadImage}
            className="flex items-center px-3 py-2 bg-indigo-600 text-white rounded hover:bg-indigo-700 ml-auto"
          >
            <FaDownload className="mr-2" /> Download
          </button>
        </div>

        {/* Editor Area */}
        <div 
          ref={containerRef}
          className="flex-1 relative overflow-hidden bg-gray-100"
          onMouseDown={handleMouseDown}
          onMouseMove={handleMouseMove}
          onMouseUp={handleMouseUp}
          onMouseLeave={handleMouseUp}
        >
          <div className="w-full h-full flex items-center justify-center relative">
            <div 
              className="relative"
              style={{ 
                width: '100%', 
                height: '100%', 
                display: 'flex', 
                alignItems: 'center', 
                justifyContent: 'center' 
              }}
            >
              <img
                ref={imageRef}
                src={image.src}
                alt="Editable"
                className="max-w-full max-h-full object-contain"
                style={{
                  cursor: mode === 'move' ? 'grab' : 'default',
                  position: 'absolute',
                  left: '50%',
                  top: '50%',
                  transform: `translate(${position.x}px, ${position.y}px) rotate(${rotation}deg) scale(${scale})`,
                  transformOrigin: 'center center',
                }}
                draggable={false}
              />
              
              {/* Crop selection overlay */}
              {mode === 'crop' && cropStart && cropEnd && (
                <div
                  className="absolute border-2 border-blue-500 border-dashed bg-blue-500 bg-opacity-20"
                  style={{
                    left: Math.min(cropStart.x, cropEnd.x),
                    top: Math.min(cropStart.y, cropEnd.y),
                    width: Math.abs(cropEnd.x - cropStart.x),
                    height: Math.abs(cropEnd.y - cropStart.y),
                  }}
                />
              )}
            </div>
          </div>
        </div>

        {/* Status Bar */}
        <div className="p-2 border-t text-sm text-gray-600 flex justify-between">
          <div>Mode: {mode}</div>
          <div>Rotation: {rotation}° | Scale: {(scale * 100).toFixed(0)}%</div>
        </div>
      </div>
    </div>
  );
};

export default ImageEditorModal;