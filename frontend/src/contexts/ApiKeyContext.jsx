import React, { createContext, useContext, useState } from 'react';
import axios from 'axios';

const ApiKeyContext = createContext();

export const useApiKey = () => {
  const context = useContext(ApiKeyContext);
  if (!context) {
    throw new Error('useApiKey must be used within an ApiKeyProvider');
  }
  return context;
};

export const ApiKeyProvider = ({ children }) => {
  const [apiKeys, setApiKeys] = useState([]);
  const [loading, setLoading] = useState(false);

  const createApiKey = async (name = 'Default API Key') => {
    try {
      setLoading(true);
      const response = await axios.post('/api/keys', { name });
      const newKey = response.data.api_key; // This should be the unhashed key

      // Fetch all keys again to update the list
      await fetchApiKeys();

      return { success: true, apiKey: newKey };
    } catch (error) {
      return {
        success: false,
        error: error.response?.data?.detail || 'Failed to create API key'
      };
    } finally {
      setLoading(false);
    }
  };

  const fetchApiKeys = async () => {
    try {
      setLoading(true);
      const response = await axios.get('/api/keys');
      setApiKeys(response.data.api_keys || []);
      return { success: true, apiKeys: response.data.api_keys || [] };
    } catch (error) {
      return {
        success: false,
        error: error.response?.data?.detail || 'Failed to fetch API keys'
      };
    } finally {
      setLoading(false);
    }
  };

  const revokeApiKey = async (apiKeyId) => {
    try {
      setLoading(true);
      await axios.post(`/api/keys/revoke/${apiKeyId}`);
      await fetchApiKeys(); // Refresh the list after revoking
      return { success: true };
    } catch (error) {
      return {
        success: false,
        error: error.response?.data?.detail || 'Failed to revoke API key'
      };
    } finally {
      setLoading(false);
    }
  };

  const value = {
    apiKeys,
    createApiKey,
    fetchApiKeys,
    revokeApiKey,
    loading
  };

  return (
    <ApiKeyContext.Provider value={value}>
      {children}
    </ApiKeyContext.Provider>
  );
};