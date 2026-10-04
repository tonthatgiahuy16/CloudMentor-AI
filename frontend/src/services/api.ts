import type {
  DeleteDocumentResult,
  DocumentRecord,
} from '../types/document'

const API_BASE_URL =
  import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

export async function getDocuments(): Promise<DocumentRecord[]> {
  const response = await fetch(
    `${API_BASE_URL}/documents/`,
  )

  if (!response.ok) {
    throw new Error('Không thể tải danh sách tài liệu')
  }

  return response.json()
}

export async function deleteDocument(
  documentId: string,
): Promise<DeleteDocumentResult> {
  const response = await fetch(
    `${API_BASE_URL}/documents/${encodeURIComponent(documentId)}`,
    {
      method: 'DELETE',
    },
  )

  if (!response.ok) {
    throw new Error('Không thể xóa tài liệu')
  }

  return response.json()
}