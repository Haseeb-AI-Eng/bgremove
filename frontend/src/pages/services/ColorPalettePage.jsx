import React, { useState } from 'react';
import { FaUpload, FaPalette, FaEye, FaDownload } from 'react-icons/fa';
import toast from 'react-hot-toast';

const ColorPaletteGeneratorPage = () => {
  const [selectedFile, setSelectedFile] = useState(null);
  const [previewUrl, setPreviewUrl] = useState(null);
  const [palette, setPalette] = useState([]);
  const [loading, setLoading] = useState(false);

  const handleFileChange = (e) => {
    const file = e.target.files[0];
    if (file) {
      setSelectedFile(file);
      setPreviewUrl(URL.createObjectURL(file));
      setPalette([]); // Reset palette when new file is selected
    }
  };

  const handleGeneratePalette = async () => {
    if (!selectedFile) {
      toast.error('Please select an image first');
      return;
    }

    setLoading(true);

    try {
      // Simulate AI processing to extract colors
      await new Promise(resolve => setTimeout(resolve, 2000));
      
      // Generate a mock color palette (in a real app, this would come from the API)
      const mockPalette = [
        { name: 'Dominant', hex: '#4F46E5', rgb: '79, 70, 229' },
        { name: 'Secondary', hex: '#7C3AED', rgb: '124, 58, 237' },
        { name: 'Accent', hex: '#EC4899', rgb: '236, 72, 153' },
        { name: 'Light', hex: '#A78BFA', rgb: '167, 139, 250' },
        { name: 'Dark', hex: '#312E81', rgb: '49, 46, 129' }
      ];
      
      setPalette(mockPalette);
      toast.success('Color palette generated successfully!');
    } catch (error) {
      toast.error('Error generating color palette');
    } finally {
      setLoading(false);
    }
  };

  const copyToClipboard = (text) => {
    navigator.clipboard.writeText(text);
    toast.success('Color copied to clipboard!');
  };

  return (
    <div className="min-h-screen bg-gray-50 py-8">
      <div className="container mx-auto px-4">
        {/* Header */}
        <div className="text-center mb-8">
          <div className="w-16 h-16 bg-gradient-to-r from-pink-500 to-rose-600 rounded-xl flex items-center justify-center mx-auto mb-4">
            <FaPalette className="text-white text-2xl" />
          </div>
          <h1 className="text-4xl font-bold text-gray-900 mb-4">Color Palette Generator</h1>
          <p className="text-xl text-gray-600 max-w-3xl mx-auto">
            Extract and generate beautiful color palettes from your images with AI-powered analysis.
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
              onClick={handleGeneratePalette}
              disabled={loading || !selectedFile}
              className="btn btn-primary w-full"
            >
              {loading ? (
                <>
                  <span className="loading-spinner mr-2"></span>
                  Generating Palette...
                </>
              ) : (
                'Generate Color Palette'
              )}
            </button>
          </div>

          {/* Palette Preview */}
          <div className="bg-white rounded-xl shadow-sm p-6">
            <h2 className="text-2xl font-semibold text-gray-900 mb-6">Color Palette</h2>
            
            {palette.length > 0 ? (
              <div className="space-y-6">
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
                  {palette.map((color, index) => (
                    <div key={index} className="text-center">
                      <div
                        className="w-full h-20 rounded-lg mb-2 cursor-pointer"
                        style={{ backgroundColor: color.hex }}
                        onClick={() => copyToClipboard(color.hex)}
                      ></div>
                      <div className="text-sm font-medium text-gray-900">{color.name}</div>
                      <div className="text-xs text-gray-600">{color.hex}</div>
                      <div className="text-xs text-gray-500">{color.rgb}</div>
                    </div>
                  ))}
                </div>
                
                <div className="bg-gray-50 p-4 rounded-lg">
                  <h3 className="text-lg font-medium text-gray-900 mb-3">CSS Variables</h3>
                  <div className="space-y-2 text-sm">
                    {palette.map((color, index) => (
                      <div key={index} className="flex items-center justify-between p-2 bg-white rounded">
                        <code className="text-gray-700">--color-{color.name.toLowerCase()}:</code>
                        <code className="text-indigo-600 font-mono">{color.hex}</code>
                        <button
                          onClick={() => copyToClipboard(`--color-${color.name.toLowerCase()}: ${color.hex};`)}
                          className="ml-2 text-xs bg-gray-200 hover:bg-gray-300 px-2 py-1 rounded"
                        >
                          Copy
                        </button>
                      </div>
                    ))}
                  </div>
                </div>
                
                <button className="btn btn-primary w-full">
                  <FaDownload className="mr-2" /> Download Palette
                </button>
              </div>
            ) : (
              <div className="flex flex-col items-center justify-center h-64 border-2 border-dashed border-gray-300 rounded-lg">
                <FaPalette className="text-gray-400 text-4xl mb-4" />
                <p className="text-gray-500 text-center">
                  {selectedFile 
                    ? 'Click "Generate Color Palette" to extract colors from your image' 
                    : 'Upload an image to start generating a color palette'
                  }
                </p>
              </div>
            )}
          </div>
        </div>

        {/* How It Works */}
        <div className="mt-16">
          <h2 className="text-3xl font-bold text-gray-900 text-center mb-12">How It Works</h2>
          
          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            <div className="bg-white p-6 rounded-xl shadow-sm text-center">
              <div className="w-12 h-12 bg-gradient-to-r from-blue-500 to-purple-600 rounded-lg flex items-center justify-center mx-auto mb-4">
                <FaUpload className="text-white" />
              </div>
              <h3 className="text-lg font-semibold text-gray-900 mb-2">Upload Image</h3>
              <p className="text-gray-600">
                Upload any image to analyze its color composition and extract dominant colors.
              </p>
            </div>
            
            <div className="bg-white p-6 rounded-xl shadow-sm text-center">
              <div className="w-12 h-12 bg-gradient-to-r from-green-500 to-teal-600 rounded-lg flex items-center justify-center mx-auto mb-4">
                <FaPalette className="text-white" />
              </div>
              <h3 className="text-lg font-semibold text-gray-900 mb-2">AI Analysis</h3>
              <p className="text-gray-600">
                Our AI algorithms analyze the image to identify dominant and complementary colors.
              </p>
            </div>
            
            <div className="bg-white p-6 rounded-xl shadow-sm text-center">
              <div className="w-12 h-12 bg-gradient-to-r from-pink-500 to-rose-600 rounded-lg flex items-center justify-center mx-auto mb-4">
                <FaDownload className="text-white" />
              </div>
              <h3 className="text-lg font-semibold text-gray-900 mb-2">Download Palette</h3>
              <p className="text-gray-600">
                Get your color palette in multiple formats for use in design projects.
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ColorPaletteGeneratorPage;