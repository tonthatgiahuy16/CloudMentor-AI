import { useEffect, useMemo, useState } from 'react'

import ChatPanel from './components/ChatPanel'
import SubjectLifecyclePanel from './components/SubjectLifecyclePanel'
import UploadPanel from './components/UploadPanel'
import {
  deleteDocument,
  getDocuments,
  getSubjects,
} from './services/api'
import type {
  DocumentRecord,
  DocumentStatus,
} from './types/document'
import type { SubjectRecord } from './types/subject'
import './WorkspaceApp.css'

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

type ActivePage = 'library' | 'chat'
type LibraryView = 'sources' | 'lifecycle'

function NavigationIcon({ type }: { type: ActivePage }) {
  if (type === 'library') {
    return (
      <svg viewBox="0 0 24 24" aria-hidden="true">
        <path d="M4 5.5A2.5 2.5 0 0 1 6.5 3H20v16H6.5A2.5 2.5 0 0 0 4 21.5v-16Z" />
        <path d="M4 18.5A2.5 2.5 0 0 1 6.5 16H20" />
      </svg>
    )
  }

  return (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path d="M20 15a3 3 0 0 1-3 3H9l-5 3V7a3 3 0 0 1 3-3h10a3 3 0 0 1 3 3v8Z" />
      <path d="M8 9h8M8 13h5" />
    </svg>
  )
}

function WorkspaceApp() {
  const [activePage, setActivePage] = useState<ActivePage>('library')
  const [libraryView, setLibraryView] = useState<LibraryView>('sources')
  const [documents, setDocuments] = useState<DocumentRecord[]>([])
  const [subjects, setSubjects] = useState<SubjectRecord[]>([])
  const [selectedSubjectId, setSelectedSubjectId] = useState('')
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [deletingId, setDeletingId] = useState<string | null>(null)

  async function refreshDocuments() {
    setError(null)

    try {
      setDocuments(await getDocuments())
    } catch (requestError) {
      setError(
        requestError instanceof Error
          ? requestError.message
          : 'Đã xảy ra lỗi không xác định',
      )
    }
  }

  async function refreshSubjects() {
    const result = await getSubjects()

    setSubjects(result)
    setSelectedSubjectId((currentId) => (
      result.some((subject) => subject.subject_id === currentId)
        ? currentId
        : result[0]?.subject_id ?? ''
    ))
  }

  async function refreshWorkspace() {
    setIsLoading(true)
    setError(null)

    try {
      const [documentResult, subjectResult] = await Promise.all([
        getDocuments(),
        getSubjects(),
      ])

      setDocuments(documentResult)
      setSubjects(subjectResult)
      setSelectedSubjectId((currentId) => (
        subjectResult.some((subject) => subject.subject_id === currentId)
          ? currentId
          : subjectResult[0]?.subject_id ?? ''
      ))
    } catch (requestError) {
      setError(
        requestError instanceof Error
          ? requestError.message
          : 'Không thể tải workspace',
      )
    } finally {
      setIsLoading(false)
    }
  }

  useEffect(() => {
    let isActive = true

    async function loadWorkspace() {
      try {
        const [documentResult, subjectResult] = await Promise.all([
          getDocuments(),
          getSubjects(),
        ])

        if (!isActive) return

        setDocuments(documentResult)
        setSubjects(subjectResult)
        setSelectedSubjectId(subjectResult[0]?.subject_id ?? '')
      } catch (requestError) {
        if (!isActive) return

        setError(
          requestError instanceof Error
            ? requestError.message
            : 'Không thể tải workspace',
        )
      } finally {
        if (isActive) setIsLoading(false)
      }
    }

    void loadWorkspace()

    return () => {
      isActive = false
    }
  }, [])

  async function handleDelete(document: DocumentRecord) {
    const confirmed = window.confirm(
      `Xóa tài liệu "${document.filename}"?`,
    )

    if (!confirmed) return

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

  function handleSubjectCreated(subject: SubjectRecord) {
    setSubjects((current) => (
      [...current, subject].sort((left, right) => (
        left.name.localeCompare(right.name, 'vi')
      ))
    ))
    setSelectedSubjectId(subject.subject_id)
  }

  async function handleLifecycleChanged() {
    await Promise.all([
      refreshDocuments(),
      refreshSubjects(),
    ])
  }

  const selectedSubject = subjects.find(
    (subject) => subject.subject_id === selectedSubjectId,
  )
  const visibleDocuments = useMemo(
    () => documents.filter(
      (document) => document.subject_id === selectedSubjectId,
    ),
    [documents, selectedSubjectId],
  )
  const indexedCount = visibleDocuments.filter(
    (document) => document.status === 'INDEXED',
  ).length
  const processingCount = visibleDocuments.filter(
    (document) => (
      document.status === 'PROCESSING'
      || document.status === 'UPLOADED'
    ),
  ).length

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <span className="brand-mark" aria-hidden="true">CM</span>
          <div>
            <strong>CloudMentor</strong>
            <span>Không gian học tập có nguồn</span>
          </div>
        </div>

        <nav aria-label="Điều hướng chính">
          {(['library', 'chat'] as ActivePage[]).map((page) => (
            <button
              className={`nav-item ${activePage === page ? 'active' : ''}`}
              type="button"
              aria-current={activePage === page ? 'page' : undefined}
              key={page}
              onClick={() => setActivePage(page)}
            >
              <NavigationIcon type={page} />
              <span>{page === 'library' ? 'Thư viện' : 'Hỏi đáp & nguồn'}</span>
            </button>
          ))}
        </nav>

        <div className="sidebar-note">
          <span className="health-dot" aria-hidden="true" />
          <div>
            <strong>Phạm vi dữ liệu</strong>
            <span>{selectedSubject?.name ?? 'Chưa chọn môn học'}</span>
          </div>
        </div>
      </aside>

      <div className="workspace">
        <header className="workspace-bar">
          <div className="workspace-title">
            <span>Không gian làm việc</span>
            <strong>{activePage === 'library' ? 'Thư viện nguồn' : 'Học tập có nguồn'}</strong>
          </div>

          <label className="subject-context" htmlFor="workspace-subject">
            <span>Ngữ cảnh môn học</span>
            <select
              id="workspace-subject"
              value={selectedSubjectId}
              onChange={(event) => setSelectedSubjectId(event.target.value)}
              disabled={isLoading || subjects.length === 0}
            >
              {subjects.length === 0 ? (
                <option value="">
                  {isLoading ? 'Đang tải...' : 'Chưa có môn học'}
                </option>
              ) : subjects.map((subject) => (
                <option key={subject.subject_id} value={subject.subject_id}>
                  {subject.name}
                </option>
              ))}
            </select>
          </label>
        </header>

        <main className="main-content">
          {activePage === 'library' ? (
            <>
              <header className="page-header">
                <div>
                  <span className="eyebrow">Không gian dữ liệu</span>
                  <h1>Thư viện</h1>
                  <p>
                    Nạp, theo dõi và quản lý vòng đời nguồn học liệu
                    trong phạm vi môn học đang chọn.
                  </p>
                </div>

                <button
                  className="secondary-button"
                  type="button"
                  onClick={() => void refreshWorkspace()}
                  disabled={isLoading}
                >
                  {isLoading ? 'Đang đồng bộ...' : 'Đồng bộ dữ liệu'}
                </button>
              </header>

              <div className="workspace-tabs" role="tablist" aria-label="Khu vực thư viện">
                <button
                  role="tab"
                  aria-selected={libraryView === 'sources'}
                  className={libraryView === 'sources' ? 'active' : ''}
                  type="button"
                  onClick={() => setLibraryView('sources')}
                >
                  Nguồn dữ liệu
                </button>
                <button
                  role="tab"
                  aria-selected={libraryView === 'lifecycle'}
                  className={libraryView === 'lifecycle' ? 'active' : ''}
                  type="button"
                  onClick={() => setLibraryView('lifecycle')}
                >
                  Vòng đời & khôi phục
                </button>
              </div>

              {error && (
                <div className="error-banner" role="alert">
                  <span>{error}</span>
                  <button type="button" onClick={() => void refreshWorkspace()}>
                    Thử lại
                  </button>
                </div>
              )}

              {libraryView === 'sources' ? (
                <>
                  <section className="summary-grid" aria-label="Tổng quan nguồn dữ liệu">
                    <article className="summary-card">
                      <span>Nguồn trong môn học</span>
                      <strong>{visibleDocuments.length}</strong>
                      <small>Bản ghi nguồn</small>
                    </article>
                    <article className="summary-card success-card">
                      <span>Sẵn sàng truy vấn</span>
                      <strong>{indexedCount}</strong>
                      <small>Đã lập chỉ mục</small>
                    </article>
                    <article className="summary-card processing-card">
                      <span>Đang xử lý</span>
                      <strong>{processingCount}</strong>
                      <small>Đã nhận / đang xử lý</small>
                    </article>
                  </section>

                  <UploadPanel
                    subjects={subjects}
                    subjectId={selectedSubjectId}
                    onSubjectChange={setSelectedSubjectId}
                    onSubjectCreated={handleSubjectCreated}
                    onUploaded={refreshDocuments}
                  />

                  <section className="document-panel" aria-label="Danh sách tài liệu">
                    <div className="panel-heading">
                      <div>
                        <span className="panel-kicker">Nguồn chuẩn</span>
                        <h2>Tài liệu của {selectedSubject?.name ?? 'môn học'}</h2>
                        <p>Chỉ hiển thị nguồn chưa bị xóa khỏi hệ thống.</p>
                      </div>
                    </div>

                    {isLoading ? (
                      <p className="state-message">Đang tải tài liệu...</p>
                    ) : visibleDocuments.length === 0 ? (
                      <div className="state-message">
                        <strong>Chưa có nguồn dữ liệu</strong>
                        <span>Tải tài liệu đầu tiên để tạo phạm vi tri thức cho môn học này.</span>
                      </div>
                    ) : (
                      <div className="table-wrapper">
                        <table>
                          <thead>
                            <tr>
                              <th>Tài liệu</th>
                              <th>Chapter</th>
                              <th>Trạng thái xử lý</th>
                              <th>Ngày tải lên</th>
                              <th><span className="sr-only">Thao tác</span></th>
                            </tr>
                          </thead>
                          <tbody>
                            {visibleDocuments.map((document) => (
                              <tr key={document.document_id}>
                                <td>
                                  <strong>{document.filename}</strong>
                                  <span className="document-type">
                                    {document.file_type.toUpperCase()}
                                  </span>
                                </td>
                                <td>{document.chapter ?? '—'}</td>
                                <td>
                                  <span className={`status status-${document.status.toLowerCase()}`}>
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
                                    {deletingId === document.document_id ? 'Đang xóa...' : 'Xóa'}
                                  </button>
                                </td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    )}
                  </section>
                </>
              ) : (
                <SubjectLifecyclePanel onLifecycleChanged={handleLifecycleChanged} />
              )}
            </>
          ) : (
            <>
              <header className="page-header chat-page-header">
                <div>
                  <span className="eyebrow">Truy xuất có kiểm chứng</span>
                  <h1>Hỏi đáp có nguồn</h1>
                  <p>
                    Hỏi trong phạm vi {selectedSubject?.name ?? 'môn học đã chọn'}
                    {' '}và đối chiếu nguồn ngay cạnh câu trả lời.
                  </p>
                </div>
              </header>
              <ChatPanel
                documents={visibleDocuments}
                subjectId={selectedSubjectId}
                subjectName={selectedSubject?.name ?? ''}
              />
            </>
          )}
        </main>
      </div>
    </div>
  )
}

export default WorkspaceApp
