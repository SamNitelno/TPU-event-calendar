import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig(({ mode }) => {
  // Только сервер Vite читает адрес API; корневой .env не передаётся в браузер.
  const env = loadEnv(mode, process.cwd(), 'API_PROXY_TARGET')
  const proxy = { '/api': { target: env.API_PROXY_TARGET || 'http://127.0.0.1:8000', changeOrigin: false } }
  return {
    plugins: [react()],
    build: { outDir: 'dist', emptyOutDir: true },
    server: { host: '127.0.0.1', port: 5173, strictPort: true, proxy },
    preview: { host: '127.0.0.1', port: 4173, strictPort: true, proxy },
  }
})
