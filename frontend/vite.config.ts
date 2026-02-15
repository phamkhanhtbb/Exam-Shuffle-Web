import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// https://vitejs.dev/config/
export default defineConfig({
    plugins: [react()],
    server: {
        port: 3000, // Keep same port as CRA for familiarity
        open: true,
    },
    build: {
        outDir: 'build', // Match CRA output directory for Dockerfile compatibility
        sourcemap: true,
    },
});
