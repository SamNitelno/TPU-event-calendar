import { defineConfig } from 'vite'
import { resolve } from 'path'

export default defineConfig({
  build: {
    outDir: 'static/dist',
    emptyOutDir: true,
    rollupOptions: {
      input: {
        style: resolve(__dirname, 'static/style.css'),
        api: resolve(__dirname, 'src/api.ts')
      },
      output: {
        assetFileNames: '[name].[hash][extname]',
        chunkFileNames: '[name].[hash].js',
        entryFileNames: '[name].[hash].js'
      }
    }
  },
  server: {
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true
      }
    }
  }
})
