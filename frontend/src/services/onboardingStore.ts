import type { DocumentRecord } from '../types/document'
import type { AttemptResult } from '../types/quiz'

const ATTEMPTS_HISTORY_KEY = 'cm_onboarding_graded_attempts_v1'
const DRAFT_QUIZ_CACHE_KEY = 'cm_onboarding_draft_quizzes_v1'

export interface StoredAttemptHistoryItem extends AttemptResult {
  quiz_title: string
  subject_id: string
  subject_name: string
  completed_at: string
}

export interface DraftQuizSession {
  quiz_id: string
  subject_id: string
  title: string
  status: 'DRAFT' | 'PUBLISHED'
  questions: {
    question_id: string
    prompt: string
    options: { option_id: string; text: string; position: number }[]
    source_document_id: string | null
    source_document_version: string | null
  }[]
}

function readJsonStorage<T>(key: string, fallback: T): T {
  try {
    const raw = window.localStorage.getItem(key)
    if (!raw) return fallback
    return JSON.parse(raw) as T
  } catch {
    return fallback
  }
}

function writeJsonStorage<T>(key: string, value: T): void {
  try {
    window.localStorage.setItem(key, JSON.stringify(value))
  } catch {
    // Ignore storage quota errors
  }
}

export function isDocumentApplicableNow(document: DocumentRecord): boolean {
  if (document.is_current !== undefined) {
    return Boolean(document.is_current)
  }

  if (document.status !== 'INDEXED') return false
  const effectiveFrom = document.effective_from ?? document.effective_date
  if (!effectiveFrom) return false

  const today = new Intl.DateTimeFormat('en-CA').format(new Date())
  if (effectiveFrom > today) return false
  if (document.effective_until && document.effective_until <= today) {
    return false
  }

  return true
}

export function getSavedDraftQuizzes(subjectId: string): DraftQuizSession[] {
  const all = readJsonStorage<DraftQuizSession[]>(DRAFT_QUIZ_CACHE_KEY, [])
  return all.filter((q) => q.subject_id === subjectId && q.status === 'DRAFT')
}

export function saveDraftQuizSession(session: DraftQuizSession): void {
  const all = readJsonStorage<DraftQuizSession[]>(DRAFT_QUIZ_CACHE_KEY, [])
  const filtered = all.filter((q) => q.quiz_id !== session.quiz_id)
  writeJsonStorage(DRAFT_QUIZ_CACHE_KEY, [session, ...filtered])
}

export function removeDraftQuizSession(quizId: string): void {
  const all = readJsonStorage<DraftQuizSession[]>(DRAFT_QUIZ_CACHE_KEY, [])
  writeJsonStorage(
    DRAFT_QUIZ_CACHE_KEY,
    all.filter((q) => q.quiz_id !== quizId),
  )
}

export function recordCompletedAttempt(item: StoredAttemptHistoryItem): void {
  const current = readJsonStorage<StoredAttemptHistoryItem[]>(
    ATTEMPTS_HISTORY_KEY,
    [],
  )
  const filtered = current.filter((a) => a.attempt_id !== item.attempt_id)
  writeJsonStorage(ATTEMPTS_HISTORY_KEY, [item, ...filtered])
}

export function getRecordedAttempts(): StoredAttemptHistoryItem[] {
  return readJsonStorage<StoredAttemptHistoryItem[]>(ATTEMPTS_HISTORY_KEY, [])
}
