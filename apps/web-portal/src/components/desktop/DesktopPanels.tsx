'use client'

import dynamic from 'next/dynamic'

const BrainCorePanel = dynamic(
  () => import('@/components/desktop/BrainCorePanel').then(m => m.BrainCorePanel),
  { ssr: false }
)
const TerminalPanel = dynamic(
  () => import('@/components/desktop/TerminalPanel').then(m => m.TerminalPanel),
  { ssr: false }
)

export function DesktopBrainCorePanel() {
  return <BrainCorePanel />
}

export function DesktopTerminalPanel() {
  return <TerminalPanel />
}
