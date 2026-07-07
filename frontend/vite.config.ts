import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { existsSync, readFileSync } from 'node:fs'
import { resolve } from 'node:path'

function readRootAdminKey() {
  const envPath = resolve(__dirname, '..', '.env')
  if (!existsSync(envPath)) return ''

  const env = readFileSync(envPath, 'utf-8')
  const line = env
    .split('\n')
    .find((item) => item.trim().startsWith('ADMIN_API_KEY='))
  if (!line) return ''

  return line
    .split('=')
    .slice(1)
    .join('=')
    .trim()
    .replace(/^["']|["']$/g, '')
}

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/api': {
        target: process.env.VITE_API_TARGET ?? 'http://127.0.0.1:8000',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, ''),
        headers: {
          'X-Admin-API-Key': process.env.VITE_ADMIN_API_KEY ?? readRootAdminKey(),
        },
      },
    },
  },
})
