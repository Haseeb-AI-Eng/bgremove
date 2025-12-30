import React, { useState } from 'react';
import { FaUpload, FaInfoCircle, FaDownload, FaEye, FaCamera, FaMapMarkerAlt, FaCalendarAlt } from 'react-icons/fa';
import toast from 'react-hot-toast';

const MetadataAnalyzerPage = () => {
  const [selectedFile, setSelectedFile] = useState(null);
  const [previewUrl, setPreviewUrl] = useState(null);
  const [metadata, setMetadata] = useState(null);
  const [loading, setLoading] = useState(false);

  const handleFileChange = (e) => {
    const file = e.target.files[0];
    if (file) {
      setSelectedFile(file);
      setPreviewUrl(URL.createObjectURL(file));
      setMetadata(null); // Reset metadata when new file is selected
    }
  };

  const handleAnalyzeMetadata = async () => {
    if (!selectedFile) {
      toast.error('Please select an image first');
      return;
    }

    setLoading(true);

    try {
      // Simulate AI processing
      await new Promise(resolve => setTimeout(resolve, 2000));
      
      // Mock metadata results (in a real app, this would come from the API)
      const mockMetadata = {
        fileName: selectedFile.name,
        fileSize: `${(selectedFile.size / 1024 / 1024).toFixed(2)} MB`,
        dimensions: '1920 x 1080',
        format: selectedFile.type.split('/')[1].toUpperCase(),
        camera: 'Canon EOS R5',
        lens: 'RF24-70mm f/2.8L IS USM',
        exposure: '1/125s f/8.0 ISO 400',
        focalLength: '50mm',
        location: 'New York, NY, USA',
        timestamp: '2023-06-15 14:30:22',
        software: 'Adobe Photoshop 24.0',
        colorProfile: 'sRGB',
        orientation: 'Landscape',
        brightness: 'Normal',
        contrast: 'High',
        saturation: 'Vibrant'
      };
      
      setMetadata(mockMetadata);
      toast.success('Metadata analyzed successfully!');
    } catch (error) {
      toast.error('Error analyzing metadata');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 py-8">
      <div className="container mx-auto px-4">
        {/* Header */}
        <div className="text-center mb-8">
          <div className="w-16 h-16 bg-gradient-to-r from-cyan-500 to-blue-600 rounded-xl flex items-center justify-center mx-auto mb-4">
            <FaInfoCircle className="text-white text-2xl" />
          </div>
          <h1 className="text-4xl font-bold text-gray-900 mb-4">Image Metadata Analyzer</h1>
          <p className="text-xl text-gray-600 max-w-3xl mx-auto">
            Extract detailed EXIF data and image information with our comprehensive metadata analysis tool.
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
              onClick={handleAnalyzeMetadata}
              disabled={loading || !selectedFile}
              className="btn btn-primary w-full"
            >
              {loading ? (
                <>
                  <span className="loading-spinner mr-2"></span>
                  Analyzing Metadata...
                </>
              ) : (
                'Analyze Metadata'
              )}
            </button>
          </div>

          {/* Results */}
          <div className="bg-white rounded-xl shadow-sm p-6">
            <h2 className="text-2xl font-semibold text-gray-900 mb-6">Metadata Results</h2>
            
            {metadata ? (
              <div className="space-y-6">
                <div>
                  <h3 className="text-lg font-medium text-gray-900 mb-3">File Information</h3>
                  <div className="space-y-3">
                    <div className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                      <span className="text-gray-600">File Name</span>
                      <span className="font-medium text-gray-900">{metadata.fileName}</span>
                    </div>
                    <div className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                      <span className="text-gray-600">File Size</span>
                      <span className="font-medium text-gray-900">{metadata.fileSize}</span>
                    </div>
                    <div className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                      <span className="text-gray-600">Dimensions</span>
                      <span className="font-medium text-gray-900">{metadata.dimensions}</span>
                    </div>
                    <div className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                      <span className="text-gray-600">Format</span>
                      <span className="font-medium text-gray-900">{metadata.format}</span>
                    </div>
                  </div>
                </div>
                
                <div>
                  <h3 className="text-lg font-medium text-gray-900 mb-3">Camera Information</h3>
                  <div className="space-y-3">
                    <div className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                      <span className="text-gray-600 flex items-center">
                        <FaCamera className="mr-2" /> Camera
                      </span>
                      <span className="font-medium text-gray-900">{metadata.camera}</span>
                    </div>
                    <div className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                      <span className="text-gray-600">Lens</span>
                      <span className="font-medium text-gray-900">{metadata.lens}</span>
                    </div>
                    <div className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                      <span className="text-gray-600">Exposure</span>
                      <span className="font-medium text-gray-900">{metadata.exposure}</span>
                    </div>
                    <div className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                      <span className="text-gray-600">Focal Length</span>
                      <span className="font-medium text-gray-900">{metadata.focalLength}</span>
                    </div>
                  </div>
                </div>
                
                <div>
                  <h3 className="text-lg font-medium text-gray-900 mb-3">Location & Time</h3>
                  <div className="space-y-3">
                    <div className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                      <span className="text-gray-600 flex items-center">
                        <FaMapMarkerAlt className="mr-2" /> Location
                      </span>
                      <span className="font-medium text-gray-900">{metadata.location}</span>
                    </div>
                    <div className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                      <span className="text-gray-600 flex items-center">
                        <FaCalendarAlt className="mr-2" /> Date & Time
                      </span>
                      <span className="font-medium text-gray-900">{metadata.timestamp}</span>
                    </div>
                  </div>
                </div>
                
                <button className="btn btn-primary w-full">
                  <FaDownload className="mr-2" /> Download Metadata
                </button>
              </div>
            ) : (
              <div className="flex flex-col items-center justify-center h-64 border-2 border-dashed border-gray-300 rounded-lg">
                <FaInfoCircle className="text-gray-400 text-4xl mb-4" />
                <p className="text-gray-500 text-center">
                  {selectedFile 
                    ? 'Click "Analyze Metadata" to extract image information' 
                    : 'Upload an image to start metadata analysis'
                  }
                </p>
              </div>
            )}
          </div>
        </div>

        {/* Features Section */}
        <div className="mt-16">
          <h2 className="text-3xl font-bold text-gray-900 text-center mb-12">Comprehensive Metadata Analysis</h2>
          
          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            <div className="bg-white p-6 rounded-xl shadow-sm">
              <div className="w-12 h-12 bg-gradient-to-r from-blue-500 to-purple-600 rounded-lg flex items-center justify-center mb-4">
                <FaInfoCircle className="text-white text-xl" />
              </div>
              <h3 className="text-lg font-semibold text-gray-900 mb-2">EXIF Data</h3>
              <p className="text-gray-600">
                Extract detailed camera settings, GPS coordinates, and other embedded metadata.
              </p>
            </div>
            
            <div className="bg-white p-6 rounded-xl shadow-sm">
              <div className="w-12 h-12 bg-gradient-to-r from-green-500 to-teal-600 rounded-lg flex items-center justify-center mb-4">
                <FaInfoCircle className="text-white text-xl" />
              </div>
              <h3 className="text-lg font-semibold text-gray-900 mb-2">Image Properties</h3>
              <p className="text-gray-600">
                Get comprehensive information about image dimensions, color profile, and format.
              </p>
            </div>
            
            <div className="bg-white p-6 rounded-xl shadow-sm">
              <div className="w-12 h-12 bg-gradient-to-r from-pink-500 to-rose-600 rounded-lg flex items-center justify-center mb-4">
                <FaInfoCircle className="text-white text-xl" />
              </div>
              <h3 className="text-lg font-semibold text-gray-900 mb-2">File Details</h3>
              <p className="text-gray-600">
                Access file size, creation date, and other important file system information.
              </p>
            </div>
          </div>
        </div>

        {/* Supported Formats */}
        <div className="mt-16 bg-white rounded-xl shadow-sm p-8">
          <h2 className="text-3xl font-bold text-gray-900 text-center mb-8">Supported Image Formats</h2>
          
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 max-w-4xl mx-auto">
            {['JPEG', 'PNG', 'TIFF', 'RAW', 'GIF', 'BMP', 'WEBP', 'HEIF'].map((format, index) => (
              <div key={index} className="bg-gray-50 p-4 rounded-lg text-center border">
                <div className="text-gray-900 font-medium">{format}</div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};

export default MetadataAnalyzerPage;