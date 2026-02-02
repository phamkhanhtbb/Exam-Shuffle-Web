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
            const data = error.response.data as any;

            if (status === 401) {
                console.error('[API] Unauthorized - please login');
            } else if (status === 404) {
                console.error('[API] Resource not found');
            } else if (status >= 500) {
                console.error('[API] Server error:', data);
            }

            // Extract friendly error message if available
            if (data && data.detail) {
                 // Return a new Error object with the friendly message
                 // This allows UI code to simply display err.message
                 const friendlyError = new Error(data.detail);
                 (friendlyError as any).originalError = error;
                 return Promise.reject(friendlyError);
            }
        } else if (error.request) {
            console.error('[API] Network error - no response received');
            return Promise.reject(new Error("Lỗi kết nối mạng. Vui lòng kiểm tra internet của bạn."));
        }

        return Promise.reject(error);
    }
);

export default apiClient;
export { API_BASE_URL };
