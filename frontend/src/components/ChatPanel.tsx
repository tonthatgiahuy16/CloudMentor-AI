import { useState } from 'react'
import type { FormEvent } from 'react'

import { askQuestion } from '../services/api'
import { isDocumentApplicableNow } from '../services/onboardingStore'
import type {
  ChatResponse,
  ChatSource,
} from '../types/chat'
import type { DocumentRecord } from '../types/document'

import ReactMarkdown from 'react-markdown'

interface ChatPanelProps {
  documents: DocumentRecord[]
  subjectId: string
  subjectName: string
}

const SAMPLE_POLICY_QUESTIONS = [
  'Quy định về thời gian làm việc và nghỉ phép năm của nhân viên mới?',
  'Nhân viên mới cần tuân thủ những nguyên tắc bảo mật cơ bản nào?',
  'Quy trình liên hệ và xin hỗ trợ kỹ thuật / nhân sự khi gặp sự cố?',
] as const

function ChatPanel({
  documents,
  subjectId,
  subjectName,
}: ChatPanelProps) {
  const [question, setQuestion] = useState('')
  const [result, setResult] = useState<ChatResponse | null>(null)
  const [isAsking, setIsAsking] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [copiedId, setCopiedId] = useState<string | null>(null)

  const applicableDocs = documents.filter((d) => isDocumentApplicableNow(d))

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()

    const text = question.trim()
    if (!text || !subjectId || isAsking) return

    setIsAsking(true)
    setError(null)
    setResult(null)

    try {
      setResult(await askQuestion(text, subjectId))
    } catch (requestError) {
      setError(
        requestError instanceof Error
          ? requestError.message
          : 'Không thể nhận câu trả lời từ kho chính sách',
      )
    } finally {
      setIsAsking(false)
    }
  }

  function getDocumentRecord(documentId: string): DocumentRecord | undefined {
    return documents.find(
      (document) => document.document_id === documentId,
    )
  }

  function handleCopyId(id: string) {
    void navigator.clipboard?.writeText(id)
    setCopiedId(id)
    window.setTimeout(() => setCopiedId(null), 1600)
  }

  return (
    <section className="chat-workspace" aria-label="Tra cứu chính sách có dẫn nguồn">
      <div className="chat-main-column">
        <div className="chat-scope-banner">
          <span className="chat-context-icon" aria-hidden="true">P</span>
          <div className="chat-scope-copy">
            <span>Phạm vi chính sách hiện hành · PostgreSQL Allow-list</span>
            <strong>{subjectName || 'Chưa chọn chuyên mục onboarding'}</strong>
            <p>
              {applicableDocs.length} văn bản đang áp dụng trên tổng số {documents.length} bản ghi trong chuyên mục này.
            </p>
          </div>
          <span className="scope-guard-badge">Fail-closed</span>
        </div>

        <div className="chat-panel">
          <div className="quick-prompts" aria-label="Gợi ý câu hỏi onboarding">
            <span className="quick-prompts-label">Gợi ý tra cứu nhanh:</span>
            <div className="quick-prompts-list">
              {SAMPLE_POLICY_QUESTIONS.map((sample) => (
                <button
                  key={sample}
                  type="button"
                  className="prompt-pill"
                  onClick={() => setQuestion(sample)}
                >
                  {sample}
                </button>
              ))}
            </div>
          </div>

          <form onSubmit={handleSubmit}>
            <label htmlFor="chat-question">Câu hỏi của nhân viên mới</label>
            <textarea
              id="chat-question"
              value={question}
              onChange={(event) => setQuestion(event.target.value)}
              maxLength={2000}
              rows={4}
              placeholder="Đặt câu hỏi bằng ngôn ngữ tự nhiên về nội quy, nghỉ phép, bảo mật hoặc quy trình hỗ trợ..."
            />
            <div className="chat-submit-row">
              <span>
                Chỉ trả lời dựa trên văn bản chính sách đang có hiệu lực và đính kèm vị trí nguồn.
              </span>
              <button
                type="submit"
                disabled={
                  isAsking
                  || !question.trim()
                  || !subjectId
                }
              >
                {isAsking ? 'Đang đối chiếu chính sách...' : 'Tra cứu chính sách'}
              </button>
            </div>
          </form>

          {isAsking && (
            <p className="chat-status" role="status">
              Đang xác định văn bản áp dụng và trích xuất dẫn chứng trong {subjectName}...
            </p>
          )}
          {error && <p className="chat-error" role="alert">{error}</p>}

          {result ? (
            <div className="chat-result">
              <div className="chat-result-header">
                <div>
                  <span className="panel-kicker">Phản hồi từ chính sách hiện hành</span>
                  <h2>Nội dung giải đáp</h2>
                </div>
                <span className="citation-summary-badge">
                  {result.sources.length} đoạn trích dẫn
                </span>
              </div>
              <div className="chat-answer">
                <ReactMarkdown>{result.answer}</ReactMarkdown>
              </div>
            </div>
          ) : (
            <div className="chat-empty-answer">
              <strong>Sẵn sàng giải đáp chính sách Onboarding</strong>
              <span>
                Mọi câu trả lời đều kèm tên tài liệu và vị trí trang / đoạn văn để nhân viên tự kiểm chứng.
              </span>
            </div>
          )}
        </div>
      </div>

      <aside className="evidence-panel" aria-label="Nguồn đối chiếu chính sách">
        <div className="evidence-heading">
          <div>
            <span className="panel-kicker">Truy vết nguồn (Lineage)</span>
            <h2>Văn bản & vị trí nguồn</h2>
          </div>
          <span className="evidence-count">{result?.sources.length ?? 0}</span>
        </div>

        {result && result.sources.length > 0 ? (
          <ol className="evidence-list">
            {result.sources.map((source) => {
              const docRecord = getDocumentRecord(source.document_id)
              const docTitle = docRecord?.filename ?? source.source

              return (
                <li key={source.chunk_id}>
                  <span className="evidence-index">{source.chunk_index + 1}</span>
                  <div>
                    <strong>{docTitle}</strong>
                    <div className="evidence-meta-row">
                      <span className="evidence-location-tag">
                        {formatSourceLocation(source)}
                      </span>
                      {docRecord?.effective_date && (
                        <span className="evidence-date-tag">
                          Hiệu lực: {docRecord.effective_date}
                        </span>
                      )}
                    </div>
                    <button
                      type="button"
                      className="evidence-id-button"
                      title="Sao chép mã định danh tài liệu"
                      onClick={() => handleCopyId(source.document_id)}
                    >
                      <code>{source.document_id}</code>
                      <span>{copiedId === source.document_id ? 'Đã chép' : 'ID'}</span>
                    </button>
                  </div>
                </li>
              )
            })}
          </ol>
        ) : (
          <div className="evidence-empty">
            <span className="evidence-empty-mark" aria-hidden="true">↳</span>
            <strong>Chưa có nguồn đối chiếu</strong>
            <p>
              Tên văn bản nội quy, ngày hiệu lực và tọa độ trang / dòng / đoạn sẽ hiển thị tại đây.
            </p>
          </div>
        )}
      </aside>
    </section>
  )
}

function formatSourceLocation(
  source: ChatSource,
): string {
  if (source.page !== null) {
    return `Trang ${source.page}`
  }

  if (source.line_range !== null) {
    const [start, end] = source.line_range

    return start === end
      ? `Dòng ${start}`
      : `Dòng ${start}–${end}`
  }

  if (source.paragraph_range !== null) {
    const [start, end] = source.paragraph_range

    return start === end
      ? `Đoạn ${start}`
      : `Đoạn ${start}–${end}`
  }

  return 'Vị trí nguồn xác thực'
}

export default ChatPanel
