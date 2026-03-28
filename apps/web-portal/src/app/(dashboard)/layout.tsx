import { NextIntlClientProvider } from 'next-intl'
import { getMessages } from 'next-intl/server'
import { TopNav } from '@/components/layout/TopNav'
import { Sidebar } from '@/components/layout/Sidebar'
import { ErrorBoundary } from '@/components/ErrorBoundary'
import { CommandPalette } from '@/components/layout/CommandPalette'
import { Toaster } from '@/components/ui/sonner'
import { DesktopBrainCorePanel, DesktopTerminalPanel } from '@/components/desktop/DesktopPanels'

export default async function DashboardLayout({ children }: { children: React.ReactNode }) {
  const messages = await getMessages()

  return (
    <NextIntlClientProvider messages={messages}>
      <div className="flex h-screen bg-background overflow-hidden">
        <Sidebar />
        <div className="flex-1 flex flex-col min-w-0">
          <TopNav />
          <DesktopBrainCorePanel />
          <main className="flex-1 overflow-y-auto">
            <ErrorBoundary>{children}</ErrorBoundary>
          </main>
          <DesktopTerminalPanel />
        </div>
      </div>
      <CommandPalette />
      <Toaster />
    </NextIntlClientProvider>
  )
}
