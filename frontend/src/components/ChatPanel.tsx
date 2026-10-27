import { useState } from 'react'
import type { FormEvent } from 'react'

import { askQuestion } from '../services/api'
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

function ChatPanel({
  documents,
  subjectId,
  subjectName,
}: ChatPanelProps) {
  const [question, setQuestion] = useState('')
  const [result, setResult] = useState<ChatResponse | null>(null)
  const [isAsking, setIsAsking] = useState(false)
  const [error, setError] = useState<string | null>(null)

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
          : 'Không thể nhận câu trả lời',
      )
    } finally {
      setIsAsking(false)
    }
  }

  function getDocumentName(documentId: string, fallback: string) {
    return documents.find(
      (document) => document.document_id === documentId,
    )?.filename ?? fallback
  }

  return (
    <section className="chat-workspace" aria-label="Trò chuyện với tài liệu">
      <div className="chat-main-column">
        <div className="chat-scope-banner">
          <span className="chat-context-icon" aria-hidden="true">S</span>
          <div>
            <span>Phạm vi truy xuất</span>
            <strong>{subjectName || 'Chưa chọn môn học'}</strong>
            <p>{documents.length} nguồn đang hoạt động trong phạm vi này.</p>
          </div>
        </div>

        <div className="chat-panel">
          <form onSubmit={handleSubmit}>
            <label htmlFor="chat-question">Câu hỏi của bạn</label>
            <textarea
              id="chat-question"
              value={question}
              onChange={(event) => setQuestion(event.target.value)}
              maxLength={2000}
              rows={5}
              placeholder="Đặt câu hỏi dựa trên các nguồn đã lập chỉ mục..."
            />
            <div className="chat-submit-row">
              <span>Câu trả lời sẽ giữ trích dẫn từ dữ liệu nguồn.</span>
              <button type="submit" disabled={
                isAsking
                || !question.trim()
                || !subjectId
              }>
                {isAsking ? 'Đang truy xuất...' : 'Tìm câu trả lời'}
              </button>
            </div>
          </form>

          {isAsking && (
            <p className="chat-status" role="status">
              Đang truy xuất evidence trong {subjectName}...
            </p>
          )}
          {error && <p className="chat-error" role="alert">{error}</p>}

          {result ? (
            <div className="chat-result">
              <span className="panel-kicker">Câu trả lời có nguồn</span>
              <h2>Câu trả lời</h2>
              <div className="chat-answer">
                <ReactMarkdown>{result.answer}</ReactMarkdown>
              </div>
            </div>
          ) : (
            <div className="chat-empty-answer">
              <strong>Sẵn sàng truy vấn kho tri thức</strong>
              <span>Câu trả lời sẽ xuất hiện tại đây và giữ liên kết tới nguồn.</span>
            </div>
          )}
        </div>
      </div>

      <aside className="evidence-panel" aria-label="Evidence">
        <div className="evidence-heading">
          <div>
            <span className="panel-kicker">Truy vết nguồn</span>
            <h2>Nguồn đối chiếu</h2>
          </div>
          <span className="evidence-count">{result?.sources.length ?? 0}</span>
        </div>

        {result && result.sources.length > 0 ? (
          <ol className="evidence-list">
            {result.sources.map((source) => (
              <li key={source.chunk_id}>
                <span className="evidence-index">{source.chunk_index + 1}</span>
                <div>
                  <strong>
                    {getDocumentName(source.document_id, source.source)}
                  </strong>
                  <span>{formatSourceLocation(source)}</span>
                  <code>{source.document_id}</code>
                </div>
              </li>
            ))}
          </ol>
        ) : (
          <div className="evidence-empty">
            <span className="evidence-empty-mark" aria-hidden="true">↳</span>
            <strong>Chưa có nguồn đối chiếu</strong>
            <p>Nguồn và vị trí trích dẫn sẽ xuất hiện sau khi có câu trả lời.</p>
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
    return `trang ${source.page}`
  }

  if (source.line_range !== null) {
    const [start, end] = source.line_range

    return start === end
      ? `dòng ${start}`
      : `dòng ${start}–${end}`
  }

  if (source.paragraph_range !== null) {
    const [start, end] = source.paragraph_range

    return start === end
      ? `đoạn ${start}`
      : `đoạn ${start}–${end}`
  }

  return 'vị trí không xác định'
}

export default ChatPanel
