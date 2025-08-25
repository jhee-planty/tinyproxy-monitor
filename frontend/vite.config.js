import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,  // Vite 기본 포트로 변경
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',  // IPv4 명시적 사용
        changeOrigin: true
      },
      '/ws': {
        target: 'ws://127.0.0.1:8000',  // IPv4 명시적 사용
        ws: true
      }
    }
  }
})