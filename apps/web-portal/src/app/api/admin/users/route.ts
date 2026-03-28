import { NextRequest, NextResponse } from 'next/server'
import { prisma } from '@dreamhelp/database'
import { getLocalUserId } from '@/lib/local-user'

// ═══ GET /api/admin/users — 用户列表 (分页+搜索) ═══

export async function GET(req: NextRequest) {
  try {
    const url = req.nextUrl
    const page = Math.max(1, Number(url.searchParams.get('page') ?? '1'))
    const limit = Math.min(100, Math.max(1, Number(url.searchParams.get('limit') ?? '20')))
    const search = url.searchParams.get('search')?.trim() ?? ''
    const status = url.searchParams.get('status')?.trim() ?? ''

    const where: Record<string, unknown> = {}

    if (search) {
      where.OR = [
        { email: { contains: search, mode: 'insensitive' } },
        { username: { contains: search, mode: 'insensitive' } },
        { displayName: { contains: search, mode: 'insensitive' } },
      ]
    }

    if (status && ['active', 'locked', 'banned'].includes(status)) {
      where.status = status
    }

    const [total, users] = await Promise.all([
      prisma.user.count({ where }),
      prisma.user.findMany({
        where,
        select: {
          id: true,
          email: true,
          username: true,
          displayName: true,
          avatarUrl: true,
          status: true,
          tierLevel: true,
          emailVerified: true,
          createdAt: true,
          lastLoginAt: true,
        },
        orderBy: { createdAt: 'desc' },
        skip: (page - 1) * limit,
        take: limit,
      }),
    ])

    return NextResponse.json({
      success: true,
      users,
      pagination: {
        page,
        limit,
        total,
        totalPages: Math.ceil(total / limit),
      },
    })
  } catch (error) {
    console.error('admin users list failed:', error)
    return NextResponse.json({ success: false, error: '服务器错误' }, { status: 500 })
  }
}

// ═══ POST /api/admin/users — 管理员创建用户 ═══

export async function POST(req: NextRequest) {
  try {
    const body = (await req.json()) as {
      email?: string
      username?: string
      displayName?: string
      password?: string
      tierLevel?: number
    }

    if (!body.email || !body.username || !body.password) {
      return NextResponse.json({ success: false, error: '邮箱、用户名、密码为必填项' }, { status: 400 })
    }

    const PASSWORD_REGEX = /^(?=.*[a-z])(?=.*[A-Z])(?=.*\d).{8,}$/
    if (!PASSWORD_REGEX.test(body.password)) {
      return NextResponse.json({ success: false, error: '密码至少 8 位，且需包含大小写字母和数字' }, { status: 400 })
    }

    // 检查重复
    const existing = await prisma.user.findFirst({
      where: { OR: [{ email: body.email }, { username: body.username }] },
    })
    if (existing) {
      return NextResponse.json({ success: false, error: '邮箱或用户名已存在' }, { status: 409 })
    }

    const { pbkdf2, randomBytes } = await import('node:crypto')
    const { promisify } = await import('node:util')
    const pbkdf2Async = promisify(pbkdf2)
    const salt = randomBytes(32).toString('hex')
    const hash = await pbkdf2Async(body.password, salt, 100_000, 64, 'sha512')
    const passwordHash = `${salt}:${hash.toString('hex')}`
    const user = await prisma.user.create({
      data: {
        email: body.email,
        username: body.username,
        displayName: body.displayName || body.username,
        passwordHash,
        tierLevel: body.tierLevel ?? 0,
        status: 'active',
        emailVerified: true, // 管理员创建的用户默认已验证
      },
      select: {
        id: true,
        email: true,
        username: true,
        displayName: true,
        status: true,
        tierLevel: true,
        createdAt: true,
      },
    })

    return NextResponse.json({ success: true, user })
  } catch (error) {
    console.error('admin create user failed:', error)
    return NextResponse.json({ success: false, error: '服务器错误' }, { status: 500 })
  }
}

// ═══ PATCH /api/admin/users — 更新用户状态 ═══

export async function PATCH(req: NextRequest) {
  try {
    const body = (await req.json()) as {
      userId?: string
      action?: 'activate' | 'lock' | 'ban' | 'setTier'
      tierLevel?: number
    }

    const { userId, action, tierLevel } = body

    if (!userId || !action) {
      return NextResponse.json({ success: false, error: '参数缺失' }, { status: 400 })
    }

    const targetUser = await prisma.user.findUnique({ where: { id: userId } })
    if (!targetUser) {
      return NextResponse.json({ success: false, error: '用户不存在' }, { status: 404 })
    }

    const operatorId = getLocalUserId()
    const operator = await prisma.user.findUnique({ where: { id: operatorId }, select: { tierLevel: true } })

    const updates: Record<string, unknown> = {}

    switch (action) {
      case 'activate':
        updates.status = 'active'
        updates.metadata = { ...(targetUser.metadata as Record<string, unknown>), failedAttempts: 0 }
        break
      case 'lock':
        updates.status = 'locked'
        break
      case 'ban':
        updates.status = 'banned'
        break
      case 'setTier':
        if (tierLevel === undefined || tierLevel < 0 || tierLevel > 10) {
          return NextResponse.json({ success: false, error: 'tierLevel 需在 0-10 之间' }, { status: 400 })
        }
        // 仅超管可修改用户等级，且不允许设置超过自身等级
        if (!operator || operator.tierLevel < 10) {
          return NextResponse.json({ success: false, error: '仅超级管理员可修改用户等级' }, { status: 403 })
        }
        updates.tierLevel = tierLevel
        break
      default:
        return NextResponse.json({ success: false, error: '未知操作' }, { status: 400 })
    }

    const updated = await prisma.user.update({
      where: { id: userId },
      data: updates,
      select: { id: true, email: true, status: true, tierLevel: true },
    })

    return NextResponse.json({ success: true, user: updated })
  } catch (error) {
    console.error('admin user update failed:', error)
    return NextResponse.json({ success: false, error: '服务器错误' }, { status: 500 })
  }
}
