import { fileURLToPath } from 'node:url'
import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'

// Keep in sync with "paths" in tsconfig.app.json.
const srcAliases = ['api', 'components', 'hooks', 'schemas', 'utils', 'views']
const alias = Object.fromEntries(
  srcAliases.map((dir) => [`@${dir}`, fileURLToPath(new URL(`./src/${dir}`, import.meta.url))]),
)

// Env vars live in the repo-root .env, shared with the backend services.
const envDir = fileURLToPath(new URL('..', import.meta.url))

// The browser always calls relative `/api/...` URLs and Vite forwards them to the
// backend. That avoids CORS (the backend has no CORS middleware) and lets the same
// code run locally (backend on :8100) and in Docker (backend at orion-backend:8000).
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, envDir, '')
  const apiTarget = env.API_PROXY_TARGET || 'http://localhost:8100'

  return {
    envDir,
    plugins: [react()],
    resolve: { alias },
    server: {
      host: true,
      port: 5173,
      proxy: {
        '/api': { target: apiTarget, changeOrigin: true },
      },
    },
  }
})
