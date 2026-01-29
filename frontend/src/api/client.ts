import axios, { AxiosError, AxiosInstance } from 'axios';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:5000';

// Create Axios instance with default config
const apiClient: AxiosInstance = axios.create({
    baseURL: API_BASE_URL,
    timeout: 30000,
    headers: {
        'Content-Type': 'application/json',
    },
});

// Request interceptor - add auth token, logging, etc.
apiClient.interceptors.request.use(
    (config) => {
        // Add timestamp for debugging
        console.log(`[API] ${config.method?.toUpperCase()} ${config.url}`);
        return config;
    },
    (error) => {
        return Promise.reject(error);
    }
);

// Response interceptor - handle errors globally
apiClient.interceptors.response.use(
    (response) => {
        return response;
    },
    (error: AxiosError) => {
        // Handle specific error codes
        if (error.response) {
            const status = error.response.status;

            if (status === 401) {
                console.error('[API] Unauthorized - please login');
            } else if (status === 404) {
                console.error('[API] Resource not found');
            } else if (status >= 500) {
                console.error('[API] Server error:', error.response.data);
            }
        } else if (error.request) {
            console.error('[API] Network error - no response received');
        }

        return Promise.reject(error);
    }
);

export default apiClient;
export { API_BASE_URL };
