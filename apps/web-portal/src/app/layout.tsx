import type { Metadata, Viewport } from 'next'
import { AuthProvider } from '@/lib/auth/AuthProvider'
import { PWAProvider } from '@/components/pwa/PWAProvider'
import 'katex/dist/katex.min.css'
import './globals.css'

const metadataBase = new URL(process.env.NEXT_PUBLIC_APP_URL ?? 'http://localhost:3000')

export const viewport: Viewport = {
  width: 'device-width',
  initialScale: 1,
  maximumScale: 1,
  viewportFit: 'cover',
  themeColor: '#ef4444',
}

export const metadata: Metadata = {
  metadataBase,
  title: 'DREAMVFIA · DreamHelper AI Assistant',
  description: 'DreamHelper v3.7 enterprise AI workspace by DREAMVFIA UNION.',
  manifest: '/manifest.json',
  icons: {
    icon: '/favicon.ico',
    apple: '/logo/avatar-192.png',
  },
  appleWebApp: {
    capable: true,
    statusBarStyle: 'black-translucent',
    title: 'DreamHelper',
  },
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="zh-CN" className="dark">
      <body className="min-h-screen bg-background text-foreground antialiased">
        <AuthProvider>{children}</AuthProvider>
        <PWAProvider />
      </body>
    </html>
  )
}
