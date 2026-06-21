import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

const proxyTarget = process.env.VITE_API_PROXY_TARGET || 'http://localhost:8888'

export default defineConfig({
  plugins: [react()],
  build: {
    chunkSizeWarningLimit: 1200,
    rollupOptions: {
      output: {
        manualChunks: {
          react: ['react', 'react-dom'],
          echarts: ['echarts', 'echarts-for-react'],
          leaflet: ['leaflet', 'react-leaflet'],
          dayjs: ['dayjs'],
        },
      },
    },
  },
  server: {
    host: '0.0.0.0',
    port: 5188,
    proxy: {
      '/api': {
        target: proxyTarget,
        changeOrigin: true,
      },
    },
  },
})
