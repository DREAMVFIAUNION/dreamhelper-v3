/// <reference types="electron-vite/node" />

import type { ElectronAPI } from './preload'

declare global {
  interface Window {
    electronAPI: ElectronAPI
  }
}
