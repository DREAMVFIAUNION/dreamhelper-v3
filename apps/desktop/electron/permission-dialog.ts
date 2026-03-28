/**
 * PermissionDialog — 原生 Electron 权限确认对话框
 *
 * 当 brain-core 的 PermissionGateway 标记操作为 DANGEROUS/CONFIRM 时,
 * 通过 IPC 通知 Electron 主进程弹出原生确认对话框。
 *
 * 对话框类型:
 *  - 文件写入确认
 *  - Shell 命令执行确认
 *  - 高危操作二次确认
 */

import { BrowserWindow, dialog, ipcMain } from 'electron'

export interface PermissionRequest {
  type: 'file_write' | 'file_delete' | 'shell_exec' | 'shell_dangerous'
  description: string
  details: string
  riskLevel: 'confirm' | 'dangerous'
}

export function registerPermissionHandlers(mainWindow: BrowserWindow | null): void {
  ipcMain.handle('permission:request', async (_event, request: PermissionRequest) => {
    const win = mainWindow || BrowserWindow.getFocusedWindow()
    if (!win) return { approved: false, reason: '无活动窗口' }

    const riskEmoji = request.riskLevel === 'dangerous' ? '🔴' : '🟡'
    const title = request.riskLevel === 'dangerous' ? '高危操作确认' : '操作确认'

    const typeLabels: Record<string, string> = {
      file_write: '文件写入',
      file_delete: '文件删除',
      shell_exec: '命令执行',
      shell_dangerous: '高危命令',
    }

    const result = await dialog.showMessageBox(win, {
      type: request.riskLevel === 'dangerous' ? 'warning' : 'question',
      title: `${riskEmoji} ${title}`,
      message: `${typeLabels[request.type] || request.type}`,
      detail: [
        request.description,
        '',
        `详情: ${request.details}`,
        '',
        request.riskLevel === 'dangerous'
          ? '⚠️ 此操作具有较高风险，请确认是否继续。'
          : '请确认是否允许此操作。',
      ].join('\n'),
      buttons: ['允许', '拒绝'],
      defaultId: 1, // 默认选中 "拒绝"
      cancelId: 1,
      noLink: true,
    })

    const approved = result.response === 0
    console.log(`[Permission] ${request.type}: ${approved ? 'APPROVED' : 'DENIED'} — ${request.details.slice(0, 80)}`)

    return { approved }
  })

  // 批量权限请求 (一次确认多个操作)
  ipcMain.handle('permission:requestBatch', async (_event, requests: PermissionRequest[]) => {
    const win = mainWindow || BrowserWindow.getFocusedWindow()
    if (!win) return { approved: false, reason: '无活动窗口' }

    const details = requests.map((r, i) => `${i + 1}. [${r.type}] ${r.description}`).join('\n')

    const result = await dialog.showMessageBox(win, {
      type: 'question',
      title: `🟡 批量操作确认 (${requests.length} 项)`,
      message: '以下操作需要您的确认:',
      detail: details,
      buttons: ['全部允许', '拒绝'],
      defaultId: 1,
      cancelId: 1,
      noLink: true,
    })

    const approved = result.response === 0
    return { approved }
  })
}
