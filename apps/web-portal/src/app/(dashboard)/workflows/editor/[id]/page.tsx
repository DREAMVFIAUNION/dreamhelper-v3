'use client';

import { useParams, redirect } from 'next/navigation';

/**
 * 旧 iframe 编辑器已弃用 — 重定向到原生 React Flow 编辑器
 */
export default function LegacyEditorRedirect() {
  const params = useParams();
  const workflowId = params.id as string;
  redirect(`/workflows/${workflowId}`);
}
