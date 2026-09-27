import path from 'node:path'
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vitest/config'

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(import.meta.dirname, './src'),
    },
  },
  test: {
    environment: 'jsdom',
    setupFiles: ['./src/test/setup.ts'],
    css: false,
    // Required for @testing-library/react's automatic afterEach(cleanup)
    // registration — without it, DOM from a previous test can leak into
    // the next one (duplicate-element failures that have nothing to do
    // with the component under test).
    globals: true,
  },
})
