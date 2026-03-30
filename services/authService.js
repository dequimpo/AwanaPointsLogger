/**
 * Authentication Service
 * Handles backend-issued session tokens after Microsoft sign-in.
 */

import * as SecureStore from 'expo-secure-store';
import { Platform } from 'react-native';
import { appConfig } from '../config/appConfig';

const API_BASE_URL = appConfig.apiBaseUrl;

// Token storage keys
const TOKEN_KEY = 'access_token';
const USER_KEY = 'user_profile';
const TOKEN_EXPIRY_KEY = 'token_expires_at';

// Platform-aware storage wrapper
const StorageAdapter = {
  // Check if we're on web platform
  isWeb: () => {
    try {
      return Platform.OS === 'web' || typeof window !== 'undefined';
    } catch {
      return false;
    }
  },

  // Get item from appropriate storage
  async getItem(key) {
    try {
      if (this.isWeb() && typeof sessionStorage !== 'undefined') {
        console.log(`📦 [Storage] Getting "${key}" from sessionStorage (web)`);
        return sessionStorage.getItem(key);
      }
      console.log(`📦 [Storage] Getting "${key}" from SecureStore (native)`);
      return await SecureStore.getItemAsync(key);
    } catch (error) {
      console.error(`❌ [Storage] Error getting "${key}":`, error);
      return null;
    }
  },

  // Set item in appropriate storage
  async setItem(key, value) {
    try {
      if (this.isWeb() && typeof sessionStorage !== 'undefined') {
        console.log(`📦 [Storage] Setting "${key}" in sessionStorage (web)`);
        sessionStorage.setItem(key, value);
        return;
      }
      console.log(`📦 [Storage] Setting "${key}" in SecureStore (native)`);
      await SecureStore.setItemAsync(key, value);
    } catch (error) {
      console.error(`❌ [Storage] Error setting "${key}":`, error);
      throw error;
    }
  },

  // Remove item from appropriate storage
  async removeItem(key) {
    try {
      if (this.isWeb() && typeof sessionStorage !== 'undefined') {
        console.log(`📦 [Storage] Removing "${key}" from sessionStorage (web)`);
        sessionStorage.removeItem(key);
        return;
      }
      console.log(`📦 [Storage] Removing "${key}" from SecureStore (native)`);
      await SecureStore.deleteItemAsync(key);
    } catch (error) {
      console.error(`❌ [Storage] Error removing "${key}":`, error);
      throw error;
    }
  },
};

class AuthService {
  constructor() {
    this.accessToken = null;
    this.userProfile = null;
    this.tokenExpiresAt = null;
    console.log(`🔐 [AuthService] Initialized on platform: ${StorageAdapter.isWeb() ? 'WEB' : 'NATIVE'}`);
  }

  /**
   * Get a valid access token, refreshing if necessary
   */
  async getAccessToken() {
    try {
      if (this.accessToken && this.isTokenValid()) {
        return this.accessToken;
      }

      const storedToken = await StorageAdapter.getItem(TOKEN_KEY);
      const expiryTime = await this.getTokenExpiryFromStorage();

      if (storedToken && this.isTokenValid(expiryTime)) {
        this.accessToken = storedToken;
        this.tokenExpiresAt = expiryTime;
        return storedToken;
      }

      await this.logout();
      throw new Error('Session expired. Please sign in again.');
    } catch (error) {
      console.error('Failed to get access token:', error);
      throw error;
    }
  }

  /**
   * Exchange the Azure authorization code on the backend for a session token.
   */
  async authenticate({ accessToken }) {
    try {
      // DEBUG: Log token details
      console.log('🔐 [AuthService] Exchanging access token for session token');
      console.log('🔐 [AuthService] Token length:', accessToken?.length || 0);
      console.log('🔐 [AuthService] Token first 50 chars:', accessToken?.substring(0, 50) + '...');
      console.log('🔐 [AuthService] Token parts (should be 3):', accessToken?.split('.').length);
      console.log('🔐 [AuthService] Backend URL:', `${API_BASE_URL}/auth/token`);

      const response = await fetch(`${API_BASE_URL}/auth/token`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          access_token: accessToken,
        }),
      });

      console.log('🔐 [AuthService] Response status:', response.status);
      console.log('🔐 [AuthService] Response headers:', {
        contentType: response.headers.get('content-type'),
        corsOrigin: response.headers.get('access-control-allow-origin'),
      });

      const data = await response.json();

      if (!response.ok) {
        console.error('❌ [AuthService] Backend auth failed:');
        console.error('   Status:', response.status);
        console.error('   Detail:', data.detail);
        console.error('   Full response:', data);
        throw new Error(data.detail || 'Authentication failed');
      }

      console.log('✅ [AuthService] Token exchange successful');
      console.log('✅ [AuthService] User:', data.user);

      await this.storeTokens(data.access_token, data.expires_in);

      if (data.user) {
        await this.storeUserProfile(data.user);
      }

      return {
        accessToken: data.access_token,
        expiresIn: data.expires_in,
        user: data.user || null,
      };
    } catch (error) {
      console.error('❌ [AuthService] Authentication error:', error);
      throw error;
    }
  }

  /**
   * Store tokens securely
   */
  async storeTokens(accessToken, expiresIn) {
    try {
      await StorageAdapter.setItem(TOKEN_KEY, accessToken);

      this.accessToken = accessToken;
      this.tokenExpiresAt = Date.now() + (expiresIn * 1000);

      await StorageAdapter.setItem(
        TOKEN_EXPIRY_KEY,
        this.tokenExpiresAt.toString()
      );
      console.log('✅ [AuthService] Tokens stored successfully');
    } catch (error) {
      console.error('Failed to store tokens:', error);
      throw error;
    }
  }

  /**
   * Check if token is still valid
   */
  isTokenValid(expiryTime = this.tokenExpiresAt) {
    if (!expiryTime) return false;
    return Date.now() < (expiryTime - 5 * 60 * 1000);
  }

  /**
   * Get token expiry time from storage
   */
  async getTokenExpiryFromStorage() {
    try {
      const expiry = await StorageAdapter.getItem(TOKEN_EXPIRY_KEY);
      return expiry ? parseInt(expiry, 10) : null;
    } catch (error) {
      return null;
    }
  }

  /**
   * Store user profile
   */
  async storeUserProfile(profile) {
    try {
      await StorageAdapter.setItem(USER_KEY, JSON.stringify(profile));
      this.userProfile = profile;
      console.log('✅ [AuthService] User profile stored');
    } catch (error) {
      console.error('Failed to store user profile:', error);
    }
  }

  /**
   * Get stored user profile
   */
  async getUserProfile() {
    try {
      if (this.userProfile) return this.userProfile;

      const profile = await StorageAdapter.getItem(USER_KEY);
      if (profile) {
        this.userProfile = JSON.parse(profile);
        return this.userProfile;
      }

      return null;
    } catch (error) {
      console.error('Failed to get user profile:', error);
      return null;
    }
  }

  /**
   * Check if user is authenticated
   */
  async isAuthenticated() {
    try {
      const token = await StorageAdapter.getItem(TOKEN_KEY);
      if (!token) return false;

      const expiryTime = await this.getTokenExpiryFromStorage();
      return this.isTokenValid(expiryTime);
    } catch (error) {
      console.error('Auth check error:', error);
      return false;
    }
  }

  /**
   * Logout user - clear all stored tokens and profile
   */
  async logout() {
    try {
      await StorageAdapter.removeItem(TOKEN_KEY);
      await StorageAdapter.removeItem(USER_KEY);
      await StorageAdapter.removeItem(TOKEN_EXPIRY_KEY);

      this.accessToken = null;
      this.userProfile = null;
      this.tokenExpiresAt = null;
      console.log('✅ [AuthService] Logged out successfully');
    } catch (error) {
      console.error('Logout error:', error);
    }
  }

  /**
   * Initialize auth service - restore stored tokens on app launch
   */
  async initialize() {
    try {
      console.log('🔐 [AuthService] Initializing...');
      const token = await StorageAdapter.getItem(TOKEN_KEY);
      const expiryTime = await this.getTokenExpiryFromStorage();
      const userProfile = await this.getUserProfile();

      if (token && this.isTokenValid(expiryTime)) {
        this.accessToken = token;
        this.tokenExpiresAt = expiryTime;
        this.userProfile = userProfile;
        console.log('✅ [AuthService] Restored existing session');
        return true;
      }

      if (token) {
        console.log('⚠️  [AuthService] Token expired, clearing');
        await this.logout();
      }

      console.log('ℹ️  [AuthService] No valid session found');
      return false;
    } catch (error) {
      console.error('Auth initialization error:', error);
      return false;
    }
  }
}

export default new AuthService();
