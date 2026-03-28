import { NextRequest, NextResponse } from 'next/server'
import { prisma } from '@dreamhelp/database'
import { getLocalUserId } from '@/lib/local-user'
import crypto from 'crypto'
import { brainCoreFetch } from '@/lib/brain-core-url'

const MAX_FILE_SIZE = 10 * 1024 * 1024 // 10 MB
const ALLOWED_TYPES = ['text/plain', 'text/markdown', 'application/pdf', 'text/csv', 'application/json']
const ALLOWED_EXTS = ['.txt', '.md', '.pdf', '.csv', '.json', '.docx']

// POST /api/knowledge/upload — 文件上传到知识库
export async function POST(req: NextRequest) {
  try {
    const userId = getLocalUserId()
    const formData = await req.formData()
    const file = formData.get('file') as File | null
    const titleOverride = formData.get('title') as string | null

    if (!file) {
      return NextResponse.json({ success: false, error: '请选择文件' }, { status: 400 })
    }

    if (file.size > MAX_FILE_SIZE) {
      return NextResponse.json({ success: false, error: '文件大小不能超过 10MB' }, { status: 400 })
    }

    // 获取文件扩展名
    const ext = '.' + (file.name.split('.').pop()?.toLowerCase() || '')
    if (!ALLOWED_EXTS.includes(ext)) {
      return NextResponse.json({
        success: false,
        error: `不支持的文件类型: ${ext}，支持: ${ALLOWED_EXTS.join(', ')}`,
      }, { status: 400 })
    }

    // 读取文件内容
    const buffer = Buffer.from(await file.arrayBuffer())

    // Magic bytes 校验（PDF / DOCX）
    if (ext === '.pdf') {
      const header = buffer.subarray(0, 4).toString('ascii')
      if (header !== '%PDF') {
        return NextResponse.json({ success: false, error: '文件内容不是有效的 PDF' }, { status: 400 })
      }
    }
    if (ext === '.docx') {
      // DOCX 是 ZIP 格式，magic bytes: PK\x03\x04
      if (buffer.length < 4 || buffer[0] !== 0x50 || buffer[1] !== 0x4B || buffer[2] !== 0x03 || buffer[3] !== 0x04) {
        return NextResponse.json({ success: false, error: '文件内容不是有效的 DOCX' }, { status: 400 })
      }
    }

    // 提取文本内容
    let textContent: string
    let docType: string

    if (ext === '.pdf' || ext === '.docx') {
      // PDF/DOCX: 发送到 brain-core 文档解析器提取文本
      docType = ext === '.pdf' ? 'pdf' : 'docx'
      try {
        const parseForm = new FormData()
        parseForm.append('file', new Blob([buffer], { type: file.type }), file.name)
        const parseRes = await brainCoreFetch('/api/v1/multimodal/document/parse', {
          method: 'POST',
          body: parseForm,
        })
        const parseData = await parseRes.json() as { success: boolean; text?: string; error?: string }
        if (parseData.success && parseData.text) {
          textContent = parseData.text
        } else {
          textContent = `[${ext.toUpperCase().slice(1)}文件: ${file.name}, ${(file.size / 1024).toFixed(1)}KB — 解析失败: ${parseData.error || '未知错误'}]`
        }
      } catch {
        textContent = `[${ext.toUpperCase().slice(1)}文件: ${file.name}, ${(file.size / 1024).toFixed(1)}KB — brain-core 不可用]`
      }
    } else {
      textContent = buffer.toString('utf-8')
      docType = ext === '.md' ? 'markdown' : ext === '.csv' ? 'csv' : ext === '.json' ? 'json' : 'text'
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

    const docTitle = titleOverride || file.name
    const contentHash = crypto.createHash('sha256').update(buffer).digest('hex')

    // 简单分块
    const chunks = chunkText(textContent, 500)

    // 存储到 MinIO（通过 gateway 代理，如果可用）
    let storageKey = ''
    if (process.env.MINIO_ENDPOINT) {
      try {
        const timestamp = Date.now()
        const hash8 = contentHash.slice(0, 8)
        storageKey = `knowledge/${userId}/${timestamp}-${hash8}${ext}`

        const gatewayUrl = process.env.GATEWAY_URL || 'http://127.0.0.1:3001'
        await fetch(`${gatewayUrl.replace('://localhost:', '://127.0.0.1:').replace('://localhost/', '://127.0.0.1/')}/api/v1/storage/upload`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            key: storageKey,
            data: buffer.toString('base64'),
            contentType: file.type || 'application/octet-stream',
            filename: file.name,
          }),
        })
      } catch (err) {
        console.warn('[MinIO] Upload skipped:', (err as Error).message)
        storageKey = ''
      }
    }

    const doc = await prisma.document.create({
      data: {
        title: docTitle,
        docType,
        content: textContent,
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

    // 通知 brain-core RAG 摄入
    void brainCoreFetch('/api/v1/rag/ingest', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ doc_id: doc.id, title: docTitle, content: textContent, type: docType }),
    }).catch(() => {})

    return NextResponse.json({
      success: true,
      document: {
        id: doc.id,
        title: doc.title,
        docType: doc.docType,
        chunkCount: chunks.length,
        fileSize: file.size,
        storageKey: storageKey || undefined,
      },
    })
  } catch (error) {
    console.error('knowledge file upload failed:', error)
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
  if (current.trim()) chunks.push(current.trim())
  return chunks.length > 0 ? chunks : [text]
}
