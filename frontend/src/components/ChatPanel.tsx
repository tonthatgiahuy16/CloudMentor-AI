import { useEffect, useState } from 'react'
import type { FormEvent } from 'react'

import {
  askQuestion,
  getSubjects,
} from '../services/api'
import type { ChatResponse } from '../types/chat'
import type { DocumentRecord } from '../types/document'
import type { SubjectRecord } from '../types/subject'

import ReactMarkdown from 'react-markdown'

interface ChatPanelProps {
  documents: DocumentRecord[]
}

function ChatPanel({ documents }: ChatPanelProps) {
  const [question, setQuestion] = useState('')
  const [subjects, setSubjects] = useState<SubjectRecord[]>([])
  const [subjectId, setSubjectId] = useState('')
  const [isLoadingSubjects, setIsLoadingSubjects] = useState(true)
  const [result, setResult] = useState<ChatResponse | null>(null)
  const [isAsking, setIsAsking] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
  let isActive = true

  async function loadSubjects() {
    try {
      const result = await getSubjects()

      if (isActive) {
        setSubjects(result)
        setSubjectId(result[0]?.subject_id ?? '')
      }
    } catch (requestError) {
      if (isActive) {
        setError(
          requestError instanceof Error
            ? requestError.message
            : 'Không thể tải danh sách môn học',
        )
      }
    } finally {
      if (isActive) {
        setIsLoadingSubjects(false)
      }
    }
  }

  void loadSubjects()

  return () => {
    isActive = false
  }
}, [])

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()

    const text = question.trim()
    if (!text || !subjectId || isAsking) return

    setIsAsking(true)
    setError(null)
    setResult(null)

    try {
      setResult(await askQuestion(text, subjectId,))
    } catch (requestError) {
      setError(
        requestError instanceof Error
          ? requestError.message
          : 'Không thể nhận câu trả lời',
      )
    } finally {
      setIsAsking(false)
    }
  }

  function handleSubjectChange(nextSubjectId: string) {
    setSubjectId(nextSubjectId)
    setResult(null)
    setError(null)
  }

  const selectedSubject = subjects.find(
    (subject) => subject.subject_id === subjectId,
  )

  function getDocumentName(documentId: string, fallback: string) {
    return documents.find(
      (document) => document.document_id === documentId,
    )?.filename ?? fallback
  }

  return (
    <section className="chat-panel" aria-label="Trò chuyện với tài liệu">
      <form onSubmit={handleSubmit}>
        <div className="chat-context">
          <div className="chat-context-copy">
            <span className="chat-context-icon" aria-hidden="true">M</span>
            <div>
              <label htmlFor="chat-subject">Môn học đang hỏi</label>
              <p>Chỉ tìm câu trả lời trong tài liệu của môn đã chọn.</p>
            </div>
          </div>

          <div className="chat-select-wrap">
            <select
              id="chat-subject"
              value={subjectId}
              onChange={(event) => handleSubjectChange(event.target.value)}
              disabled={isLoadingSubjects || subjects.length === 0}
              aria-label="Chọn môn học để tìm kiếm"
            >
              {subjects.length === 0 ? (
                <option value="">
                  {isLoadingSubjects
                    ? 'Đang tải môn học...'
                    : 'Chưa có môn học'}
                </option>
              ) : (
                subjects.map((subject) => (
                  <option
                    key={subject.subject_id}
                    value={subject.subject_id}
                  >
                    {subject.name}
                  </option>
                ))
              )}
            </select>
            <span className="chat-select-arrow" aria-hidden="true">⌄</span>
          </div>
        </div>

        {selectedSubject && (
          <p className="chat-scope-note">
            Phạm vi hiện tại: <strong>{selectedSubject.name}</strong>
          </p>
        )}

        <label htmlFor="chat-question">Câu hỏi của bạn</label>
        <textarea
          id="chat-question"
          value={question}
          onChange={(event) => setQuestion(event.target.value)}
          maxLength={2000}
          rows={4}
          placeholder="Ví dụ: Cloud computing là gì?"
        />
        <button type="submit" disabled={
          isAsking
          || !question.trim()
          || !subjectId
          || isLoadingSubjects
        }>
          {isAsking ? 'Đang tìm câu trả lời...' : 'Gửi câu hỏi'}
        </button>
      </form>

      {isAsking && (
        <p className="chat-status" role="status">
          Đang tìm trong tài liệu...
        </p>
      )}
      {error && <p role="alert">{error}</p>}

      {result && (
        <div className="chat-result">
          <h2>Câu trả lời</h2>
          <div className="chat-answer">
            <ReactMarkdown>{result.answer}</ReactMarkdown>
          </div>

          {result.sources.length > 0 && (
            <div className="chat-sources">
              <h3>Nguồn tham khảo</h3>
              <ul>
                {result.sources.map((source) => (
                  <li key={source.chunk_id}>
                    {getDocumentName(
                      source.document_id,
                      source.source,
                    )} — trang {source.page}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </section>
  )
}

export default ChatPanel
