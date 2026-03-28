import { NextRequest, NextResponse } from 'next/server'
import { jwtVerify } from 'jose'
import { prisma } from '@dreamhelp/database'
import { sendEmail, sendBatchEmails } from '@/lib/email/resend'
import { addEmailLog } from '@/lib/email/email-logs'

const getSecret = () => {
  const s = process.env.JWT_SECRET
  if (!s && process.env.NODE_ENV === 'production') throw new Error('JWT_SECRET is required')
  return new TextEncoder().encode(s || 'dev-secret-do-not-use-in-production')
}

interface SendBody {
  to?: string[]
  subject?: string
  html?: string
  sendType?: 'single' | 'batch' | 'all_users'
}

/** 验证 super_admin 权限 */
async function verifySuperAdmin(req: NextRequest): Promise<{ authorized: boolean; error?: string }> {
  const token = req.cookies.get('token')?.value
  if (!token) return { authorized: false, error: '未登录' }

  try {
    const { payload } = await jwtVerify(token, getSecret(), { issuer: 'dreamhelp' })
    const role = (payload as Record<string, unknown>).role as string | undefined
    if (role !== 'super_admin' && role !== 'admin') {
      return { authorized: false, error: '需要管理员权限' }
    }
    return { authorized: true }
  } catch {
    return { authorized: false, error: 'Token 无效' }
  }
}

// ═══ POST /api/admin/email/send ═══

export async function POST(req: NextRequest) {
  const auth = await verifySuperAdmin(req)
  if (!auth.authorized) {
    return NextResponse.json({ success: false, error: auth.error }, { status: 403 })
  }

  let body: SendBody
  try {
    body = (await req.json()) as SendBody
  } catch {
    return NextResponse.json({ success: false, error: '请求格式错误' }, { status: 400 })
  }

  const { subject, html, sendType = 'single' } = body

  if (!subject?.trim()) {
    return NextResponse.json({ success: false, error: '请填写邮件主题' }, { status: 400 })
  }
  if (!html?.trim()) {
    return NextResponse.json({ success: false, error: '请填写邮件内容' }, { status: 400 })
  }

  let recipients: string[] = []

  if (sendType === 'all_users') {
    // 获取所有 active + emailVerified 用户
    const users = await prisma.user.findMany({
      where: { status: 'active', emailVerified: true },
      select: { email: true },
    })
    recipients = users.map(({ email }) => email)
  } else {
    recipients = body.to ?? []
  }

  if (recipients.length === 0) {
    return NextResponse.json({ success: false, error: '无有效收件人' }, { status: 400 })
  }

  // 单封发送
  if (recipients.length === 1) {
    const result = await sendEmail({ to: recipients[0]!, subject, html })
    addEmailLog({ subject, recipientCount: 1, sent: result.success ? 1 : 0, failed: result.success ? 0 : 1 })
    return NextResponse.json({
      success: result.success,
      data: { total: 1, sent: result.success ? 1 : 0, failed: result.success ? 0 : 1, id: result.id },
      error: result.error,
    })
  }

  // 批量发送
  const result = await sendBatchEmails({ recipients, subject, html })
  addEmailLog({ subject, recipientCount: result.total, sent: result.sent, failed: result.failed })

  return NextResponse.json({
    success: result.failed === 0,
    data: result,
  })
}
