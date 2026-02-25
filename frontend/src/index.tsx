import React from 'react';
import ReactDOM from 'react-dom/client';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { SpeedInsights } from "@vercel/speed-insights/react"
import './index.css';
import App from './App';

/**
 * APPLICATION ENTRY POINT
 * 
 * Sets up the global providers and handles low-level browser lifecycle:
 * 1. Clean up stale Service Workers (Zombie preventation).
 * 2. Initialize React Query client.
 * 3. Render the application root.
 */

if ('serviceWorker' in navigator) {
  // Prevent caching issues by unregistering any existing service workers.
  navigator.serviceWorker.getRegistrations().then(function (registrations) {
    for (let registration of registrations) {
      registration.unregister();
      console.log("Đã diệt Zombie Service Worker!");
    }
  });
  // Clear old cache storage for a fresh state.
  caches.keys().then(function (names) {
    for (let name of names) caches.delete(name);
  });
}

// Create React Query client with optimized default options.
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 1000 * 60 * 5, // Cache valid for 5 minutes
      retry: 2,                 // Retry failed requests twice
      refetchOnWindowFocus: false,
    },
    mutations: {
      retry: 1,
    },
  },
});

const root = ReactDOM.createRoot(
  document.getElementById('root') as HTMLElement
);

root.render(
  <React.StrictMode>
    {/* Global State Provider for Async Data (API status, job polling). */}
    <QueryClientProvider client={queryClient}>
      <App />
      {/* Vercel performance monitoring. */}
      <SpeedInsights />
    </QueryClientProvider>
  </React.StrictMode>
);
