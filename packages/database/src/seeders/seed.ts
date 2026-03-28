import { PrismaClient } from '@prisma/client'

const prisma = new PrismaClient()

async function hashPassword(password: string): Promise<string> {
  const { pbkdf2, randomBytes } = await import('node:crypto')
  const { promisify } = await import('node:util')
  const pbkdf2Async = promisify(pbkdf2)
  const salt = randomBytes(32).toString('hex')
  const hash = await pbkdf2Async(password, salt, 100_000, 64, 'sha512')
  return `${salt}:${hash.toString('hex')}`
}

/** 本地默认用户 ID — 与 apps/web-portal/src/lib/local-user.ts 保持一致 */
const LOCAL_USER_ID = '00000000-0000-0000-0000-000000000001'

async function main() {
  console.log('🌱 Seeding database...')

  // ── 0. 创建本地默认用户 (免注册模式) ──
  const localUser = await prisma.user.upsert({
    where: { id: LOCAL_USER_ID },
    update: {},
    create: {
      id: LOCAL_USER_ID,
      email: 'local@dreamhelper.local',
      username: 'local',
      displayName: '本地用户',
      passwordHash: '',
      status: 'active',
      tierLevel: 0,
      emailVerified: true,
      settings: { theme: 'dark', language: 'zh-CN' },
    },
  })
  console.log(`  ✓ Local user: ${localUser.email} (免注册默认用户)`)

  // ── 1. 创建管理员用户 ──
  const adminPassword = await hashPassword('Admin@2026')
  const admin = await prisma.user.upsert({
    where: { email: 'admin@dreamvfia.com' },
    update: {},
    create: {
      email: 'admin@dreamvfia.com',
      username: 'admin',
      displayName: '系统管理员',
      passwordHash: adminPassword,
      status: 'active',
      tierLevel: 99,
      emailVerified: true,
      settings: { theme: 'dark', language: 'zh-CN' },
    },
  })
  console.log(`  ✓ Admin user: ${admin.email}`)

  const testUser = localUser

  // ── 3. 创建默认组织 ──
  const org = await prisma.organization.upsert({
    where: { slug: 'dreamvfia' },
    update: {},
    create: {
      name: 'DREAMVFIA UNION',
      slug: 'dreamvfia',
      description: '梦帮小助默认组织',
      ownerId: admin.id,
      plan: 'enterprise',
    },
  })
  console.log(`  ✓ Organization: ${org.name}`)

  // ── 4. 添加成员 ──
  await prisma.organizationMember.upsert({
    where: {
      organizationId_userId: { organizationId: org.id, userId: admin.id },
    },
    update: {},
    create: {
      organizationId: org.id,
      userId: admin.id,
      role: 'owner',
      permissions: ['admin:all'],
    },
  })

  await prisma.organizationMember.upsert({
    where: {
      organizationId_userId: { organizationId: org.id, userId: testUser.id },
    },
    update: {},
    create: {
      organizationId: org.id,
      userId: testUser.id,
      role: 'member',
      permissions: ['chat:read', 'chat:write', 'agent:create', 'kb:upload'],
    },
  })
  console.log('  ✓ Organization members')

  // ── 5. 创建默认智能体 ──
  const defaultAgent = await prisma.agent.upsert({
    where: { id: '00000000-0000-0000-0000-000000000001' },
    update: {},
    create: {
      id: '00000000-0000-0000-0000-000000000001',
      name: '梦帮小助',
      description: '你的超级 AI 助手 — 不让你思考、不让你等待、不让你重复',
      ownerId: admin.id,
      organizationId: org.id,
      type: 'system',
      systemPrompt: `你是梦帮小助，一个温暖、聪明、可靠的 AI 助手，由 DREAMVFIA UNION 开发。
你的核心理念：不让用户思考、不让用户等待、不让用户重复。
你擅长日常办公、知识检索、代码辅助、数据分析等任务。
请用友好、专业的语气回复用户，适当使用 emoji 增加亲和力。
如果不确定答案，请诚实说明，不要编造信息。`,
      modelProvider: 'minimax',
      modelName: 'abab6.5s-chat',
      temperature: 0.7,
      maxTokens: 4096,
      capabilities: ['chat', 'completion', 'tool_use'],
      tools: [],
      isPublic: true,
      status: 'active',
    },
  })
  console.log(`  ✓ Default agent: ${defaultAgent.name}`)

  const codeAgent = await prisma.agent.upsert({
    where: { id: '00000000-0000-0000-0000-000000000002' },
    update: {},
    create: {
      id: '00000000-0000-0000-0000-000000000002',
      name: '代码助手',
      description: '专注编程辅助，支持代码生成、审查、调试和解释',
      ownerId: admin.id,
      organizationId: org.id,
      type: 'system',
      systemPrompt: `你是一个专业的编程助手。
擅长 TypeScript、Python、SQL 等语言。
回复代码时使用 Markdown 代码块并标注语言。
优先给出简洁、可运行的代码，附带简要说明。`,
      modelProvider: 'minimax',
      modelName: 'abab6.5s-chat',
      temperature: 0.3,
      maxTokens: 8192,
      capabilities: ['chat', 'completion', 'tool_use'],
      tools: ['code_execute', 'web_search'],
      isPublic: true,
      status: 'active',
    },
  })
  console.log(`  ✓ Code agent: ${codeAgent.name}`)

  // ── 6. 创建默认知识库 ──
  const kb = await prisma.knowledgeBase.upsert({
    where: { id: '00000000-0000-0000-0000-000000000010' },
    update: {},
    create: {
      id: '00000000-0000-0000-0000-000000000010',
      name: '产品文档',
      description: '梦帮小助产品使用文档和常见问题',
      type: 'general',
      status: 'active',
    },
  })
  console.log(`  ✓ Knowledge base: ${kb.name}`)

  // ── 7. 创建示例会话和消息 ──
  const session1 = await prisma.chatSession.upsert({
    where: { id: '00000000-0000-0000-0000-000000000100' },
    update: {},
    create: {
      id: '00000000-0000-0000-0000-000000000100',
      userId: testUser.id,
      agentId: defaultAgent.id,
      title: '你好，梦帮小助',
      status: 'active',
    },
  })

  const session2 = await prisma.chatSession.upsert({
    where: { id: '00000000-0000-0000-0000-000000000101' },
    update: {},
    create: {
      id: '00000000-0000-0000-0000-000000000101',
      userId: testUser.id,
      agentId: codeAgent.id,
      title: 'Python 装饰器用法',
      status: 'active',
    },
  })

  const session3 = await prisma.chatSession.upsert({
    where: { id: '00000000-0000-0000-0000-000000000102' },
    update: {},
    create: {
      id: '00000000-0000-0000-0000-000000000102',
      userId: admin.id,
      agentId: defaultAgent.id,
      title: '管理员测试会话',
      status: 'active',
    },
  })

  // 会话 1 消息
  await prisma.message.createMany({
    skipDuplicates: true,
    data: [
      { id: '00000000-0000-0000-0000-000000000200', sessionId: session1.id, role: 'user',      content: '你好！我是新用户，介绍一下你自己吧',  tokens: 20,  latencyMs: null },
      { id: '00000000-0000-0000-0000-000000000201', sessionId: session1.id, role: 'assistant',  content: '你好！我是梦帮小助，由 DREAMVFIA UNION 开发的 AI 助手。我擅长日常办公、知识检索、代码辅助等任务。有什么我能帮你的吗？😊', tokens: 80, latencyMs: 1200 },
      { id: '00000000-0000-0000-0000-000000000202', sessionId: session1.id, role: 'user',      content: '你能做什么？', tokens: 8, latencyMs: null },
      { id: '00000000-0000-0000-0000-000000000203', sessionId: session1.id, role: 'assistant',  content: '我有 70 个内置技能，涵盖 5 大类：\n\n- **日常类** (15)：计算器、单位换算、密码生成等\n- **办公类** (15)：待办管理、会议纪要、发票生成等\n- **编程类** (16)：代码格式化、Base64编解码、哈希计算等\n- **文档类** (13)：Markdown处理、文本统计、正则构建等\n- **娱乐类** (11)：抛硬币、迷宫生成、数独求解等\n\n直接告诉我你需要什么，我会帮你搞定！', tokens: 200, latencyMs: 2500 },
    ],
  })

  // 会话 2 消息
  await prisma.message.createMany({
    skipDuplicates: true,
    data: [
      { id: '00000000-0000-0000-0000-000000000210', sessionId: session2.id, role: 'user',      content: '帮我写一个 Python 装饰器，用于函数计时', tokens: 15, latencyMs: null },
      { id: '00000000-0000-0000-0000-000000000211', sessionId: session2.id, role: 'assistant',  content: '```python\nimport time\nimport functools\n\ndef timer(func):\n    @functools.wraps(func)\n    def wrapper(*args, **kwargs):\n        start = time.perf_counter()\n        result = func(*args, **kwargs)\n        elapsed = time.perf_counter() - start\n        print(f"{func.__name__} 耗时: {elapsed:.4f}s")\n        return result\n    return wrapper\n\n@timer\ndef slow_function():\n    time.sleep(1)\n    return "done"\n```\n\n这个装饰器使用 `time.perf_counter()` 精确计时，`functools.wraps` 保留原函数的元信息。', tokens: 180, latencyMs: 3200 },
    ],
  })

  // 会话 3 消息
  await prisma.message.createMany({
    skipDuplicates: true,
    data: [
      { id: '00000000-0000-0000-0000-000000000220', sessionId: session3.id, role: 'user',      content: '系统状态如何？', tokens: 6, latencyMs: null },
      { id: '00000000-0000-0000-0000-000000000221', sessionId: session3.id, role: 'assistant',  content: '系统运行正常！当前状态：\n- 🟢 Web Portal: 在线\n- 🟢 Brain Core: 在线\n- 🟢 数据库: 已连接\n- 🟢 Redis: 已连接\n- 📊 已注册技能: 70 个\n- 👥 活跃用户: 2 人', tokens: 100, latencyMs: 800 },
    ],
  })
  console.log(`  ✓ Chat sessions: 3 sessions, 8 messages`)

  // ── 8. 创建示例文档 ──
  await prisma.document.createMany({
    skipDuplicates: true,
    data: [
      {
        id: '00000000-0000-0000-0000-000000000300',
        knowledgeBaseId: kb.id,
        title: '产品介绍',
        content: '梦帮小助是由 DREAMVFIA UNION 开发的企业级 AI 智能助手平台。',
        docType: 'text',
        chunkCount: 3,
        status: 'indexed',
      },
      {
        id: '00000000-0000-0000-0000-000000000301',
        knowledgeBaseId: kb.id,
        title: '常见问题 FAQ',
        content: '问：梦帮小助支持哪些模型？\n答：目前支持 MiniMax、OpenAI 等主流大模型。',
        docType: 'text',
        chunkCount: 5,
        status: 'indexed',
      },
      {
        id: '00000000-0000-0000-0000-000000000302',
        knowledgeBaseId: kb.id,
        title: '使用指南',
        content: '快速开始：1. 注册账号 2. 选择智能体 3. 开始对话',
        docType: 'text',
        chunkCount: 3,
        status: 'indexed',
      },
    ],
  })

  // 更新知识库文档数
  await prisma.knowledgeBase.update({
    where: { id: kb.id },
    data: { docCount: 3 },
  })
  console.log('  ✓ Documents: 3 docs in knowledge base')

  console.log('\n✅ Seed completed!')
  console.log('  Admin: admin@dreamvfia.com / Admin@2026')
  console.log('  Test:  test@dreamvfia.com / Test@2026')
}

main()
  .catch((e) => {
    console.error('❌ Seed failed:', e)
    process.exit(1)
  })
  .finally(async () => {
    await prisma.$disconnect()
  })
