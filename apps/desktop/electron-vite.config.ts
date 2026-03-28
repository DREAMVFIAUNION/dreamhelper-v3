import { defineConfig, externalizeDepsPlugin } from 'electron-vite'
import path from 'node:path'

export default defineConfig({
  main: {
    plugins: [externalizeDepsPlugin()],
    build: {
      outDir: 'dist-electron',
      rollupOptions: {
        input: {
          main: path.resolve(__dirname, 'electron/main.ts'),
        },
        external: ['node-pty'],
      },
    },
  },
  preload: {
    plugins: [externalizeDepsPlugin()],
    build: {
      outDir: 'dist-electron',
      rollupOptions: {
        input: {
          preload: path.resolve(__dirname, 'electron/preload.ts'),
        },
      },
    },
  },
  renderer: {
    // 渲染进程不需要单独构建 — 使用 web-portal 的构建输出
    build: {
      outDir: 'dist/renderer',
    },
  },
})
