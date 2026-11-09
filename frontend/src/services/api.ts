import type {
  ActivatePolicyVersionInput,
  DeleteDocumentResult,
  DocumentRecord,
  UploadDocumentInput,
  UploadDocumentResult,
} from '../types/document'

import type {
  DeleteSubjectResult,
  RestoreSubjectResult,
  SubjectRecord,
  SubjectTrashRecord,
} from '../types/subject'

import type { ChatResponse } from '../types/chat'
import type {
  AttemptAnswerSubmitInput,
  AttemptResult,
  AttemptStartResponse,
  QuizCreateResponse,
  QuizOverview,
  QuizPublic,
  QuizPublishResponse,
  QuizQuestionCreateInput,
  QuizQuestionPublic,
  QuizSummary,
} from '../types/quiz'

const API_BASE_URL =
  import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

async function getErrorMessage(
  response: Response,
  fallback: string,
): Promise<string> {
  try {
    const payload: unknown = await response.json()

    if (
      typeof payload !== 'object'
      || payload === null
      || !('detail' in payload)
    ) {
      return fallback
    }

    const detail: unknown = payload.detail

    if (typeof detail === 'string') {
      return detail
    }

    if (
      typeof detail !== 'object'
      || detail === null
      || !('code' in detail)
    ) {
      return fallback
    }

    if (detail.code !== 'DOCUMENT_ALREADY_EXISTS') {
      return fallback
    }

    const documentStatus: unknown =
      'status' in detail
        ? detail.status
        : undefined

    if (documentStatus === 'INDEXED') {
      return 'Văn bản chính sách này đã được tải lên và lập chỉ mục'
    }

    return 'Văn bản chính sách này đã được tải lên trước đó'
  } catch {
    return fallback
  }
}

export async function getDocuments(): Promise<DocumentRecord[]> {
  const response = await fetch(
    `${API_BASE_URL}/documents/`,
  )

  if (!response.ok) {
    throw new Error(
      await getErrorMessage(
        response,
        'Không thể tải danh sách văn bản chính sách',
      ),
    )
  }

  return response.json()
}

export async function activatePolicyVersion(
  input: ActivatePolicyVersionInput,
): Promise<DocumentRecord> {
  const response = await fetch(
    `${API_BASE_URL}/documents/${encodeURIComponent(input.documentId)}/activate`,
    {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        effective_from: input.effectiveFrom,
        supersedes_document_id: input.supersedesDocumentId || null,
      }),
    },
  )

  if (!response.ok) {
    throw new Error(
      await getErrorMessage(
        response,
        'Không thể kích hoạt phiên bản chính sách',
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
        'Không thể tải danh sách chuyên mục onboarding',
      ),
    )
  }

  return response.json()
}

export async function getSubjectTrash(): Promise<
  SubjectTrashRecord[]
> {
  const response = await fetch(
    `${API_BASE_URL}/subjects/trash`,
  )

  if (!response.ok) {
    throw new Error(
      await getErrorMessage(
        response,
        'Không thể tải danh sách chuyên mục đã lưu trữ',
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
        'Không thể tạo chuyên mục onboarding',
      ),
    )
  }

  return response.json()
}

export async function deleteSubject(
  subjectId: string,
): Promise<DeleteSubjectResult> {
  const response = await fetch(
    `${API_BASE_URL}/subjects/${encodeURIComponent(subjectId)}`,
    {
      method: 'DELETE',
    },
  )

  if (!response.ok) {
    throw new Error(
      await getErrorMessage(
        response,
        'Không thể lưu trữ chuyên mục onboarding',
      ),
    )
  }

  return response.json()
}

export async function restoreSubject(
  subjectId: string,
): Promise<RestoreSubjectResult> {
  const response = await fetch(
    `${API_BASE_URL}/subjects/${encodeURIComponent(subjectId)}/restore`,
    {
      method: 'POST',
    },
  )

  if (!response.ok) {
    throw new Error(
      await getErrorMessage(
        response,
        'Không thể khôi phục chuyên mục onboarding',
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
        'Không thể tải văn bản chính sách lên',
      ),
    )
  }

  const result: UploadDocumentResult = await response.json()

  if (input.activateImmediately && input.effectiveDate) {
    try {
      await activatePolicyVersion({
        documentId: result.document_id,
        effectiveFrom: input.effectiveDate,
        supersedesDocumentId: input.supersedesDocumentId ?? null,
      })
    } catch {
      // If activation fails, document remains INDEXED and can be activated from the table
    }
  }

  return result
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
        'Không thể xóa văn bản chính sách',
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
        'Không thể nhận câu trả lời từ kho chính sách',
      ),
    )
  }

  return response.json()
}

export async function getPublishedQuizzes(
  subjectId: string,
): Promise<QuizSummary[]> {
  const response = await fetch(
    `${API_BASE_URL}/quizzes/?subject_id=${encodeURIComponent(subjectId)}`,
  )

  if (!response.ok) {
    throw new Error(
      await getErrorMessage(
        response,
        'Không thể tải danh sách đề kiểm tra onboarding',
      ),
    )
  }

  return response.json()
}

export async function getPublishedQuizDetail(
  quizId: string,
): Promise<QuizPublic> {
  const response = await fetch(
    `${API_BASE_URL}/quizzes/${encodeURIComponent(quizId)}`,
  )

  if (!response.ok) {
    throw new Error(
      await getErrorMessage(
        response,
        'Không thể tải nội dung bài kiểm tra',
      ),
    )
  }

  return response.json()
}

export async function createDraftQuiz(
  subjectId: string,
  title: string,
): Promise<QuizCreateResponse> {
  const response = await fetch(
    `${API_BASE_URL}/quizzes/`,
    {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        subject_id: subjectId,
        title,
      }),
    },
  )

  if (!response.ok) {
    throw new Error(
      await getErrorMessage(
        response,
        'Không thể khởi tạo đề kiểm tra nháp',
      ),
    )
  }

  return response.json()
}

export async function addQuestionToQuiz(
  quizId: string,
  payload: QuizQuestionCreateInput,
): Promise<QuizQuestionPublic> {
  const response = await fetch(
    `${API_BASE_URL}/quizzes/${encodeURIComponent(quizId)}/questions`,
    {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(payload),
    },
  )

  if (!response.ok) {
    throw new Error(
      await getErrorMessage(
        response,
        'Không thể thêm câu hỏi vào đề kiểm tra',
      ),
    )
  }

  return response.json()
}

export async function publishDraftQuiz(
  quizId: string,
): Promise<QuizPublishResponse> {
  const response = await fetch(
    `${API_BASE_URL}/quizzes/${encodeURIComponent(quizId)}/publish`,
    {
      method: 'POST',
    },
  )

  if (!response.ok) {
    throw new Error(
      await getErrorMessage(
        response,
        'Không thể phê duyệt và xuất bản đề kiểm tra',
      ),
    )
  }

  return response.json()
}

export async function startQuizAttempt(
  quizId: string,
  employeeId: string,
): Promise<AttemptStartResponse> {
  const response = await fetch(
    `${API_BASE_URL}/quizzes/${encodeURIComponent(quizId)}/attempts`,
    {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        employee_id: employeeId,
      }),
    },
  )

  if (!response.ok) {
    throw new Error(
      await getErrorMessage(
        response,
        'Không thể bắt đầu lượt làm bài kiểm tra',
      ),
    )
  }

  return response.json()
}

export async function submitQuizAttempt(
  attemptId: string,
  answers: AttemptAnswerSubmitInput[],
): Promise<AttemptResult> {
  const response = await fetch(
    `${API_BASE_URL}/quizzes/attempts/${encodeURIComponent(attemptId)}/submit`,
    {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ answers }),
    },
  )

  if (!response.ok) {
    throw new Error(
      await getErrorMessage(
        response,
        'Không thể nộp và chấm điểm bài kiểm tra',
      ),
    )
  }

  return response.json()
}

export async function getQuizOverview(
  quizId: string,
): Promise<QuizOverview> {
  const response = await fetch(
    `${API_BASE_URL}/quizzes/${encodeURIComponent(quizId)}/overview`,
  )

  if (!response.ok) {
    throw new Error(
      await getErrorMessage(
        response,
        'Không thể tải thống kê tổng quan của đề kiểm tra',
      ),
    )
  }

  return response.json()
}

export async function getQuizAttemptResults(
  quizId: string,
): Promise<AttemptResult[]> {
  const response = await fetch(
    `${API_BASE_URL}/quizzes/${encodeURIComponent(quizId)}/attempts`,
  )

  if (!response.ok) {
    throw new Error(
      await getErrorMessage(
        response,
        'Không thể tải lịch sử lượt làm bài từ máy chủ',
      ),
    )
  }

  return response.json()
}
