import { NextRequest, NextResponse } from 'next/server'
import { prisma } from '@dreamhelp/database'
import { getLocalUserId } from '@/lib/local-user'
import { brainCoreFetch } from '@/lib/brain-core-url'

// GET /api/knowledge/[id] — 获取单个文档详情
export async function GET(req: NextRequest, { params }: { params: Promise<{ id: string }> }) {
  try {
    const userId = getLocalUserId()
    const { id } = await params

    const doc = await prisma.document.findUnique({
      where: { id },
      include: { knowledgeBase: { select: { ownerId: true } } },
    })

    if (!doc || doc.knowledgeBase.ownerId !== userId) {
      return NextResponse.json({ success: false, error: '文档不存在' }, { status: 404 })
    }

    return NextResponse.json({
      success: true,
      document: {
        id: doc.id,
        title: doc.title,
        content: doc.content,
        docType: doc.docType,
        status: doc.status,
        chunkCount: doc.chunkCount,
        createdAt: doc.createdAt,
        updatedAt: doc.updatedAt,
      },
    })
  } catch (error) {
    console.error('knowledge get failed:', error)
    return NextResponse.json({ success: false, error: '服务器错误' }, { status: 500 })
  }
}

// DELETE /api/knowledge/[id] — 删除文档
export async function DELETE(req: NextRequest, { params }: { params: Promise<{ id: string }> }) {
  try {
    const userId = getLocalUserId()
    const { id } = await params

    const doc = await prisma.document.findUnique({
      where: { id },
      include: { knowledgeBase: { select: { id: true, ownerId: true } } },
    })

    if (!doc || doc.knowledgeBase.ownerId !== userId) {
      return NextResponse.json({ success: false, error: '文档不存在' }, { status: 404 })
    }

    await prisma.document.delete({ where: { id } })

    // 更新文档计数
    await prisma.knowledgeBase.update({
      where: { id: doc.knowledgeBase.id },
      data: { docCount: { decrement: 1 } },
    })

    // 通知 brain-core RAG 删除索引（后台异步）
    void brainCoreFetch(`/api/v1/rag/document/${id}`, { method: 'DELETE' }).catch(() => {})

    return NextResponse.json({ success: true })
  } catch (error) {
    console.error('knowledge delete failed:', error)
    return NextResponse.json({ success: false, error: '服务器错误' }, { status: 500 })
  }
}
