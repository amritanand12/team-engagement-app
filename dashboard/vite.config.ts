import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],

  server: {
    port: 5173,
    host: true,
    allowedHosts: ['f3a9-117-194-204-52.ngrok-free.app'],
  },

  preview: {
    port: 5173,
    host: true,
    allowedHosts: ['f3a9-117-194-204-52.ngrok-free.app'],
  },
});