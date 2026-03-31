/**
 * Login Screen
 * Microsoft sign-in via Expo Auth Session + backend code exchange.
 */

import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  ActivityIndicator,
  SafeAreaView,
  Alert,
  Platform,
} from 'react-native';
import MaterialCommunityIcons from '../components/MaterialCommunityIconCompat';
import * as AuthSession from 'expo-auth-session';
import * as WebBrowser from 'expo-web-browser';
import authService from '../services/authService';
import { appConfig, azureDiscovery, hasRequiredAuthConfig } from '../config/appConfig';

WebBrowser.maybeCompleteAuthSession();

const processedAuthCodes = new Set();
const LOGIN_SCREEN_BUILD_MARKER = 'LoginScreen auth patch 2026-03-27T22:25Z';

const FIXED_WEB_REDIRECT_URI =
  (process.env.EXPO_PUBLIC_WEB_REDIRECT_URI ||
    (typeof window !== 'undefined' && window.location?.origin
      ? `${window.location.origin}/auth`
      : 'http://localhost:8081/auth'));

const isIOSSafariWeb = () => {
  if (Platform.OS !== 'web' || typeof navigator === 'undefined') {
    return false;
  }

  const ua = navigator.userAgent || '';
  const isIOS = /iP(hone|ad|od)/.test(ua);
  const isSafari = /Safari/i.test(ua) && !/CriOS|FxiOS|EdgiOS/i.test(ua);
  return isIOS && isSafari;
};

const LoginScreen = ({ onLoginSuccess }) => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const redirectUri =
    Platform.OS === 'web'
      ? FIXED_WEB_REDIRECT_URI
      : AuthSession.makeRedirectUri({
          scheme: appConfig.redirectScheme,
          path: appConfig.redirectPath,
          preferLocalhost: true,
        });

  const requestConfig = {
    clientId: appConfig.azureClientId || 'missing-client-id',
    scopes: appConfig.authScopes,
    responseType: AuthSession.ResponseType.Code,
    usePKCE: true,
    redirectUri,
    extraParams: {
      prompt: 'select_account',
    },
  };

  const [request, response, promptAsync] = AuthSession.useAuthRequest(
    requestConfig,
    azureDiscovery
  );

  useEffect(() => {
    console.log('🔑 [LoginScreen] Build marker:', LOGIN_SCREEN_BUILD_MARKER);
    checkAuthStatus();
  }, []);

  useEffect(() => {
    if (!response) {
      // Safari full-page redirects may not repopulate useAuthRequest response.
      // Fall back to reading auth code directly from the callback URL.
      if (Platform.OS === 'web' && typeof window !== 'undefined') {
        try {
          const url = new URL(window.location.href);
          const codeFromUrl = url.searchParams.get('code');

          if (codeFromUrl && !processedAuthCodes.has(codeFromUrl)) {
            console.log('🔑 [LoginScreen] Fallback URL code detected, processing callback manually');
            processedAuthCodes.add(codeFromUrl);

            const savedVerifier =
              typeof sessionStorage !== 'undefined'
                ? sessionStorage.getItem('__awana_pkce_cv')
                : null;
            const codeVerifier = savedVerifier || request?.codeVerifier;

            if (savedVerifier && typeof sessionStorage !== 'undefined') {
              sessionStorage.removeItem('__awana_pkce_cv');
            }

            if (codeVerifier) {
              void finishLogin(codeFromUrl, codeVerifier);

              // Remove OAuth params from URL after processing.
              const cleanedUrl = `${window.location.origin}${window.location.pathname}`;
              window.history.replaceState({}, document.title, cleanedUrl);
            } else {
              const errorMsg = 'PKCE state lost — please try signing in again.';
              console.error('❌ [LoginScreen]', errorMsg);
              setError(errorMsg);
              setLoading(false);
            }
          }
        } catch (urlError) {
          console.error('❌ [LoginScreen] Failed to process fallback callback URL:', urlError);
        }
      }
      return;
    }

    console.log('🔑 [LoginScreen] useEffect triggered with response type:', response.type);
    console.log('   - response.params.code:', response.params?.code ? '✅ present' : '❌ MISSING');
    console.log('   - window.location.href:', window.location?.href || 'UNAVAILABLE');
    console.log('   - sessionStorage.length:', typeof sessionStorage !== 'undefined' ? sessionStorage.length : 'N/A');

    if (response.type === 'success' && response.params.code) {
      if (processedAuthCodes.has(response.params.code)) {
        console.log('🔑 [LoginScreen] Skipping duplicate auth code processing');
        console.log('   - code first 30 chars:', response.params.code.substring(0, 30));
        return;
      }

      processedAuthCodes.add(response.params.code);

      // On web the page reloads after the Azure redirect, so useAuthRequest
      // generates a fresh codeVerifier. We read the one we saved before the
      // redirect from sessionStorage so PKCE verification succeeds.
      
      console.log('🔑 [LoginScreen] === PKCE Recovery Attempt ===');
      console.log('   - Checking all sessionStorage keys:');
      if (typeof sessionStorage !== 'undefined') {
        for (let i = 0; i < sessionStorage.length; i++) {
          const key = sessionStorage.key(i);
          console.log(`     [${i}] ${key}`);
        }
      }
      
      const savedVerifier =
        Platform.OS === 'web' && typeof sessionStorage !== 'undefined'
          ? sessionStorage.getItem('__awana_pkce_cv')
          : null;

      console.log('🔑 [LoginScreen] Got auth code, checking PKCE state:');
      console.log('   - Platform:', Platform.OS);
      console.log('   - sessionStorage available:', typeof sessionStorage !== 'undefined');
      console.log('   - Saved verifier from storage:', savedVerifier ? `✅ present (${savedVerifier.length} chars)` : '❌ NOT FOUND');
      console.log('   - Saved verifier first 30 chars:', savedVerifier ? savedVerifier.substring(0, 30) : 'N/A');
      console.log('   - Request code_verifier:', request?.codeVerifier ? `present (${request.codeVerifier.length} chars)` : '❌ MISSING from request');
      console.log('   - Request verifier first 30 chars:', request?.codeVerifier ? request.codeVerifier.substring(0, 30) : 'N/A');

      const codeVerifier = savedVerifier || request?.codeVerifier;

      console.log('   - Using codeVerifier:', codeVerifier ? `✅ present (${codeVerifier.length} chars)` : '❌ MISSING!');
      console.log('   - Final verifier first 30 chars:', codeVerifier ? codeVerifier.substring(0, 30) : 'N/A');

      if (savedVerifier) {
        sessionStorage.removeItem('__awana_pkce_cv');
        console.log('   ✅ Cleared saved verifier from storage');
      }

      if (codeVerifier) {
        console.log('🔑 [LoginScreen] Proceeding with finishLogin using codeVerifier');
        void finishLogin(response.params.code, codeVerifier);
      } else {
        const errorMsg = 'PKCE state lost — please try signing in again.';
        console.error('❌ [LoginScreen]', errorMsg);
        setError(errorMsg);
        setLoading(false);
      }
      return;
    }

    if (response.type === 'error') {
      const nextError = response.error?.message || 'Microsoft sign-in failed.';
      setError(nextError);
      setLoading(false);
    }
  }, [request, response]);

  const checkAuthStatus = async () => {
    try {
      const isAuthenticated = await authService.isAuthenticated();
      if (isAuthenticated) {
        const profile = await authService.getUserProfile();
        onLoginSuccess(profile);
      }
    } catch (error) {
      console.error('Auth check error:', error);
    }
  };

  const finishLogin = async (code, codeVerifier) => {
    const exchangeRedirectUri = request?.redirectUri || redirectUri;

    try {

      // DEBUG: Log auth parameters
      console.log('🔑 [LoginScreen] finishLogin() called');
      console.log('🔑 [LoginScreen] Parameters:');
      console.log('   - code: present (' + code.length + ' chars)');
      console.log('   - codeVerifier: present (' + codeVerifier.length + ' chars)');
      console.log('   - codeVerifier first 50 chars:', codeVerifier.substring(0, 50) + '...');
      console.log('🔑 [LoginScreen] Azure endpoints:');
      console.log('   - authorizationEndpoint:', azureDiscovery.authorizationEndpoint);
      console.log('   - tokenEndpoint:', azureDiscovery.tokenEndpoint);

      // SPA platform codes must be exchanged in the browser, not server-side
      console.log('🔑 [LoginScreen] Calling AuthSession.exchangeCodeAsync...');
      console.log('🔑 [LoginScreen] Exchange details:');
      console.log('   - clientId:', appConfig.azureClientId);
      console.log('   - configured redirectUri:', redirectUri);
      console.log('   - request.redirectUri:', request?.redirectUri || 'UNAVAILABLE');
      console.log('   - exchange redirectUri:', exchangeRedirectUri);
      console.log('   - tokenEndpoint:', azureDiscovery.tokenEndpoint);
      console.log('   - request.url:', request?.url || 'UNAVAILABLE');
      console.log('🔑 [LoginScreen] Full azureDiscovery object:');
      console.log('   - authorizationEndpoint:', azureDiscovery.authorizationEndpoint);
      console.log('   - tokenEndpoint:', azureDiscovery.tokenEndpoint);
      console.log('   - discoveryDocument:', azureDiscovery.discoveryDocument);
      
      const tokenResponse = await AuthSession.exchangeCodeAsync(
        {
          clientId: appConfig.azureClientId,
          code,
          redirectUri: exchangeRedirectUri,
          extraParams: {
            code_verifier: codeVerifier,
          },
        },
        azureDiscovery
      );

      console.log('✅ [LoginScreen] Auth code exchanged successfully');
      console.log('✅ [LoginScreen] Token response keys:', Object.keys(tokenResponse));
      console.log('✅ [LoginScreen] Access token length:', tokenResponse.accessToken?.length || 0);
      console.log('✅ [LoginScreen] Expires in:', tokenResponse.expiresIn);

      const result = await authService.authenticate({
        accessToken: tokenResponse.accessToken,
      });

      const profile = result.user || (await authService.getUserProfile()) || {
        displayName: 'User',
        email: '',
      };

      console.log('✅ [LoginScreen] Login successful for user:', profile.displayName);
      onLoginSuccess(profile);
    } catch (err) {
      const errorMessage = err.message || 'Failed to login. Please try again.';
      const tokenErrorDetails = {
        message: err?.message,
        name: err?.name,
        code: err?.code,
        status: err?.status,
        description: err?.description,
        uri: err?.uri,
        params: err?.params,
        response: err?.response,
      };

      console.error('❌ [LoginScreen] Login error:', {
        message: err.message,
        name: err.name,
        stack: err.stack,
      });
      console.error('❌ [LoginScreen] Token error details:', tokenErrorDetails);
      try {
        console.error('❌ [LoginScreen] Token error JSON:', JSON.stringify(tokenErrorDetails, null, 2));
      } catch {
        console.error('❌ [LoginScreen] Token error JSON: [unserializable]');
      }
      
      // Log details about redirect URI mismatch
      if (errorMessage.includes('redirect')) {
        console.error('❌ [LoginScreen] REDIRECT URI MISMATCH DETECTED');
        console.error('   - Configured redirectUri:', redirectUri);
        console.error('   - request.redirectUri:', request?.redirectUri || 'UNAVAILABLE');
        console.error('   - Exchange redirectUri:', exchangeRedirectUri);
        console.error('   - This app redeems the code in the browser, so use Azure SPA platform for this URI');
        console.error('   - Do not register the same URI under both SPA and Web on the same app registration');
        console.error('   - Must match EXACTLY in authorization and token exchange');
      }
      
      setError(errorMessage);
      Alert.alert('Login Failed', errorMessage, [{ text: 'OK' }]);
    } finally {
      setLoading(false);
    }
  };

  const handleLogin = async () => {
    if (!hasRequiredAuthConfig()) {
      const nextError = 'Missing Azure configuration. Check your EXPO_PUBLIC_AZURE_* environment variables.';
      setError(nextError);
      Alert.alert('Configuration Error', nextError);
      return;
    }

    if (!request) {
      const nextError = 'Sign-in request is not ready yet. Try again in a moment.';
      setError(nextError);
      return;
    }

    try {
      setLoading(true);
      setError(null);

      // Save codeVerifier BEFORE the redirect so we can use it after the
      // page reloads back from Azure (it won't survive in the hook state).
      if (Platform.OS === 'web' && request?.codeVerifier && typeof sessionStorage !== 'undefined') {
        console.log('🔑 [LoginScreen] Saving PKCE codeVerifier before redirect:');
        console.log('   - codeVerifier length:', request.codeVerifier.length);
        console.log('   - First 50 chars:', request.codeVerifier.substring(0, 50) + '...');
        sessionStorage.setItem('__awana_pkce_cv', request.codeVerifier);
        console.log('   ✅ Saved to sessionStorage.__awana_pkce_cv');
        console.log('   - Verify retrieval:', sessionStorage.getItem('__awana_pkce_cv') ? '✅ Can retrieve' : '❌ Cannot retrieve');
      } else {
        console.log('🔑 [LoginScreen] Skipping PKCE save:');
        console.log('   - Platform.OS:', Platform.OS);
        console.log('   - request?.codeVerifier:', request?.codeVerifier ? 'present' : 'MISSING');
        console.log('   - sessionStorage available:', typeof sessionStorage !== 'undefined');
      }

      // iOS Safari often blocks popup-based OAuth; use full-page redirect instead.
      if (isIOSSafariWeb() && request?.url && typeof window !== 'undefined') {
        console.log('🔑 [LoginScreen] iOS Safari detected, using full-page redirect for auth');
        window.location.assign(request.url);
        return;
      }

      const result = await promptAsync(
        Platform.OS === 'web'
          ? { windowFeatures: 'noopener,noreferrer,width=500,height=700' }
          : undefined
      );
      if (result.type !== 'success') {
        setLoading(false);
      }
    } catch (err) {
      console.error('❌ [LoginScreen] handleLogin error:', err);
      setLoading(false);
      const nextError = err?.message || 'Unable to start Microsoft sign-in.';
      setError(nextError);
      Alert.alert('Login Failed', nextError, [{ text: 'OK' }]);
    }
  };

  return (
    <SafeAreaView style={styles.container}>
      <View style={styles.content}>
        {/* Logo Section */}
        <View style={styles.logoSection}>
          <MaterialCommunityIcons
            name="microsoft"
            size={80}
            color="#0078D4"
            style={styles.logo}
          />
          <Text style={styles.title}>Awana Points Logger</Text>
          <Text style={styles.subtitle}>Microsoft 365 Integration</Text>
          <Text style={styles.redirectText}>{redirectUri}</Text>
        </View>

        {/* Info Section */}
        <View style={styles.infoSection}>
          <View style={styles.infoItem}>
            <MaterialCommunityIcons
              name="shield-check"
              size={24}
              color="#107C10"
            />
            <Text style={styles.infoText}>Secure MS365 Authentication</Text>
          </View>

          <View style={styles.infoItem}>
            <MaterialCommunityIcons
              name="cloud-sync"
              size={24}
              color="#50E6FF"
            />
            <Text style={styles.infoText}>SharePoint Integration</Text>
          </View>

          <View style={styles.infoItem}>
            <MaterialCommunityIcons
              name="lock"
              size={24}
              color="#E7630B"
            />
            <Text style={styles.infoText}>Your Data is Protected</Text>
          </View>
        </View>

        {/* Error Message */}
        {error && (
          <View style={styles.errorBox}>
            <MaterialCommunityIcons
              name="alert-circle"
              size={20}
              color="#E81828"
            />
            <Text style={styles.errorText}>{error}</Text>
          </View>
        )}

        {/* Login Button */}
        <TouchableOpacity
          style={[
            styles.loginButton,
            loading && styles.loginButtonDisabled,
          ]}
          onPress={handleLogin}
          disabled={loading || !request}
        >
          {loading ? (
            <ActivityIndicator
              size="large"
              color="white"
              style={styles.loader}
            />
          ) : (
            <>
              <MaterialCommunityIcons
                name="microsoft"
                size={24}
                color="white"
              />
              <Text style={styles.loginButtonText}>
                Sign in with Microsoft 365
              </Text>
            </>
          )}
        </TouchableOpacity>

        {/* Footer */}
        <View style={styles.footer}>
          <Text style={styles.footerText}>
            By signing in, you agree to our Terms of Service
          </Text>
          <Text style={styles.footerVersion}>v1.0.0 - Production</Text>
        </View>
      </View>
    </SafeAreaView>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#F5F5F5',
  },
  content: {
    flex: 1,
    padding: 24,
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  logoSection: {
    alignItems: 'center',
    marginTop: 40,
  },
  logo: {
    marginBottom: 16,
  },
  title: {
    fontSize: 28,
    fontWeight: 'bold',
    color: '#1F1F1F',
    marginBottom: 8,
    textAlign: 'center',
  },
  subtitle: {
    fontSize: 16,
    color: '#666',
    textAlign: 'center',
  },
  redirectText: {
    marginTop: 12,
    fontSize: 12,
    color: '#888',
    textAlign: 'center',
  },
  infoSection: {
    width: '100%',
    backgroundColor: 'white',
    borderRadius: 12,
    padding: 16,
    marginVertical: 24,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 3,
  },
  infoItem: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 16,
  },
  infoText: {
    marginLeft: 12,
    fontSize: 14,
    color: '#333',
    flex: 1,
  },
  errorBox: {
    width: '100%',
    backgroundColor: '#FED7D7',
    borderColor: '#E81828',
    borderWidth: 1,
    borderRadius: 8,
    padding: 12,
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 16,
  },
  errorText: {
    marginLeft: 12,
    fontSize: 14,
    color: '#E81828',
    flex: 1,
  },
  loginButton: {
    width: '100%',
    backgroundColor: '#0078D4',
    paddingVertical: 14,
    paddingHorizontal: 16,
    borderRadius: 8,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: 16,
    shadowColor: '#0078D4',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.3,
    shadowRadius: 8,
    elevation: 5,
  },
  loginButtonDisabled: {
    opacity: 0.7,
  },
  loginButtonText: {
    color: 'white',
    fontSize: 16,
    fontWeight: '600',
    marginLeft: 8,
  },
  loader: {
    marginRight: 8,
  },
  footer: {
    alignItems: 'center',
    marginBottom: 24,
  },
  footerText: {
    fontSize: 12,
    color: '#666',
    textAlign: 'center',
    marginBottom: 4,
  },
  footerVersion: {
    fontSize: 11,
    color: '#999',
  },
});

export default LoginScreen;
