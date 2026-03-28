/**
 * Electron 主进程 — 梦帮小助桌面客户端
 *
 * 职责:
 *  - 窗口管理 (BrowserWindow)
 *  - brain-core Python 进程生命周期
 *  - IPC 桥接 (终端 PTY、权限确认、文件对话框)
 *  - 系统托盘 + 全局快捷键
 */

import { app, BrowserWindow, globalShortcut, ipcMain, shell, dialog } from 'electron'
import path from 'node:path'
import { BrainCoreManager } from './brain-core-manager'
import { TerminalManager } from './terminal-manager'
import { setupTray } from './tray'
import { registerPermissionHandlers } from './permission-dialog'

// ── 路径常量 ──────────────────────────────────
const IS_DEV = !app.isPackaged
const WEB_PORTAL_DEV_URL = 'http://localhost:3000'
const PRELOAD_PATH = path.join(__dirname, 'preload.js')

// ── 全局引用 ──────────────────────────────────
let mainWindow: BrowserWindow | null = null
const brainCore = new BrainCoreManager()
const terminalMgr = new TerminalManager()

// ── 创建主窗口 ────────────────────────────────
function createMainWindow(): BrowserWindow {
  const win = new BrowserWindow({
    width: 1280,
    height: 860,
    minWidth: 800,
    minHeight: 600,
    title: '梦帮小助',
    icon: path.join(__dirname, '../resources/icon.png'),
    backgroundColor: '#0a0e1a',
    titleBarStyle: process.platform === 'darwin' ? 'hiddenInset' : 'default',
    webPreferences: {
      preload: PRELOAD_PATH,
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: false, // node-pty 需要
    },
  })

  // 加载页面
  if (IS_DEV) {
    win.loadURL(WEB_PORTAL_DEV_URL)
    win.webContents.openDevTools({ mode: 'detach' })
  } else {
    // 生产环境: 加载打包后的 web-portal
    const indexPath = path.join(__dirname, '../renderer/index.html')
    win.loadFile(indexPath)
  }

  // 外部链接在浏览器打开
  win.webContents.setWindowOpenHandler(({ url }) => {
    if (url.startsWith('http')) shell.openExternal(url)
    return { action: 'deny' }
  })

  win.on('closed', () => {
    mainWindow = null
  })

  // 最小化到托盘而非关闭
  win.on('close', (e) => {
    if (process.platform === 'darwin' || process.platform === 'win32') {
      if (!app.isQuitting) {
        e.preventDefault()
        win.hide()
      }
    }
  })

  return win
}

// ── IPC 处理器注册 ─────────────────────────────

function registerIpcHandlers(): void {
  // -- brain-core 进程管理 --
  ipcMain.handle('brain:start', async () => {
    return brainCore.start()
  })

  ipcMain.handle('brain:stop', async () => {
    return brainCore.stop()
  })

  ipcMain.handle('brain:status', () => {
    return brainCore.getStatus()
  })

  ipcMain.handle('brain:health', async () => {
    return brainCore.healthCheck()
  })

  // -- 终端 PTY --
  ipcMain.handle('terminal:create', async (_e, options?: { cwd?: string; shell?: string }) => {
    const id = terminalMgr.create(options)
    // 转发终端输出到渲染进程
    terminalMgr.onData(id, (data: string) => {
      mainWindow?.webContents.send('terminal:data', { id, data })
    })
    terminalMgr.onExit(id, (exitCode: number) => {
      mainWindow?.webContents.send('terminal:exit', { id, exitCode })
    })
    return id
  })

  ipcMain.handle('terminal:write', (_e, id: string, data: string) => {
    terminalMgr.write(id, data)
  })

  ipcMain.handle('terminal:resize', (_e, id: string, cols: number, rows: number) => {
    terminalMgr.resize(id, cols, rows)
  })

  ipcMain.handle('terminal:kill', (_e, id: string) => {
    terminalMgr.kill(id)
  })

  ipcMain.handle('terminal:list', () => {
    return terminalMgr.list()
  })

  // -- 文件对话框 --
  ipcMain.handle('dialog:openFile', async (_e, options?: Electron.OpenDialogOptions) => {
    const result = await dialog.showOpenDialog(mainWindow!, {
      properties: ['openFile'],
      ...options,
    })
    return result.filePaths
  })

  ipcMain.handle('dialog:openDirectory', async (_e, options?: Electron.OpenDialogOptions) => {
    const result = await dialog.showOpenDialog(mainWindow!, {
      properties: ['openDirectory'],
      ...options,
    })
    return result.filePaths
  })

  ipcMain.handle('dialog:saveFile', async (_e, options?: Electron.SaveDialogOptions) => {
    const result = await dialog.showSaveDialog(mainWindow!, options || {})
    return result.filePath
  })

  // -- 应用信息 --
  ipcMain.handle('app:info', () => ({
    version: app.getVersion(),
    platform: process.platform,
    arch: process.arch,
    isDev: IS_DEV,
    paths: {
      userData: app.getPath('userData'),
      home: app.getPath('home'),
      documents: app.getPath('documents'),
    },
  }))

  // -- 窗口控制 --
  ipcMain.handle('window:minimize', () => mainWindow?.minimize())
  ipcMain.handle('window:maximize', () => {
    if (mainWindow?.isMaximized()) mainWindow.unmaximize()
    else mainWindow?.maximize()
  })
  ipcMain.handle('window:close', () => mainWindow?.close())

  // 注册权限确认处理器
  registerPermissionHandlers(mainWindow)
}

// ── 全局快捷键 ─────────────────────────────────

function registerGlobalShortcut(): void {
  // Ctrl/Cmd+Shift+D: 显示/隐藏窗口
  globalShortcut.register('CommandOrControl+Shift+D', () => {
    if (mainWindow?.isVisible()) {
      mainWindow.hide()
    } else {
      mainWindow?.show()
      mainWindow?.focus()
    }
  })
}

// ── App 生命周期 ───────────────────────────────

// 单实例锁
const gotLock = app.requestSingleInstanceLock()
if (!gotLock) {
  app.quit()
} else {
  app.on('second-instance', () => {
    if (mainWindow) {
      if (mainWindow.isMinimized()) mainWindow.restore()
      mainWindow.show()
      mainWindow.focus()
    }
  })

  app.whenReady().then(async () => {
    // 注册 IPC 处理器
    registerIpcHandlers()

    // 创建主窗口
    mainWindow = createMainWindow()

    // 系统托盘
    setupTray(mainWindow)

    // 全局快捷键
    registerGlobalShortcut()

    // 自动启动 brain-core
    if (!IS_DEV) {
      try {
        await brainCore.start()
      } catch (err) {
        console.error('[Desktop] Failed to start brain-core:', err)
      }
    }

    app.on('activate', () => {
      if (BrowserWindow.getAllWindows().length === 0) {
        mainWindow = createMainWindow()
      } else {
        mainWindow?.show()
      }
    })
  })

  app.on('window-all-closed', () => {
    if (process.platform !== 'darwin') {
      app.quit()
    }
  })

  // 退出时清理
  ;(app as any).isQuitting = false

  app.on('before-quit', async () => {
    ;(app as any).isQuitting = true
    globalShortcut.unregisterAll()
    terminalMgr.killAll()
    await brainCore.stop()
  })
}
