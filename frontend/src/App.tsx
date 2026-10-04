import { useEffect, useState } from 'react'

import UploadPanel from './components/UploadPanel'

import {
  deleteDocument,
  getDocuments,
} from './services/api'
import type {
  DocumentRecord,
  DocumentStatus,
} from './types/document'
import './App.css'

const STATUS_LABELS: Record<DocumentStatus, string> = {
  UPLOADED: 'Đã tải lên',
  PROCESSING: 'Đang xử lý',
  INDEXED: 'Sẵn sàng',
  FAILED: 'Thất bại',
  DELETED: 'Đã xóa',
}

function formatDate(value: string): string {
  return new Intl.DateTimeFormat('vi-VN', {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(new Date(value))
}

function App() {
  const [documents, setDocuments] = useState<DocumentRecord[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [deletingId, setDeletingId] = useState<string | null>(null)

  async function refreshDocuments() {
    setIsLoading(true)
    setError(null)

    try {
      setDocuments(await getDocuments())
    } catch (requestError) {
      setError(
        requestError instanceof Error
          ? requestError.message
          : 'Đã xảy ra lỗi không xác định',
      )
    } finally {
      setIsLoading(false)
    }
  }

  useEffect(() => {
    let isActive = true

    async function loadDocuments() {
      try {
        const result = await getDocuments()

        if (isActive) {
          setDocuments(result)
        }
      } catch (requestError) {
        if (isActive) {
          setError(
            requestError instanceof Error
              ? requestError.message
              : 'Đã xảy ra lỗi không xác định',
          )
        }
      } finally {
        if (isActive) {
          setIsLoading(false)
        }
      }
    }

    void loadDocuments()

    return () => {
      isActive = false
    }
  }, [])

  async function handleDelete(document: DocumentRecord) {
    const confirmed = window.confirm(
      `Xóa tài liệu "${document.filename}"?`,
    )

    if (!confirmed) {
      return
    }

    setDeletingId(document.document_id)
    setError(null)

    try {
      await deleteDocument(document.document_id)

      setDocuments((currentDocuments) =>
        currentDocuments.filter(
          (item) => item.document_id !== document.document_id,
        ),
      )
    } catch (requestError) {
      setError(
        requestError instanceof Error
          ? requestError.message
          : 'Đã xảy ra lỗi không xác định',
      )
    } finally {
      setDeletingId(null)
    }
  }

  const indexedCount = documents.filter(
    (document) => document.status === 'INDEXED',
  ).length

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <span className="brand-mark">CM</span>
          <div>
            <strong>CloudMentor AI</strong>
            <span>Learning Data Platform</span>
          </div>
        </div>

        <nav aria-label="Điều hướng chính">
          <a className="nav-item active" href="#documents">
            Tài liệu
          </a>
          <span className="nav-item disabled">Trò chuyện</span>
          <span className="nav-item disabled">Quiz</span>
          <span className="nav-item disabled">Phân tích</span>
        </nav>
      </aside>

      <main className="main-content">
        <header className="page-header">
          <div>
            <span className="eyebrow">Knowledge workspace</span>
            <h1>Thư viện tài liệu</h1>
            <p>
              Quản lý nguồn học liệu và theo dõi trạng thái xử lý.
            </p>
          </div>

          <button
            className="secondary-button"
            type="button"
            onClick={() => void refreshDocuments()}
            disabled={isLoading}
          >
            {isLoading ? 'Đang tải...' : 'Tải lại'}
          </button>
        </header>
        <UploadPanel onUploaded={refreshDocuments} />

        <section className="summary-grid" aria-label="Tổng quan">
          <article className="summary-card">
            <span>Tổng tài liệu</span>
            <strong>{documents.length}</strong>
          </article>

          <article className="summary-card">
            <span>Sẵn sàng tìm kiếm</span>
            <strong>{indexedCount}</strong>
          </article>

          <article className="summary-card">
            <span>Đang xử lý</span>
            <strong>
              {
                documents.filter(
                  (document) =>
                    document.status === 'PROCESSING'
                    || document.status === 'UPLOADED',
                ).length
              }
            </strong>
          </article>
        </section>

        {error && (
          <div className="error-banner" role="alert">
            <span>{error}</span>
            <button
              type="button"
              onClick={() => void refreshDocuments()}
            >
              Thử lại
            </button>
          </div>
        )}

        <section className="document-panel" id="documents">
          <div className="panel-heading">
            <div>
              <h2>Documents</h2>
              <p>Tài liệu chưa bị xóa khỏi hệ thống.</p>
            </div>
          </div>

          {isLoading ? (
            <p className="state-message">Đang tải tài liệu...</p>
          ) : documents.length === 0 ? (
            <p className="state-message">
              Chưa có tài liệu nào. Hãy tải PDF đầu tiên.
            </p>
          ) : (
            <div className="table-wrapper">
              <table>
                <thead>
                  <tr>
                    <th>Tên tài liệu</th>
                    <th>Chapter</th>
                    <th>Trạng thái</th>
                    <th>Ngày tải lên</th>
                    <th>
                      <span className="sr-only">Thao tác</span>
                    </th>
                  </tr>
                </thead>

                <tbody>
                  {documents.map((document) => (
                    <tr key={document.document_id}>
                      <td>
                        <strong>{document.filename}</strong>
                        <span className="document-type">
                          {document.file_type.toUpperCase()}
                        </span>
                      </td>
                      <td>{document.chapter ?? '—'}</td>
                      <td>
                        <span
                          className={`status status-${document.status.toLowerCase()}`}
                        >
                          {STATUS_LABELS[document.status]}
                        </span>
                      </td>
                      <td>{formatDate(document.uploaded_at)}</td>
                      <td className="actions">
                        <button
                          className="danger-button"
                          type="button"
                          disabled={deletingId === document.document_id}
                          onClick={() => void handleDelete(document)}
                        >
                          {deletingId === document.document_id
                            ? 'Đang xóa...'
                            : 'Xóa'}
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>
      </main>
    </div>
  )
}

export default App