// Vite build, dev server and Vitest configuration.
/// <reference types="vitest/config" />
import { fileURLToPath, URL } from 'node:url'

import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: { '@': fileURLToPath(new URL('./src', import.meta.url)) },
  },
  server: {
    port: 5173,
    strictPort: true,
    // Same-origin in development: the browser only talks to :5173, so the refresh cookie
    // (SameSite=Strict, Path=/api/v1/auth) just works and no CORS preflights are needed.
    proxy: {
      '/api': { target: 'http://localhost:8000', xfwd: true },
    },
  },
  build: {
    sourcemap: false, // don't publish source maps: they would expose the original source
    rolldownOptions: {
      output: {
        // Libraries change less often than app code, so separate chunks stay cached across deploys.
        // Anything not listed (the Markdown stack) stays with the lazy page that imports it.
        codeSplitting: {
          groups: [
            {
              name: 'react',
              test: /node_modules[\\/](react|react-dom|react-router|scheduler)[\\/]/,
            },
            {
              name: 'motion',
              test: /node_modules[\\/](motion|framer-motion|motion-dom|motion-utils)[\\/]/,
            },
            {
              name: 'vendor',
              test: /node_modules[\\/](@tanstack|lucide-react|clsx|tailwind-merge|class-variance-authority)[\\/]/,
            },
          ],
        },
      },
    },
  },
  test: {
    environment: 'jsdom',
    setupFiles: ['./src/test/setup.ts'],
    restoreMocks: true,
  },
})
