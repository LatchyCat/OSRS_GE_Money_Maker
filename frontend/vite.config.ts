import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    host: true,
    strictPort: true, // Force port 5173, don't try alternatives
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        secure: false,
        // Add better error handling for connection issues
        onError: (err, req, res) => {
          console.warn('Backend connection failed:', err.message);
          res.writeHead(503, {
            'Content-Type': 'application/json',
          });
          res.end(JSON.stringify({
            error: 'Backend service unavailable',
            message: 'Try ports 8000-8008 or check if backend is running'
          }));
        }
      }
    }
  },
  optimizeDeps: {
    esbuildOptions: {
      target: 'es2020'
    }
  }
})
