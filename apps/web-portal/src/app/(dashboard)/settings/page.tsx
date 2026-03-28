'use client'

import { useState, useEffect, useCallback } from 'react'
import { useAuth } from '@/lib/auth/AuthProvider'
import { useTranslations } from 'next-intl'
import { Bell, BellOff, Download, Trash2, AlertTriangle, Bot, Globe } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { cn } from '@/lib/utils'

const STYLE_KEYS = ['default', 'concise', 'detailed', 'professional', 'casual'] as const

function StyleSettingsSection() {
  const t = useTranslations('settings')
  const [style, setStyle] = useState('default')
  const [saved, setSaved] = useState(false)

  useEffect(() => {
    const stored = localStorage.getItem('dreamhelp_style')
    if (stored) setStyle(stored)
  }, [])

  function handleChange(value: string) {
    setStyle(value)
    localStorage.setItem('dreamhelp_style', value)
    setSaved(true)
    setTimeout(() => setSaved(false), 1500)
  }

  return (
    <Card>
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="text-sm font-mono">{t('style')}</CardTitle>
          {saved && (
            <Badge variant="success" className="text-[9px] px-1.5 py-0 h-5 animate-pulse">{t('saved')}</Badge>
          )}
        </div>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
          {STYLE_KEYS.map((key) => {
            const label = t(`style${key.charAt(0).toUpperCase()}${key.slice(1)}` as any)
            const desc = t(`style${key.charAt(0).toUpperCase()}${key.slice(1)}Desc` as any)
            return (
              <button
                key={key}
                onClick={() => handleChange(key)}
                className={cn(
                  'text-left px-3 py-2.5 border text-xs font-mono transition-all rounded-md',
                  style === key
                    ? 'bg-primary/10 border-primary/40 text-primary'
                    : 'bg-secondary border-border text-foreground hover:border-primary/20'
                )}
              >
                <div className="font-bold">{label}</div>
                <div className="text-[10px] text-muted-foreground mt-0.5">{desc}</div>
              </button>
            )
          })}
        </div>
      </CardContent>
    </Card>
  )
}

interface ModelInfo {
  id: string
  provider: string
}

const PROVIDER_LABELS: Record<string, string> = {
  minimax: 'MiniMax',
  openai: 'OpenAI',
  deepseek: 'DeepSeek',
}

function ModelSettingsSection() {
  const t = useTranslations('settings')
  const [model, setModel] = useState('')
  const [models, setModels] = useState<ModelInfo[]>([])
  const [loading, setLoading] = useState(true)
  const [saved, setSaved] = useState(false)

  useEffect(() => {
    const stored = localStorage.getItem('dreamhelp_model')
    if (stored) setModel(stored)

    fetch('/api/chat/models')
      .then((r) => r.json())
      .then((d: { models?: ModelInfo[] }) => setModels(d.models ?? []))
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [])

  function handleChange(value: string) {
    setModel(value)
    localStorage.setItem('dreamhelp_model', value)
    setSaved(true)
    setTimeout(() => setSaved(false), 1500)
  }

  const grouped = models.reduce<Record<string, ModelInfo[]>>((acc, m) => {
    const key = m.provider
    if (!acc[key]) acc[key] = []
    acc[key]!.push(m)
    return acc
  }, {})

  return (
    <Card>
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Bot size={14} className="text-primary" />
            <CardTitle className="text-sm font-mono">{t('defaultModel')}</CardTitle>
          </div>
          {saved && (
            <Badge variant="success" className="text-[9px] px-1.5 py-0 h-5 animate-pulse">{t('saved')}</Badge>
          )}
        </div>
      </CardHeader>
      <CardContent>
        {loading ? (
          <p className="text-[10px] font-mono text-muted-foreground">{t('loadingModels')}</p>
        ) : models.length === 0 ? (
          <p className="text-[10px] font-mono text-muted-foreground">{t('noModels')}</p>
        ) : (
          <div className="space-y-3">
            {Object.entries(grouped).map(([provider, providerModels]) => (
              <div key={provider}>
                <p className="text-[10px] font-mono text-muted-foreground mb-1.5 tracking-widest">
                  {PROVIDER_LABELS[provider] ?? provider}
                </p>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-1.5">
                  {providerModels.map((m) => (
                    <button
                      key={m.id}
                      onClick={() => handleChange(m.id)}
                      className={cn(
                        'text-left px-3 py-2 border text-xs font-mono transition-all rounded-md',
                        model === m.id
                          ? 'bg-primary/10 border-primary/40 text-primary'
                          : 'bg-secondary border-border text-foreground hover:border-primary/20'
                      )}
                    >
                      {m.id}
                    </button>
                  ))}
                </div>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  )
}

const LOCALE_OPTIONS = [
  { value: 'zh-CN', label: '简体中文', flag: '🇨🇳' },
  { value: 'en', label: 'English', flag: '🇺🇸' },
] as const

function LanguageSettingsSection() {
  const t = useTranslations('settings')
  const [locale, setLocale] = useState('zh-CN')
  const [saved, setSaved] = useState(false)

  useEffect(() => {
    const cookie = document.cookie.split('; ').find((c) => c.startsWith('locale='))
    if (cookie) setLocale(cookie.split('=')[1] ?? 'zh-CN')
  }, [])

  function handleChange(value: string) {
    setLocale(value)
    document.cookie = `locale=${value}; path=/; max-age=31536000`
    setSaved(true)
    setTimeout(() => {
      setSaved(false)
      window.location.reload()
    }, 500)
  }

  return (
    <Card>
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Globe size={14} className="text-muted-foreground" />
            <CardTitle className="text-sm font-mono">{t('language')}</CardTitle>
          </div>
          {saved && (
            <Badge variant="success" className="text-[9px] px-1.5 py-0 h-5 animate-pulse">✓ saved</Badge>
          )}
        </div>
        <CardDescription className="text-[10px] font-mono">{t('languageDesc')}</CardDescription>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-2 gap-2">
          {LOCALE_OPTIONS.map((opt) => (
            <button
              key={opt.value}
              onClick={() => handleChange(opt.value)}
              className={cn(
                'flex items-center gap-2 px-3 py-2.5 border text-xs font-mono transition-all rounded-md',
                locale === opt.value
                  ? 'bg-primary/10 border-primary/40 text-primary'
                  : 'bg-secondary border-border text-foreground hover:border-primary/20'
              )}
            >
              <span>{opt.flag}</span>
              <span className="font-bold">{opt.label}</span>
            </button>
          ))}
        </div>
      </CardContent>
    </Card>
  )
}

function NotificationSettingsSection() {
  const t = useTranslations('settings')
  const [proactive, setProactive] = useState(true)
  const [sound, setSound] = useState(true)
  const [saved, setSaved] = useState(false)

  useEffect(() => {
    const stored = localStorage.getItem('dreamhelp_notifications')
    if (stored) {
      try {
        const val = JSON.parse(stored) as { proactive?: boolean; sound?: boolean }
        if (val.proactive !== undefined) setProactive(val.proactive)
        if (val.sound !== undefined) setSound(val.sound)
      } catch { /* ignore */ }
    }
  }, [])

  function save(p: boolean, s: boolean) {
    setProactive(p)
    setSound(s)
    localStorage.setItem('dreamhelp_notifications', JSON.stringify({ proactive: p, sound: s }))
    setSaved(true)
    setTimeout(() => setSaved(false), 1500)
  }

  return (
    <Card>
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="text-sm font-mono">{t('notificationPrefs')}</CardTitle>
          {saved && (
            <Badge variant="success" className="text-[9px] px-1.5 py-0 h-5 animate-pulse">{t('saved')}</Badge>
          )}
        </div>
      </CardHeader>
      <CardContent className="space-y-3">
        <label className="flex items-center justify-between cursor-pointer group">
          <div className="flex items-center gap-2 text-xs font-mono text-foreground">
            {proactive ? <Bell size={14} className="text-primary" /> : <BellOff size={14} className="text-muted-foreground" />}
            {t('proactiveNotif')}
          </div>
          <button
            onClick={() => save(!proactive, sound)}
            className={cn('w-10 h-5 rounded-full transition-colors relative', proactive ? 'bg-primary' : 'bg-secondary border border-border')}
          >
            <span className={cn('absolute top-0.5 w-4 h-4 rounded-full bg-white transition-all', proactive ? 'left-5' : 'left-0.5')} />
          </button>
        </label>
        <label className="flex items-center justify-between cursor-pointer group">
          <span className="text-xs font-mono text-foreground">{t('notifSound')}</span>
          <button
            onClick={() => save(proactive, !sound)}
            className={cn('w-10 h-5 rounded-full transition-colors relative', sound ? 'bg-primary' : 'bg-secondary border border-border')}
          >
            <span className={cn('absolute top-0.5 w-4 h-4 rounded-full bg-white transition-all', sound ? 'left-5' : 'left-0.5')} />
          </button>
        </label>
      </CardContent>
    </Card>
  )
}

function DataExportSection() {
  const t = useTranslations('settings')
  const [exporting, setExporting] = useState(false)

  const handleExport = useCallback(async (format: 'json' | 'markdown') => {
    setExporting(true)
    try {
      const res = await fetch(`/api/user/export?format=${format}`, { credentials: 'include' })
      if (!res.ok) throw new Error('Export failed')
      const blob = await res.blob()
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `dreamhelp-export-${Date.now()}.${format === 'json' ? 'json' : 'md'}`
      a.click()
      URL.revokeObjectURL(url)
    } catch {
      alert('导出失败，请稍后重试')
    } finally {
      setExporting(false)
    }
  }, [])

  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="text-sm font-mono">{t('dataExport')}</CardTitle>
        <CardDescription className="text-[10px] font-mono">{t('exportDesc')}</CardDescription>
      </CardHeader>
      <CardContent>
        <div className="flex gap-2">
          <Button variant="outline" size="sm" onClick={() => handleExport('json')} disabled={exporting} className="font-mono text-xs gap-1.5">
            <Download size={12} />
            {t('exportJSON')}
          </Button>
          <Button variant="outline" size="sm" onClick={() => handleExport('markdown')} disabled={exporting} className="font-mono text-xs gap-1.5">
            <Download size={12} />
            {t('exportMarkdown')}
          </Button>
        </div>
      </CardContent>
    </Card>
  )
}

function DangerZoneSection() {
  const t = useTranslations('settings')
  const [confirmDelete, setConfirmDelete] = useState(false)
  const [deleting, setDeleting] = useState(false)

  async function handleDeleteChats() {
    if (!confirmDelete) {
      setConfirmDelete(true)
      return
    }
    setDeleting(true)
    try {
      const res = await fetch('/api/user/chats', { method: 'DELETE', credentials: 'include' })
      const data = (await res.json()) as { success: boolean }
      if (data.success) {
        alert('所有对话已删除')
        setConfirmDelete(false)
      } else {
        alert('删除失败')
      }
    } catch {
      alert('网络错误')
    } finally {
      setDeleting(false)
    }
  }

  return (
    <Card className="border-destructive/20">
      <CardHeader className="pb-3">
        <div className="flex items-center gap-2">
          <AlertTriangle size={14} className="text-destructive" />
          <CardTitle className="text-sm font-mono text-destructive">{t('dangerZone')}</CardTitle>
        </div>
      </CardHeader>
      <CardContent>
        <div className="flex items-center justify-between">
          <div>
            <p className="text-xs font-mono text-foreground">{t('deleteAllChats')}</p>
            <p className="text-[10px] font-mono text-muted-foreground">{t('deleteAllChatsDesc')}</p>
          </div>
          <Button
            variant={confirmDelete ? 'destructive' : 'outline'}
            size="sm"
            onClick={handleDeleteChats}
            disabled={deleting}
            className="font-mono text-xs gap-1.5"
          >
            <Trash2 size={12} />
            {confirmDelete ? t('confirmDelete') : t('deleteAllChats')}
          </Button>
        </div>
      </CardContent>
    </Card>
  )
}

function ApiKeysSettingsSection() {
  const [keys, setKeys] = useState<Record<string, string>>({})
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [saved, setSaved] = useState(false)

  useEffect(() => {
    fetch('/api/settings/keys')
      .then(r => r.json())
      .then(d => {
        if (!d.error) setKeys(d)
      })
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [])

  function handleChange(k: string, v: string) {
    setKeys(prev => ({ ...prev, [k]: v }))
  }

  async function handleSave() {
    setSaving(true)
    try {
      const res = await fetch('/api/settings/keys', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(keys)
      })
      if (res.ok) {
        setSaved(true)
        setTimeout(() => setSaved(false), 2000)
      }
    } catch {}
    setSaving(false)
  }

  const providers = ['OPENAI_API_KEY', 'MINIMAX_API_KEY', 'DEEPSEEK_API_KEY', 'QWEN_API_KEY', 'GLM_API_KEY', 'KIMI_API_KEY', 'NVIDIA_API_KEY']

  return (
    <Card className="border-primary/30 shadow-[0_0_15px_hsl(var(--primary)/0.05)]">
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="text-sm font-mono flex items-center gap-2">
            <Globe size={14} className="text-primary" />
            自定义 API Keys (BYOK)
          </CardTitle>
          {saved && <Badge variant="success" className="text-[9px] px-1.5 py-0 h-5 animate-pulse">✓ saved</Badge>}
        </div>
        <CardDescription className="text-[10px] font-mono">
          将使用您配置的 API Key 覆盖系统的默认设置。留空使用系统默认。存储在此本机的 PostgreSQL 数据库中。
        </CardDescription>
      </CardHeader>
      <CardContent>
        {loading ? (
          <p className="text-[10px] font-mono text-muted-foreground">加载中...</p>
        ) : (
          <div className="space-y-3">
            {providers.map(p => (
              <div key={p} className="flex flex-col gap-1.5">
                <label className="text-[10px] font-mono text-muted-foreground">{p.replace('_API_KEY', '')}</label>
                <input
                  type="password"
                  value={keys[p] || ''}
                  onChange={e => handleChange(p, e.target.value)}
                  placeholder={`未配置 ${p}`}
                  className="w-full bg-secondary border border-border rounded-md px-3 py-1.5 text-xs font-mono focus:border-primary/50 outline-none transition-colors"
                />
              </div>
            ))}
            <div className="pt-2">
              <Button onClick={handleSave} disabled={saving} size="sm" className="font-mono text-xs bg-primary/20 text-primary hover:bg-primary/30 border border-primary/50">
                {saving ? '保存中...' : '保存 API Keys'}
              </Button>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  )
}

export default function SettingsPage() {
  const { user } = useAuth()
  const t = useTranslations('settings')
  const tTier = useTranslations('tier')

  return (
    <div className="p-6">
      <div className="flex items-center gap-3 mb-6">
        <div className="w-1 h-8 bg-primary rounded-full shadow-[0_0_8px_hsl(var(--primary)/0.4)]" />
        <div>
          <h1 className="font-display text-xl font-bold text-foreground tracking-wider">{t('title')}</h1>
          <p className="text-xs font-mono text-muted-foreground mt-0.5">{t('subtitle')}</p>
        </div>
      </div>

      <div className="space-y-6 max-w-2xl">
        {/* 账户信息 */}
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-mono">{t('accountInfo')}</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2 text-xs font-mono">
              <div className="flex items-center gap-3">
                <span className="text-muted-foreground w-16">{t('email')}</span>
                <span className="text-foreground">{user?.email ?? '—'}</span>
              </div>
              <div className="flex items-center gap-3">
                <span className="text-muted-foreground w-16">{t('username')}</span>
                <span className="text-foreground">{user?.username ?? '—'}</span>
              </div>
              <div className="flex items-center gap-3">
                <span className="text-muted-foreground w-16">{t('level')}</span>
                <Badge variant="cyber" className="text-[9px] px-1.5 py-0 h-4">
                  {user?.tierLevel && user.tierLevel >= 9 ? tTier('admin') : tTier('free')}
                </Badge>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* API Keys BYOK */}
        <ApiKeysSettingsSection />

        {/* AI 回复风格 */}
        <StyleSettingsSection />

        {/* 默认模型 */}
        <ModelSettingsSection />

        {/* 语言切换 */}
        <LanguageSettingsSection />

        {/* 通知偏好 */}
        <NotificationSettingsSection />

        {/* 数据导出 */}
        <DataExportSection />

        {/* 危险区域 */}
        <DangerZoneSection />
      </div>
    </div>
  )
}
