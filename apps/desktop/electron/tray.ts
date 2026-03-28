/**
 * 系统托盘 — 最小化到托盘 + 右键菜单
 */

import { Tray, Menu, BrowserWindow, app, nativeImage } from 'electron'
import path from 'node:path'

let tray: Tray | null = null

export function setupTray(mainWindow: BrowserWindow): void {
  // 图标路径
  const iconPath = path.join(__dirname, '../resources/tray-icon.png')

  // 创建默认 16x16 图标（如果文件不存在则用空白图标）
  let icon: Electron.NativeImage
  try {
    icon = nativeImage.createFromPath(iconPath)
    if (icon.isEmpty()) throw new Error('empty')
  } catch {
    // 生成一个简单的默认图标
    icon = nativeImage.createEmpty()
  }

  tray = new Tray(icon)
  tray.setToolTip('梦帮小助 — AI 桌面助手')

  const contextMenu = Menu.buildFromTemplate([
    {
      label: '显示窗口',
      click: () => {
        mainWindow.show()
        mainWindow.focus()
      },
    },
    { type: 'separator' },
    {
      label: '新建对话',
      accelerator: 'CommandOrControl+N',
      click: () => {
        mainWindow.show()
        mainWindow.focus()
        mainWindow.webContents.send('action:newChat')
      },
    },
    { type: 'separator' },
    {
      label: '退出',
      click: () => {
        ;(app as any).isQuitting = true
        app.quit()
      },
    },
  ])

  tray.setContextMenu(contextMenu)

  // 点击托盘图标切换窗口
  tray.on('click', () => {
    if (mainWindow.isVisible()) {
      mainWindow.hide()
    } else {
      mainWindow.show()
      mainWindow.focus()
    }
  })
}

export function destroyTray(): void {
  tray?.destroy()
  tray = null
}
