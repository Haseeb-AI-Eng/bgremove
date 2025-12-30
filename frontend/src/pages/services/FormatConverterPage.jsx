import React, { useState } from 'react';
import { FaUpload, FaFileExport, FaDownload, FaEye, FaCompress } from 'react-icons/fa';
import toast from 'react-hot-toast';

const FormatConverterPage = () => {
  const [selectedFile, setSelectedFile] = useState(null);
  const [previewUrl, setPreviewUrl] = useState(null);
  const [resultUrl, setResultUrl] = useState(null);
  const [loading, setLoading] = useState(false);
  const [targetFormat, setTargetFormat] = useState('jpg');
  const [quality, setQuality] = useState(85);

  const handleFileChange = (e) => {
    const file = e.target.files[0];
    if (file) {
      setSelectedFile(file);
      setPreviewUrl(URL.createObjectURL(file));
      setResultUrl(null); // Reset result when new file is selected
    }
  };

  const handleConvertFormat = async () => {
    if (!selectedFile) {
      toast.error('Please select an image first');
      return;
    }

    setLoading(true);

    try {
      // Simulate AI processing
      await new Promise(resolve => setTimeout(resolve, 2000));
      
      // For demo, we'll use the original image as the result
      // In a real app, this would be the converted image from the API
      setResultUrl(previewUrl);
      toast.success(`Image converted to ${targetFormat.toUpperCase()} successfully!`);
    } catch (error) {
      toast.error('Error converting image format');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 py-8">
      <div className="container mx-auto px-4">
        {/* Header */}
        <div className="text-center mb-8">
          <div className="w-16 h-16 bg-gradient-to-r from-emerald-500 to-teal-600 rounded-xl flex items-center justify-center mx-auto mb-4">
            <FaFileExport className="text-white text-2xl" />
          </div>
          <h1 className="text-4xl font-bold text-gray-900 mb-4">Format Converter</h1>
          <p className="text-xl text-gray-600 max-w-3xl mx-auto">
            Convert between image formats with smart compression and quality optimization.
          </p>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 max-w-6xl mx-auto">
          {/* Upload and Controls */}
          <div className="bg-white rounded-xl shadow-sm p-6">
            <h2 className="text-2xl font-semibold text-gray-900 mb-6">Upload Image</h2>
            
            {/* Target Format Selection */}
            <div className="mb-6">
              <label className="block text-sm font-medium text-gray-700 mb-2">Target Format</label>
              <select
                value={targetFormat}
                onChange={(e) => setTargetFormat(e.target.value)}
                className="input-field w-full"
              >
                <option value="jpg">JPG - Joint Photographic Experts Group</option>
                <option value="png">PNG - Portable Network Graphics</option>
                <option value="webp">WebP - Web Picture Format</option>
                <option value="gif">GIF - Graphics Interchange Format</option>
                <option value="bmp">BMP - Bitmap Image File</option>
                <option value="tiff">TIFF - Tagged Image File Format</option>
              </select>
            </div>

            {/* Quality Selection */}
            <div className="mb-6">
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Quality: {quality}%
              </label>
              <input
                type="range"
                min="1"
                max="100"
                value={quality}
                onChange={(e) => setQuality(parseInt(e.target.value))}
                className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer"
              />
              <div className="flex justify-between text-xs text-gray-500 mt-1">
                <span>Smaller File</span>
                <span>Balanced</span>
                <span>Better Quality</span>
              </div>
            </div>

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
              onClick={handleConvertFormat}
              disabled={loading || !selectedFile}
              className="btn btn-primary w-full"
            >
              {loading ? (
                <>
                  <span className="loading-spinner mr-2"></span>
                  Converting...
                </>
              ) : (
                `Convert to ${targetFormat.toUpperCase()}`
              )}
            </button>
          </div>

          {/* Results */}
          <div className="bg-white rounded-xl shadow-sm p-6">
            <h2 className="text-2xl font-semibold text-gray-900 mb-6">Converted Result</h2>
            
            {resultUrl ? (
              <div className="space-y-6">
                <div>
                  <h3 className="text-lg font-medium text-gray-900 mb-2">Converted Image</h3>
                  <div className="border rounded-lg p-4 bg-gray-50">
                    <img 
                      src={resultUrl} 
                      alt="Result" 
                      className="max-h-80 w-full object-contain rounded"
                    />
                  </div>
                </div>
                
                <div className="bg-gray-50 p-4 rounded-lg">
                  <h3 className="text-lg font-medium text-gray-900 mb-3">Conversion Details</h3>
                  <div className="space-y-2">
                    <div className="flex justify-between">
                      <span className="text-gray-600">Original Format:</span>
                      <span className="font-medium text-gray-900">
                        {selectedFile ? selectedFile.type.split('/')[1].toUpperCase() : 'N/A'}
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-600">Target Format:</span>
                      <span className="font-medium text-gray-900">{targetFormat.toUpperCase()}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-600">Quality:</span>
                      <span className="font-medium text-gray-900">{quality}%</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-600">File Size:</span>
                      <span className="font-medium text-gray-900">
                        {selectedFile ? `${(selectedFile.size / 1024).toFixed(2)} KB` : 'N/A'}
                      </span>
                    </div>
                  </div>
                </div>
                
                <div className="flex flex-wrap gap-3">
                  <button className="btn btn-primary flex-1 min-w-[120px]">
                    <FaDownload className="mr-2" /> Download
                  </button>
                  
                  <button className="btn btn-outline flex-1 min-w-[120px]">
                    <FaEye className="mr-2" /> Preview
                  </button>
                </div>
              </div>
            ) : (
              <div className="flex flex-col items-center justify-center h-64 border-2 border-dashed border-gray-300 rounded-lg">
                <FaFileExport className="text-gray-400 text-4xl mb-4" />
                <p className="text-gray-500 text-center">
                  {selectedFile 
                    ? 'Click "Convert" to change your image format' 
                    : 'Upload an image to start format conversion'
                  }
                </p>
              </div>
            )}
          </div>
        </div>

        {/* Format Comparison */}
        <div className="mt-16">
          <h2 className="text-3xl font-bold text-gray-900 text-center mb-12">Format Comparison</h2>
          
          <div className="overflow-x-auto">
            <table className="min-w-full bg-white rounded-xl shadow-sm">
              <thead>
                <tr className="bg-gray-50">
                  <th className="py-3 px-4 text-left text-sm font-semibold text-gray-900">Format</th>
                  <th className="py-3 px-4 text-left text-sm font-semibold text-gray-900">Best For</th>
                  <th className="py-3 px-4 text-left text-sm font-semibold text-gray-900">Quality</th>
                  <th className="py-3 px-4 text-left text-sm font-semibold text-gray-900">Compression</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200">
                <tr>
                  <td className="py-3 px-4 font-medium text-gray-900">JPG</td>
                  <td className="py-3 px-4 text-gray-600">Photographs, complex images</td>
                  <td className="py-3 px-4 text-gray-600">Good</td>
                  <td className="py-3 px-4 text-gray-600">Lossy, High</td>
                </tr>
                <tr>
                  <td className="py-3 px-4 font-medium text-gray-900">PNG</td>
                  <td className="py-3 px-4 text-gray-600">Graphics, transparency</td>
                  <td className="py-3 px-4 text-gray-600">Excellent</td>
                  <td className="py-3 px-4 text-gray-600">Lossless</td>
                </tr>
                <tr>
                  <td className="py-3 px-4 font-medium text-gray-900">WebP</td>
                  <td className="py-3 px-4 text-gray-600">Web, smaller file sizes</td>
                  <td className="py-3 px-4 text-gray-600">Excellent</td>
                  <td className="py-3 px-4 text-gray-600">Lossy/Lossless</td>
                </tr>
                <tr>
                  <td className="py-3 px-4 font-medium text-gray-900">GIF</td>
                  <td className="py-3 px-4 text-gray-600">Simple animations</td>
                  <td className="py-3 px-4 text-gray-600">Limited</td>
                  <td className="py-3 px-4 text-gray-600">Lossy, Limited Colors</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>

        {/* Features Section */}
        <div className="mt-16">
          <h2 className="text-3xl font-bold text-gray-900 text-center mb-12">Smart Conversion Features</h2>
          
          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            <div className="bg-white p-6 rounded-xl shadow-sm">
              <div className="w-12 h-12 bg-gradient-to-r from-blue-500 to-purple-600 rounded-lg flex items-center justify-center mb-4">
                <FaCompress className="text-white text-xl" />
              </div>
              <h3 className="text-lg font-semibold text-gray-900 mb-2">Smart Compression</h3>
              <p className="text-gray-600">
                Optimize file size while preserving visual quality using advanced algorithms.
              </p>
            </div>
            
            <div className="bg-white p-6 rounded-xl shadow-sm">
              <div className="w-12 h-12 bg-gradient-to-r from-green-500 to-teal-600 rounded-lg flex items-center justify-center mb-4">
                <FaCompress className="text-white text-xl" />
              </div>
              <h3 className="text-lg font-semibold text-gray-900 mb-2">Quality Control</h3>
              <p className="text-gray-600">
                Adjust compression levels to balance file size and image quality.
              </p>
            </div>
            
            <div className="bg-white p-6 rounded-xl shadow-sm">
              <div className="w-12 h-12 bg-gradient-to-r from-pink-500 to-rose-600 rounded-lg flex items-center justify-center mb-4">
                <FaCompress className="text-white text-xl" />
              </div>
              <h3 className="text-lg font-semibold text-gray-900 mb-2">Batch Processing</h3>
              <p className="text-gray-600">
                Convert multiple images at once with consistent settings and quality.
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default FormatConverterPage;