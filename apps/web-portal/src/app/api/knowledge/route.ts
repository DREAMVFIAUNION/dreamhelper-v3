import { NextRequest, NextResponse } from 'next/server'
import { prisma } from '@dreamhelp/database'
import { getLocalUserId } from '@/lib/local-user'
import crypto from 'crypto'
import { brainCoreFetch } from '@/lib/brain-core-url'

// GET /api/knowledge — 列出当前用户的知识库文档
export async function GET(req: NextRequest) {
  try {
    const userId = getLocalUserId()
    const { searchParams } = new URL(req.url)
    const q = searchParams.get('q') || ''

    // 确保用户有默认知识库
    let kb = await prisma.knowledgeBase.findFirst({ where: { ownerId: userId } })
    if (!kb) {
      kb = await prisma.knowledgeBase.create({
        data: {
          name: '我的知识库',
          description: '默认知识库',
          owner: { connect: { id: userId } },
        },
      })
    }

    const documents = await prisma.document.findMany({
      where: { knowledgeBaseId: kb.id, ...(q ? { title: { contains: q } } : {}) },
      orderBy: { createdAt: 'desc' },
      select: {
        id: true,
        title: true,
        docType: true,
        status: true,
        chunkCount: true,
        createdAt: true,
        updatedAt: true,
      },
    })

    return NextResponse.json({
      success: true,
      knowledgeBaseId: kb.id,
      documents,
      total: documents.length,
    })
  } catch (error) {
    console.error('knowledge list failed:', error)
    return NextResponse.json({ success: false, error: '服务器错误' }, { status: 500 })
  }
}

// POST /api/knowledge — 上传文档 (text/markdown 纯文本)
export async function POST(req: NextRequest) {
  try {
    const userId = getLocalUserId()
    const body = await req.json()
    const { title, content, type } = body as { title?: string; content?: string; type?: string }

    if (!content || !content.trim()) {
      return NextResponse.json({ success: false, error: '内容不能为空' }, { status: 400 })
    }

    // 确保用户有知识库
    let kb = await prisma.knowledgeBase.findFirst({ where: { ownerId: userId } })
    if (!kb) {
      kb = await prisma.knowledgeBase.create({
        data: {
          name: '我的知识库',
          description: '默认知识库',
          owner: { connect: { id: userId } },
        },
      })
    }

    const docTitle = title || content.slice(0, 50).replace(/\n/g, ' ') + '...'
    const docType = type || 'text'
    const contentHash = crypto.createHash('sha256').update(content).digest('hex')

    // 简单分块: 按段落分割，每块最大 500 字
    const chunks = chunkText(content, 500)

    const doc = await prisma.document.create({
      data: {
        title: docTitle,
        docType,
        content,
        contentHash,
        status: 'ready',
        chunkCount: chunks.length,
        knowledgeBaseId: kb.id,
      },
    })

    // 更新知识库文档计数
    await prisma.knowledgeBase.update({
      where: { id: kb.id },
      data: { docCount: { increment: 1 } },
    })

    // 通知 brain-core RAG 摄入（后台异步，不阻塞）
    void brainCoreFetch('/api/v1/rag/ingest', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ doc_id: doc.id, title: docTitle, content, type: docType }),
    }).catch(() => {})

    return NextResponse.json({
      success: true,
      document: {
        id: doc.id,
        title: doc.title,
        docType: doc.docType,
        chunkCount: chunks.length,
      },
    })
  } catch (error) {
    console.error('knowledge upload failed:', error)
    return NextResponse.json({ success: false, error: '服务器错误' }, { status: 500 })
  }
}

function chunkText(text: string, maxLen: number): string[] {
  const paragraphs = text.split(/\n{2,}/)
  const chunks: string[] = []
  let current = ''

  for (const p of paragraphs) {
    if ((current + '\n\n' + p).length > maxLen && current) {
      chunks.push(current.trim())
      current = p
    } else {
      current = current ? current + '\n\n' + p : p
    }
  }
  if (current.trim()) {
    chunks.push(current.trim())
  }
  return chunks.length > 0 ? chunks : [text]
}
