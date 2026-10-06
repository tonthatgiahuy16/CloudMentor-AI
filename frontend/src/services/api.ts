import type {
  DeleteDocumentResult,
  DocumentRecord,
  UploadDocumentInput,
  UploadDocumentResult,
} from '../types/document'

import type { SubjectRecord } from '../types/subject'

import type { ChatResponse } from '../types/chat'

const API_BASE_URL =
  import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

async function getErrorMessage(
  response: Response,
  fallback: string,
): Promise<string> {
  try {
    const payload: unknown = await response.json()

    if (
      typeof payload === 'object'
      && payload !== null
      && 'detail' in payload
      && typeof payload.detail === 'string'
    ) {
      return payload.detail
    }
  } catch {
    // Response did not contain JSON.
  }

  return fallback
}

export async function getDocuments(): Promise<DocumentRecord[]> {
  const response = await fetch(
    `${API_BASE_URL}/documents/`,
  )

  if (!response.ok) {
    throw new Error(
      await getErrorMessage(
        response,
        'Không thể tải danh sách tài liệu',
      ),
    )
  }

  return response.json()
}

export async function getSubjects(): Promise<SubjectRecord[]> {
  const response = await fetch(
    `${API_BASE_URL}/subjects/`,
  )

  if (!response.ok) {
    throw new Error(
      await getErrorMessage(
        response,
        'Không thể tải danh sách môn học',
      ),
    )
  }

  return response.json()
}

export async function createSubject(
  name: string,
): Promise<SubjectRecord> {
  const response = await fetch(
    `${API_BASE_URL}/subjects/`,
    {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ name }),
    },
  )

  if (!response.ok) {
    throw new Error(
      await getErrorMessage(
        response,
        'Không thể tạo môn học',
      ),
    )
  }

  return response.json()
}

export async function uploadDocument(
  input: UploadDocumentInput,
): Promise<UploadDocumentResult> {
  const formData = new FormData()

  formData.append('file', input.file)
  formData.append('subject_id', input.subjectId)

  if (input.chapter !== null) {
    formData.append('chapter', String(input.chapter))
  }

  const response = await fetch(
    `${API_BASE_URL}/upload/`,
    {
      method: 'POST',
      body: formData,
    },
  )

  if (!response.ok) {
    throw new Error(
      await getErrorMessage(
        response,
        'Không thể tải tài liệu lên',
      ),
    )
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
    throw new Error(
      await getErrorMessage(
        response,
        'Không thể xóa tài liệu',
      ),
    )
  }

  return response.json()

}

export async function askQuestion(
  question: string,
  subjectId: string,
): Promise<ChatResponse> {
  const response = await fetch(
    `${API_BASE_URL}/chat/`,
    {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        question,
        subject_id: subjectId,
      }),
    },
  )

  if (!response.ok) {
    throw new Error(
      await getErrorMessage(
        response,
        'Không thể nhận câu trả lời',
      ),
    )
  }

  return response.json()
}
