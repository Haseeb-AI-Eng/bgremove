import React, { useState, useEffect, useRef } from 'react';
import { useSearchParams } from 'react-router-dom';
import { useLanguage } from '../contexts/LanguageContext';
import { FaUser, FaKey, FaChartLine, FaCrown, FaHistory, FaCreditCard } from 'react-icons/fa';
import { useAuth } from '../contexts/AuthContext';
import { useApiKey } from '../contexts/ApiKeyContext';
import toast from 'react-hot-toast';

const DashboardPage = () => {
  const { user, isAuthenticated } = useAuth();
  const { apiKeys, createApiKey, fetchApiKeys, revokeApiKey, loading } = useApiKey();
  const [searchParams, setSearchParams] = useSearchParams();
  const [activeTab, setActiveTab] = useState(() => {
    const tabFromUrl = searchParams.get('tab');
    return tabFromUrl || 'profile';
  });
  const [apiKeyName, setApiKeyName] = useState('Default API Key');
  const [showApiKey, setShowApiKey] = useState(false);
  const [generatedApiKey, setGeneratedApiKey] = useState('');
  const { t } = useLanguage();

  useEffect(() => {
    if (isAuthenticated) {
      fetchApiKeys();
    }
  }, [isAuthenticated]); // Only run when authentication status changes

  const handleCreateApiKey = async () => {
    const result = await createApiKey(apiKeyName);
    if (result.success) {
      setGeneratedApiKey(result.apiKey);
      setShowApiKey(true);
      toast.success('API key created successfully!');
      // Reset the name field
      setApiKeyName('Default API Key');
    } else {
      toast.error(result.error);
    }
  };

  const handleRevokeApiKey = async (apiKeyId) => {
    if (window.confirm('Are you sure you want to revoke this API key?')) {
      const result = await revokeApiKey(apiKeyId);
      if (result.success) {
        toast.success('API key revoked successfully!');
      } else {
        toast.error(result.error);
      }
    }
  };

  if (!isAuthenticated) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <h2 className="text-2xl font-bold text-gray-900 mb-4">Please log in</h2>
          <p className="text-gray-600">You need to be logged in to access the dashboard.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 py-8">
      <div className="container mx-auto px-4">
        <div className="max-w-6xl mx-auto">
          {/* Header */}
          <div className="mb-8">
            <h1 className="text-3xl font-bold text-gray-900 mb-2">
              AI Background Removal Dashboard
            </h1>
            <p className="text-gray-600">Welcome back, {user?.first_name || user?.email?.split('@')[0]}! Manage your account and API keys</p>
          </div>

          {/* User Info Card */}
          <div className="bg-white rounded-xl shadow-sm p-6 mb-8">
            <div className="flex items-center space-x-4">
              <div className="w-16 h-16 bg-gradient-to-r from-indigo-500 to-purple-600 rounded-full flex items-center justify-center">
                <FaUser className="text-white text-2xl" />
              </div>
              <div>
                <h2 className="text-xl font-semibold text-gray-900">
                  {user?.first_name} {user?.last_name}
                </h2>
                <p className="text-gray-600">{user?.email}</p>
                {user?.is_pro && (
                  <div className="flex items-center mt-1">
                    <FaCrown className="text-yellow-500 mr-1" />
                    <span className="text-sm text-yellow-600 font-medium">Pro Member</span>
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* Navigation Tabs */}
          <div className="flex border-b border-gray-200 mb-8">
            <button
              className={`px-4 py-2 font-medium text-sm ${
                activeTab === 'profile'
                  ? 'text-indigo-600 border-b-2 border-indigo-600'
                  : 'text-gray-500 hover:text-gray-700'
              }`}
              onClick={() => {
                setActiveTab('profile');
                setSearchParams({ tab: 'profile' });
              }}
            >
              <div className="flex items-center">
                <FaUser className="mr-2" />
                Profile
              </div>
            </button>
            <button
              className={`px-4 py-2 font-medium text-sm ${
                activeTab === 'api-keys'
                  ? 'text-indigo-600 border-b-2 border-indigo-600'
                  : 'text-gray-500 hover:text-gray-700'
              }`}
              onClick={() => {
                setActiveTab('api-keys');
                setSearchParams({ tab: 'api-keys' });
                setShowApiKey(false);
                setGeneratedApiKey('');
              }}
            >
              <div className="flex items-center">
                <FaKey className="mr-2" />
                API Keys
              </div>
            </button>
            <button
              className={`px-4 py-2 font-medium text-sm ${
                activeTab === 'usage'
                  ? 'text-indigo-600 border-b-2 border-indigo-600'
                  : 'text-gray-500 hover:text-gray-700'
              }`}
              onClick={() => {
                setActiveTab('usage');
                setSearchParams({ tab: 'usage' });
              }}
            >
              <div className="flex items-center">
                <FaChartLine className="mr-2" />
                Usage
              </div>
            </button>
          </div>

          {/* Tab Content */}
          {activeTab === 'profile' && (
            <ProfileEditSection user={user} />
          )}

          {activeTab === 'api-keys' && (
            <div className="bg-white rounded-xl shadow-sm p-6">
              <div className="flex justify-between items-center mb-6">
                <h3 className="text-lg font-semibold text-gray-900">API Keys</h3>
                <div className="flex space-x-2">
                  <input
                    type="text"
                    value={apiKeyName}
                    onChange={(e) => setApiKeyName(e.target.value)}
                    placeholder="API Key Name"
                    className="input-field w-48"
                  />
                  <button
                    onClick={handleCreateApiKey}
                    disabled={loading}
                    className="btn btn-primary flex items-center"
                  >
                    {loading ? (
                      <>
                        <span className="loading-spinner mr-2"></span>
                        Creating...
                      </>
                    ) : (
                      'Create API Key'
                    )}
                  </button>
                </div>
              </div>

              {/* Show newly generated API key */}
              {showApiKey && generatedApiKey && (
                <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4 mb-6">
                  <div className="flex justify-between items-start">
                    <div>
                      <h4 className="font-medium text-yellow-800 mb-2">Your new API key:</h4>
                      <code className="bg-yellow-100 text-yellow-900 p-2 rounded break-all font-mono text-sm">
                        {generatedApiKey}
                      </code>
                      <p className="text-yellow-700 text-sm mt-2">
                        <strong>Important:</strong> This key will only be shown once. Please save it securely.
                      </p>
                    </div>
                    <button
                      onClick={() => {
                        navigator.clipboard.writeText(generatedApiKey);
                        toast.success('API key copied to clipboard!');
                      }}
                      className="ml-4 px-3 py-1 bg-yellow-600 text-white rounded text-sm hover:bg-yellow-700"
                    >
                      Copy
                    </button>
                  </div>
                </div>
              )}

              {/* API Keys List */}
              <div className="overflow-x-auto">
                <table className="min-w-full divide-y divide-gray-200">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Name
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Key
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Created
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Status
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Actions
                      </th>
                    </tr>
                  </thead>
                  <tbody className="bg-white divide-y divide-gray-200">
                    {apiKeys.map((key) => (
                      <tr key={key.id}>
                        <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                          {key.name}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                          <code>...{key.key_prefix}</code>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                          {new Date(key.created_at).toLocaleDateString()}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap">
                          <span
                            className={`px-2 inline-flex text-xs leading-5 font-semibold rounded-full ${
                              key.status === 'active'
                                ? 'bg-green-100 text-green-800'
                                : 'bg-red-100 text-red-800'
                            }`}
                          >
                            {key.status}
                          </span>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                          <button
                            onClick={() => handleRevokeApiKey(key.id)}
                            className="text-red-600 hover:text-red-900"
                            disabled={loading}
                          >
                            {loading ? 'Revoking...' : 'Revoke'}
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              {apiKeys.length === 0 && (
                <div className="text-center py-8 text-gray-500">
                  <p>No API keys created yet.</p>
                  <p className="text-sm mt-2">Create your first API key to start using our services programmatically.</p>
                </div>
              )}
            </div>
          )}

          {activeTab === 'usage' && (
            <div className="bg-white rounded-xl shadow-sm p-6">
              <h3 className="text-lg font-semibold text-gray-900 mb-4">Usage Statistics</h3>
              
              <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
                <div className="bg-gray-50 p-4 rounded-lg">
                  <div className="text-2xl font-bold text-indigo-600">1,248</div>
                  <div className="text-gray-600">API Calls This Month</div>
                </div>
                <div className="bg-gray-50 p-4 rounded-lg">
                  <div className="text-2xl font-bold text-green-600">42</div>
                  <div className="text-gray-600">Images Processed</div>
                </div>
                <div className="bg-gray-50 p-4 rounded-lg">
                  <div className="text-2xl font-bold text-purple-600">12</div>
                  <div className="text-gray-600">Active API Keys</div>
                </div>
              </div>

              <div className="border-t pt-6">
                <h4 className="text-md font-semibold text-gray-900 mb-4">Recent Activity</h4>
                <div className="space-y-3">
                  <div className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                    <div className="flex items-center">
                      <FaHistory className="text-gray-400 mr-3" />
                      <span>Image processed: background removal</span>
                    </div>
                    <span className="text-sm text-gray-500">2 hours ago</span>
                  </div>
                  <div className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                    <div className="flex items-center">
                      <FaHistory className="text-gray-400 mr-3" />
                      <span>API key created: Production</span>
                    </div>
                    <span className="text-sm text-gray-500">1 day ago</span>
                  </div>
                  <div className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                    <div className="flex items-center">
                      <FaHistory className="text-gray-400 mr-3" />
                      <span>CV generated: Professional Resume</span>
                    </div>
                    <span className="text-sm text-gray-500">3 days ago</span>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

// Profile Edit Section Component
const ProfileEditSection = ({ user }) => {
  const { updateProfile, uploadProfileImage } = useAuth();
  const [formData, setFormData] = useState({
    first_name: user?.first_name || '',
    last_name: user?.last_name || '',
    bio: user?.bio || ''
  });
  const [isEditing, setIsEditing] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [profileImage, setProfileImage] = useState(null);
  const [previewImage, setPreviewImage] = useState(user?.profile_image || null);
  const fileInputRef = useRef(null);

  useEffect(() => {
    setFormData({
      first_name: user?.first_name || '',
      last_name: user?.last_name || '',
      bio: user?.bio || ''
    });
    setPreviewImage(user?.profile_image || null);
  }, [user]);

  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: value
    }));
  };

  const handleImageChange = (e) => {
    const file = e.target.files[0];
    if (file) {
      setProfileImage(file);
      // Create a preview URL for the selected image
      const reader = new FileReader();
      reader.onloadend = () => {
        setPreviewImage(reader.result);
      };
      reader.readAsDataURL(file);
    }
  };

  const handleUploadImage = async () => {
    if (!profileImage) return;

    setIsUploading(true);
    try {
      const result = await uploadProfileImage(profileImage);
      if (result.success) {
        toast.success('Profile image updated successfully!');
      } else {
        toast.error(result.error);
      }
    } catch (error) {
      toast.error('Failed to upload profile image');
    } finally {
      setIsUploading(false);
    }
  };

  const handleUpdateProfile = async () => {
    try {
      const result = await updateProfile(formData);
      if (result.success) {
        toast.success('Profile updated successfully!');
        setIsEditing(false);
      } else {
        toast.error(result.error);
      }
    } catch (error) {
      toast.error('Failed to update profile');
    }
  };

  return (
    <div className="bg-white rounded-xl shadow-sm p-6">
      <h3 className="text-lg font-semibold text-gray-900 mb-4">Profile Information</h3>

      {/* Profile Image Section */}
      <div className="flex items-start mb-6">
        <div className="relative">
          <img
            src={previewImage || '/jju.png'} // Use default image if no profile image
            alt="Profile"
            className="w-24 h-24 rounded-full object-cover border-4 border-gray-200"
          />
          <button
            onClick={() => fileInputRef.current?.click()}
            className="absolute -bottom-2 -right-2 bg-indigo-600 text-white p-2 rounded-full hover:bg-indigo-700 transition-colors"
            title="Change profile picture"
          >
            <FaUser className="text-sm" />
          </button>
          <input
            type="file"
            ref={fileInputRef}
            onChange={handleImageChange}
            accept="image/*"
            className="hidden"
          />
        </div>
        <div className="ml-6 flex-1">
          <div className="flex items-center space-x-4">
            <button
              onClick={handleUploadImage}
              disabled={!profileImage || isUploading}
              className={`px-4 py-2 rounded-lg text-sm font-medium ${
                !profileImage || isUploading
                  ? 'bg-gray-200 text-gray-500 cursor-not-allowed'
                  : 'bg-indigo-600 text-white hover:bg-indigo-700'
              }`}
            >
              {isUploading ? 'Uploading...' : 'Upload Image'}
            </button>
            <button
              onClick={() => {
                fileInputRef.current?.click();
                setProfileImage(null);
                setPreviewImage(user?.profile_image || null);
              }}
              className="px-4 py-2 border border-gray-300 text-gray-700 rounded-lg text-sm font-medium hover:bg-gray-50"
            >
              Choose File
            </button>
          </div>
          <p className="text-sm text-gray-500 mt-2">JPG, PNG, GIF up to 5MB</p>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">First Name</label>
          <input
            type="text"
            name="first_name"
            value={formData.first_name}
            onChange={handleInputChange}
            className="input-field"
            disabled={!isEditing}
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Last Name</label>
          <input
            type="text"
            name="last_name"
            value={formData.last_name}
            onChange={handleInputChange}
            className="input-field"
            disabled={!isEditing}
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Email</label>
          <input
            type="email"
            value={user?.email || ''}
            className="input-field"
            disabled
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Account Type</label>
          <div className="input-field">
            {user?.is_pro ? 'Pro Member' : 'Free Member'}
          </div>
        </div>
      </div>

      <div className="mt-6">
        <label className="block text-sm font-medium text-gray-700 mb-1">Bio</label>
        <textarea
          name="bio"
          value={formData.bio}
          onChange={handleInputChange}
          rows={4}
          className="input-field"
          disabled={!isEditing}
          placeholder="Tell us about yourself..."
        />
      </div>

      <div className="mt-6 flex justify-between">
        {!isEditing ? (
          <button
            onClick={() => setIsEditing(true)}
            className="btn btn-primary"
          >
            Edit Profile
          </button>
        ) : (
          <div className="flex space-x-3">
            <button
              onClick={handleUpdateProfile}
              className="btn btn-primary"
            >
              Save Changes
            </button>
            <button
              onClick={() => {
                setIsEditing(false);
                setFormData({
                  first_name: user?.first_name || '',
                  last_name: user?.last_name || '',
                  bio: user?.bio || ''
                });
                setProfileImage(null);
                setPreviewImage(user?.profile_image || null);
              }}
              className="px-4 py-2 border border-gray-300 text-gray-700 rounded-lg text-sm font-medium hover:bg-gray-50"
            >
              Cancel
            </button>
          </div>
        )}
      </div>
    </div>
  );
};

export default DashboardPage;