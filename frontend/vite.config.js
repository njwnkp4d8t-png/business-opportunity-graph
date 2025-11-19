import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],

  server: {
    port: 5173,
    host: true, // Listen on all addresses
    strictPort: false,
    open: false,
  },

  build: {
    outDir: 'dist',
    sourcemap: true,
    minify: 'esbuild',
    target: 'es2015',
    rollupOptions: {
      output: {
        manualChunks: {
          'react-vendor': ['react', 'react-dom'],
        },
      },
    },
  },

  preview: {
    port: 4173,
    host: true,
    strictPort: false,
  },

  optimizeDeps: {
    include: ['react', 'react-dom', 'axios'],
  },
});

