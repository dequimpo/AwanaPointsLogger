/**
 * API Client with Authentication
 * Handles API requests with backend session tokens.
 */

import authService from './authService';
import { appConfig } from '../config/appConfig';

const API_BASE_URL = appConfig.apiBaseUrl;

class APIClient {
  constructor() {
    this.baseURL = API_BASE_URL;
  }

  /**
   * Get headers with authorization token
   */
  async getAuthHeaders() {
    try {
      const token = await authService.getAccessToken();
      return {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`,
      };
    } catch (error) {
      console.error('Failed to get auth headers:', error);
      throw error;
    }
  }

  /**
   * Make a GET request
   */
  async get(endpoint, options = {}) {
    try {
      const headers = await this.getAuthHeaders();
      const url = `${this.baseURL}${endpoint}`;

      const response = await fetch(url, {
        method: 'GET',
        headers: { ...headers, ...options.headers },
        ...options,
      });

      return await this.handleResponse(response);
    } catch (error) {
      console.error(`GET ${endpoint} failed:`, error);
      throw error;
    }
  }

  /**
   * Make a POST request
   */
  async post(endpoint, data, options = {}) {
    try {
      const headers = await this.getAuthHeaders();
      const url = `${this.baseURL}${endpoint}`;

      const response = await fetch(url, {
        method: 'POST',
        headers: { ...headers, ...options.headers },
        body: JSON.stringify(data),
        ...options,
      });

      return await this.handleResponse(response);
    } catch (error) {
      console.error(`POST ${endpoint} failed:`, error);
      throw error;
    }
  }

  /**
   * Make a PATCH request
   */
  async patch(endpoint, data, options = {}) {
    try {
      const headers = await this.getAuthHeaders();
      const url = `${this.baseURL}${endpoint}`;

      const response = await fetch(url, {
        method: 'PATCH',
        headers: { ...headers, ...options.headers },
        body: JSON.stringify(data),
        ...options,
      });

      return await this.handleResponse(response);
    } catch (error) {
      console.error(`PATCH ${endpoint} failed:`, error);
      throw error;
    }
  }

  /**
   * Make a PUT request
   */
  async put(endpoint, data, options = {}) {
    try {
      const headers = await this.getAuthHeaders();
      const url = `${this.baseURL}${endpoint}`;

      const response = await fetch(url, {
        method: 'PUT',
        headers: { ...headers, ...options.headers },
        body: JSON.stringify(data),
        ...options,
      });

      return await this.handleResponse(response);
    } catch (error) {
      console.error(`PUT ${endpoint} failed:`, error);
      throw error;
    }
  }

  /**
   * Handle API response
   */
  async handleResponse(response) {
    try {
      const data = await response.json();

      if (!response.ok) {
        if (response.status === 401) {
          await authService.logout();
          throw new Error('Authentication failed - please login again');
        }

        throw new Error(data.detail || `HTTP ${response.status}: ${data.message || 'Unknown error'}`);
      }

      return data;
    } catch (error) {
      console.error('Response handling error:', error);
      throw error;
    }
  }

  /**
   * Check backend health
   */
  async checkHealth() {
    try {
      const response = await fetch(`${this.baseURL}/health`);
      return response.ok;
    } catch (error) {
      console.error('Health check failed:', error);
      return false;
    }
  }
}

export default new APIClient();
