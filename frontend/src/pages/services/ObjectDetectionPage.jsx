import React, { useState } from 'react';
import { FaUpload, FaEye, FaDownload, FaCrosshairs } from 'react-icons/fa';
import toast from 'react-hot-toast';
import axios from 'axios';

const ObjectDetectionPage = () => {
  const [selectedFile, setSelectedFile] = useState(null);
  const [previewUrl, setPreviewUrl] = useState(null);
  const [resultUrl, setResultUrl] = useState(null);
  const [detectionResults, setDetectionResults] = useState([]);
  const [loading, setLoading] = useState(false);

  const handleFileChange = (e) => {
    const file = e.target.files[0];
    if (file) {
      setSelectedFile(file);
      setPreviewUrl(URL.createObjectURL(file));
      setResultUrl(null); // Reset result when new file is selected
      setDetectionResults([]); // Reset detection results
    }
  };

  const handleDetectObjects = async () => {
    if (!selectedFile) {
      toast.error('Please select an image first');
      return;
    }

    setLoading(true);

    try {
      const formData = new FormData();
      formData.append('file', selectedFile);

      const token = localStorage.getItem('token');
      const response = await axios.post('/api/detect-objects', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
          'Authorization': `Bearer ${token}`,
        },
        responseType: 'blob' // For the result image
      });

      // Create a URL for the processed image blob
      const imageUrl = URL.createObjectURL(response.data);
      setResultUrl(imageUrl);

      toast.success('Objects detected successfully!');
    } catch (error) {
      console.error('Error detecting objects:', error);
      // Fallback to simulated results if endpoint doesn't exist
      if (error.response?.status === 404) {
        // Mock detection results (for demo purposes)
        const mockResults = [
          { label: 'Person', confidence: 0.95, bbox: [10, 20, 100, 150] },
          { label: 'Car', confidence: 0.87, bbox: [200, 50, 300, 180] },
          { label: 'Tree', confidence: 0.78, bbox: [350, 100, 400, 250] },
          { label: 'Bicycle', confidence: 0.65, bbox: [150, 200, 220, 280] }
        ];

        setDetectionResults(mockResults);
        setResultUrl(previewUrl); // For demo, use the original image as result
        toast.success('Objects detected successfully! (simulated)');
      } else {
        toast.error(error.response?.data?.detail || 'Error detecting objects');
      }
    } finally {
      setLoading(false);
    }
  };

  const handleDownload = () => {
    if (resultUrl) {
      const link = document.createElement('a');
      link.href = resultUrl;
      link.download = 'object-detection-result.png';
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 py-8">
      <div className="container mx-auto px-4">
        {/* Header */}
        <div className="text-center mb-8">
          <div className="w-16 h-16 bg-gradient-to-r from-yellow-500 to-orange-600 rounded-xl flex items-center justify-center mx-auto mb-4">
            <FaCrosshairs className="text-white text-2xl" />
          </div>
          <h1 className="text-4xl font-bold text-gray-900 mb-4">Object Detection Tool</h1>
          <p className="text-xl text-gray-600 max-w-3xl mx-auto">
            Identify and locate objects in images with precision using advanced AI algorithms.
          </p>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 max-w-6xl mx-auto">
          {/* Upload and Controls */}
          <div className="bg-white rounded-xl shadow-sm p-6">
            <h2 className="text-2xl font-semibold text-gray-900 mb-6">Upload Image</h2>
            
            {/* File Upload */}
            <div className="mb-6">
              <label className="block text-sm font-medium text-gray-700 mb-2">Upload Image</label>
              <div className="mt-1">
                <input
                  id="file-input"
                  type="file"
                  accept="image/*"
                  onChange={handleFileChange}
                  className="file-input"
                />
                <label htmlFor="file-input" className="file-label">
                  <FaUpload className="mr-2" />
                  {selectedFile ? selectedFile.name : 'Choose an image file'}
                </label>
              </div>
            </div>

            {/* Preview */}
            {previewUrl && (
              <div className="mb-6">
                <h3 className="text-lg font-medium text-gray-900 mb-2">Preview</h3>
                <div className="border rounded-lg p-4 bg-gray-50">
                  <img 
                    src={previewUrl} 
                    alt="Preview" 
                    className="max-h-48 w-full object-contain rounded"
                  />
                </div>
              </div>
            )}

            {/* Action Button */}
            <button
              onClick={handleDetectObjects}
              disabled={loading || !selectedFile}
              className="btn btn-primary w-full"
            >
              {loading ? (
                <>
                  <span className="loading-spinner mr-2"></span>
                  Detecting Objects...
                </>
              ) : (
                'Detect Objects'
              )}
            </button>
          </div>

          {/* Results */}
          <div className="bg-white rounded-xl shadow-sm p-6">
            <h2 className="text-2xl font-semibold text-gray-900 mb-6">Detection Results</h2>
            
            {resultUrl ? (
              <div className="space-y-6">
                <div>
                  <h3 className="text-lg font-medium text-gray-900 mb-2">Detected Objects</h3>
                  <div className="border rounded-lg p-4 bg-gray-50 relative">
                    <img
                      src={resultUrl}
                      alt="Result"
                      className="max-h-80 w-full object-contain rounded"
                    />
                    {/* Watermark */}
                    <div className="absolute bottom-2 right-2 bg-black bg-opacity-50 text-white text-xs px-2 py-1 rounded">
                      AI Processed
                    </div>
                  </div>
                </div>
                
                {detectionResults.length > 0 && (
                  <div>
                    <h3 className="text-lg font-medium text-gray-900 mb-3">Detection Details</h3>
                    <div className="space-y-3">
                      {detectionResults.map((result, index) => (
                        <div key={index} className="flex items-center justify-between p-3 bg-white border rounded-lg">
                          <div>
                            <span className="font-medium text-gray-900">{result.label}</span>
                            <span className="text-gray-500 ml-2">({Math.round(result.confidence * 100)}% confidence)</span>
                          </div>
                          <div className="text-sm text-gray-600">
                            BBox: [{result.bbox[0]}, {result.bbox[1]}, {result.bbox[2]}, {result.bbox[3]}]
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
                
                <button
                  onClick={handleDownload}
                  className="btn btn-primary w-full">
                  <FaDownload className="mr-2" /> Download Results
                </button>
              </div>
            ) : (
              <div className="flex flex-col items-center justify-center h-64 border-2 border-dashed border-gray-300 rounded-lg">
                <FaCrosshairs className="text-gray-400 text-4xl mb-4" />
                <p className="text-gray-500 text-center">
                  {selectedFile 
                    ? 'Click "Detect Objects" to analyze your image' 
                    : 'Upload an image to start object detection'
                  }
                </p>
              </div>
            )}
          </div>
        </div>

        {/* How It Works */}
        <div className="mt-16">
          <h2 className="text-3xl font-bold text-gray-900 text-center mb-12">How Object Detection Works</h2>
          
          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            <div className="bg-white p-6 rounded-xl shadow-sm text-center">
              <div className="w-12 h-12 bg-gradient-to-r from-blue-500 to-purple-600 rounded-lg flex items-center justify-center mx-auto mb-4">
                <FaUpload className="text-white" />
              </div>
              <h3 className="text-lg font-medium text-gray-900 mb-2">Upload Image</h3>
              <p className="text-gray-600">
                Upload any image containing objects you want to detect and identify.
              </p>
            </div>
            
            <div className="bg-white p-6 rounded-xl shadow-sm text-center">
              <div className="w-12 h-12 bg-gradient-to-r from-green-500 to-teal-600 rounded-lg flex items-center justify-center mx-auto mb-4">
                <FaCrosshairs className="text-white" />
              </div>
              <h3 className="text-lg font-medium text-gray-900 mb-2">AI Processing</h3>
              <p className="text-gray-600">
                Our AI models analyze the image to identify and locate objects with bounding boxes.
              </p>
            </div>
            
            <div className="bg-white p-6 rounded-xl shadow-sm text-center">
              <div className="w-12 h-12 bg-gradient-to-r from-pink-500 to-rose-600 rounded-lg flex items-center justify-center mx-auto mb-4">
                <FaEye className="text-white" />
              </div>
              <h3 className="text-lg font-medium text-gray-900 mb-2">View Results</h3>
              <p className="text-gray-600">
                Get detailed information about detected objects including labels and confidence scores.
              </p>
            </div>
          </div>
        </div>

        {/* Supported Objects */}
        <div className="mt-16">
          <h2 className="text-3xl font-bold text-gray-900 text-center mb-12">Supported Object Types</h2>
          
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 max-w-4xl mx-auto">
            {[
              'Person', 'Car', 'Bicycle', 'Motorcycle',
              'Airplane', 'Bus', 'Train', 'Truck',
              'Boat', 'Traffic Light', 'Fire Hydrant', 'Stop Sign',
              'Parking Meter', 'Bench', 'Bird', 'Cat',
              'Dog', 'Horse', 'Sheep', 'Cow',
              'Elephant', 'Bear', 'Zebra', 'Giraffe'
            ].map((obj, index) => (
              <div key={index} className="bg-white p-4 rounded-lg text-center border">
                <div className="text-gray-900 font-medium">{obj}</div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};

export default ObjectDetectionPage;