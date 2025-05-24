import path from 'path';
import { defineConfig, loadEnv } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig(({ mode }) => {
    const env = loadEnv(mode, '.', '');
    return {
      plugins: [react()],
      define: {
        'process.env.API_KEY': JSON.stringify(env.GEMINI_API_KEY),
        'process.env.GEMINI_API_KEY': JSON.stringify(env.GEMINI_API_KEY)
      },
      resolve: {
        alias: {
          '@': path.resolve(__dirname, './src'),
        }
      },
      server: {
        port: 3000,
        host: true,
        proxy: {
          '/api': {
            target: 'http://localhost:8001',
            changeOrigin: true,
          },
          '/ws': {
            target: 'ws://localhost:8001',
            ws: true,
          },
        },
      },
      build: {
        outDir: 'dist',
        sourcemap: true,
        rollupOptions: {
          output: {
            manualChunks: {
              vendor: ['react', 'react-dom'],
              ui: ['@headlessui/react', '@heroicons/react', 'framer-motion'],
              charts: ['recharts'],
              flow: ['react-flow-renderer'],
            },
          },
        },
      },
    };
});
