import { defineConfig } from 'vitest/config'
import path from 'path'

export default defineConfig({
  test: {
    environment: 'node',
    globals: true,
    include: ['tests/**/*.test.ts'],
    setupFiles: ['tests/setup.ts'],
    testTimeout: 15000,
  },
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
      '@dreamhelp/auth': path.resolve(__dirname, '../../packages/auth/src'),
      '@dreamhelp/database': path.resolve(__dirname, '../../packages/database/src'),
    },
  },
})
