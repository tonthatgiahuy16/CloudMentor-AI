import { useEffect, useMemo, useState } from 'react'

import ChatPanel from './components/ChatPanel'
import MyResultsPanel from './components/MyResultsPanel'
import OnboardingQuizPanel from './components/OnboardingQuizPanel'
import SubjectLifecyclePanel from './components/SubjectLifecyclePanel'
import TrainingOverviewPanel from './components/TrainingOverviewPanel'
import UploadPanel from './components/UploadPanel'
import {
  activatePolicyVersion,
  deleteDocument,
  getDocuments,
  getSubjects,
} from './services/api'
import { isDocumentApplicableNow } from './services/onboardingStore'
import type {
  DocumentRecord,
  DocumentStatus,
} from './types/document'
import type { SubjectRecord } from './types/subject'
import './WorkspaceApp.css'

const IS_DEMO_MODE = import.meta.env.VITE_DEMO_MODE === 'true'

const STATUS_LABELS: Record<DocumentStatus, string> = {
  UPLOADED: 'Đã tiếp nhận',
  PROCESSING: 'Đang lập chỉ mục',
  INDEXED: 'Đã lập chỉ mục',
  FAILED: 'Lỗi chỉ mục',
  DELETED: 'Đã gỡ',
}

function formatDate(value: string): string {
  return new Intl.DateTimeFormat('vi-VN', {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(new Date(value))
}

type UserRole = 'admin' | 'employee'
type ActivePage =
  | 'library'
  | 'authoring'
  | 'overview'
  | 'chat'
  | 'quiz'
  | 'my-results'
type LibraryView = 'sources' | 'lifecycle'

const PAGE_LABELS: Record<ActivePage, string> = {
  library: 'Kho chính sách & Phiên bản',
  authoring: 'Biên soạn & Phát hành đề',
  overview: 'Tổng quan đào tạo',
  chat: 'Tra cứu nội quy',
  quiz: 'Làm bài kiểm tra',
  'my-results': 'Kết quả bài làm của tôi',
}

const ROLE_PAGES: Record<UserRole, ActivePage[]> = {
  admin: ['library', 'authoring', 'overview'],
  employee: ['chat', 'quiz', 'my-results'],
}

function NavigationIcon({ type }: { type: ActivePage }) {
  if (type === 'library') {
    return (
      <svg viewBox="0 0 24 24" aria-hidden="true">
        <path d="M4 5.5A2.5 2.5 0 0 1 6.5 3H20v16H6.5A2.5 2.5 0 0 0 4 21.5v-16Z" />
        <path d="M4 18.5A2.5 2.5 0 0 1 6.5 16H20" />
      </svg>
    )
  }

  if (type === 'authoring') {
    return (
      <svg viewBox="0 0 24 24" aria-hidden="true">
        <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7" />
        <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z" />
      </svg>
    )
  }

  if (type === 'chat') {
    return (
      <svg viewBox="0 0 24 24" aria-hidden="true">
        <path d="M20 15a3 3 0 0 1-3 3H9l-5 3V7a3 3 0 0 1 3-3h10a3 3 0 0 1 3 3v8Z" />
        <path d="M8 9h8M8 13h5" />
      </svg>
    )
  }

  if (type === 'quiz') {
    return (
      <svg viewBox="0 0 24 24" aria-hidden="true">
        <path d="M9 11l3 3L22 4" />
        <path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11" />
      </svg>
    )
  }

  if (type === 'my-results') {
    return (
      <svg viewBox="0 0 24 24" aria-hidden="true">
        <path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z" />
      </svg>
    )
  }

  return (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path d="M18 20V10M12 20V4M6 20v-6" />
    </svg>
  )
}

function WorkspaceApp() {
  const [userRole, setUserRole] = useState<UserRole>('admin')
  const [activePage, setActivePage] = useState<ActivePage>('library')
  const [libraryView, setLibraryView] = useState<LibraryView>('sources')
  const [documents, setDocuments] = useState<DocumentRecord[]>([])
  const [subjects, setSubjects] = useState<SubjectRecord[]>([])
  const [selectedSubjectId, setSelectedSubjectId] = useState('')
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [deletingId, setDeletingId] = useState<string | null>(null)
  const [activatingId, setActivatingId] = useState<string | null>(null)
  const [overviewRefreshKey, setOverviewRefreshKey] = useState(0)

  function handleRoleChange(newRole: UserRole) {
    setUserRole(newRole)
    if (newRole === 'admin') {
      setActivePage('library')
    } else {
      setActivePage('chat')
    }
  }

  async function refreshDocuments() {
    setError(null)

    try {
      setDocuments(await getDocuments())
    } catch (requestError) {
      setError(
        requestError instanceof Error
          ? requestError.message
          : 'Đã xảy ra lỗi không xác định khi tải danh sách văn bản',
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
          : 'Đã xảy ra lỗi không xác định',
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

        if (isActive) {
          setDocuments(documentResult)
          setSubjects(subjectResult)
          setSelectedSubjectId((currentId) => (
            subjectResult.some((subject) => subject.subject_id === currentId)
              ? currentId
              : subjectResult[0]?.subject_id ?? ''
          ))
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

    void loadWorkspace()

    return () => {
      isActive = false
    }
  }, [])

  function handleSubjectCreated(subject: SubjectRecord) {
    setSubjects((current) => [...current, subject])
    setSelectedSubjectId(subject.subject_id)
  }

  async function handleLifecycleChanged() {
    await Promise.all([
      refreshDocuments(),
      refreshSubjects(),
    ])
  }

  async function handleActivateDocument(document: DocumentRecord) {
    setActivatingId(document.document_id)
    setError(null)

    try {
      const today = new Intl.DateTimeFormat('en-CA').format(new Date())
      const effectiveFrom = document.effective_from ?? document.effective_date ?? today

      await activatePolicyVersion({
        documentId: document.document_id,
        effectiveFrom,
        supersedesDocumentId: null,
      })
      await refreshDocuments()
    } catch (requestError) {
      setError(
        requestError instanceof Error
          ? requestError.message
          : 'Không thể kích hoạt phiên bản chính sách',
      )
    } finally {
      setActivatingId(null)
    }
  }

  async function handleDelete(document: DocumentRecord) {
    const confirmed = window.confirm(
      `Gỡ văn bản chính sách "${document.filename}" khỏi hệ thống?`,
    )

    if (!confirmed) return

    setDeletingId(document.document_id)
    setError(null)

    try {
      await deleteDocument(document.document_id)
      await refreshDocuments()
    } catch (requestError) {
      setError(
        requestError instanceof Error
          ? requestError.message
          : 'Không thể xóa văn bản chính sách',
      )
    } finally {
      setDeletingId(null)
    }
  }

  const selectedSubject = useMemo(
    () => subjects.find(
      (subject) => subject.subject_id === selectedSubjectId,
    ) ?? null,
    [subjects, selectedSubjectId],
  )
  const visibleDocuments = useMemo(
    () => documents.filter(
      (document) => document.subject_id === selectedSubjectId,
    ),
    [documents, selectedSubjectId],
  )
  const applicableCount = visibleDocuments.filter(
    (document) => isDocumentApplicableNow(document),
  ).length
  const processingCount = visibleDocuments.filter(
    (document) => (
      document.status === 'PROCESSING'
      || document.status === 'UPLOADED'
    ),
  ).length

  const currentNavPages = ROLE_PAGES[userRole]

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <span className="brand-mark" aria-hidden="true">CM</span>
          <div>
            <strong>CloudMentor</strong>
            <span> Chính sách & Đào tạo Onboarding</span>
          </div>
        </div>

        <nav aria-label="Điều hướng chức năng">
          {currentNavPages.map((page) => (
            <button
              className={`nav-item ${activePage === page ? 'active' : ''}`}
              type="button"
              aria-current={activePage === page ? 'page' : undefined}
              key={page}
              onClick={() => setActivePage(page)}
            >
              <NavigationIcon type={page} />
              <span>{PAGE_LABELS[page]}</span>
            </button>
          ))}
        </nav>

        <div className="sidebar-note">
          <span className="health-dot" aria-hidden="true" />
          <div>
            <strong>Chuyên mục đang chọn</strong>
            <span>{selectedSubject?.name ?? 'Chưa chọn chuyên mục'}</span>
          </div>
        </div>
      </aside>

      <div className="workspace">
        <header className="workspace-bar">
          <div className="workspace-title">
            <span>Doanh nghiệp mẫu · Single-tenant MVP</span>
            <strong>{PAGE_LABELS[activePage]}</strong>
          </div>

          <div className="role-switcher-box" role="radiogroup" aria-label="Vai trò làm việc">
            <span className="role-switcher-label">Không gian:</span>
            <div className="role-switcher-group">
              <button
                type="button"
                className={`role-switcher-btn ${userRole === 'admin' ? 'active' : ''}`}
                onClick={() => handleRoleChange('admin')}
              >
                <span>👔 Người phụ trách đào tạo</span>
              </button>
              <button
                type="button"
                className={`role-switcher-btn ${userRole === 'employee' ? 'active' : ''}`}
                onClick={() => handleRoleChange('employee')}
              >
                <span>🎓 Nhân viên mới</span>
              </button>
            </div>
          </div>

          <label className="subject-context" htmlFor="workspace-subject">
            <span>Chuyên mục Onboarding</span>
            <select
              id="workspace-subject"
              value={selectedSubjectId}
              onChange={(event) => setSelectedSubjectId(event.target.value)}
              disabled={isLoading || subjects.length === 0}
            >
              {subjects.length === 0 ? (
                <option value="">
                  {isLoading ? 'Đang tải...' : 'Chưa có chuyên mục'}
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
          {activePage === 'library' && (
            <>
              <header className="page-header">
                <div>
                  <span className="eyebrow">PostgreSQL System of Record</span>
                  <h1>Kho chính sách</h1>
                  <p>
                    {IS_DEMO_MODE
                      ? 'Khám phá văn bản nội quy và tra cứu chính sách có dẫn nguồn trong phạm vi demo.'
                      : 'Quản lý văn bản onboarding (nội quy, nghỉ phép, bảo mật, quy trình hỗ trợ), kiểm soát ngày hiệu lực và trạng thái phiên bản áp dụng.'}
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

              {!IS_DEMO_MODE && (
                <div className="workspace-tabs" role="tablist" aria-label="Khu vực quản trị văn bản">
                  <button
                    role="tab"
                    aria-selected={libraryView === 'sources'}
                    className={libraryView === 'sources' ? 'active' : ''}
                    type="button"
                    onClick={() => setLibraryView('sources')}
                  >
                    Văn bản & phiên bản áp dụng
                  </button>
                  <button
                    role="tab"
                    aria-selected={libraryView === 'lifecycle'}
                    className={libraryView === 'lifecycle' ? 'active' : ''}
                    type="button"
                    onClick={() => setLibraryView('lifecycle')}
                  >
                    Vòng đời chuyên mục & tái tạo chỉ mục
                  </button>
                </div>
              )}

              {error && (
                <div className="error-banner" role="alert">
                  <span>{error}</span>
                  <button type="button" onClick={() => void refreshWorkspace()}>
                    Thử lại
                  </button>
                </div>
              )}

              {(IS_DEMO_MODE || libraryView === 'sources') ? (
                <>
                  <section className="summary-grid" aria-label="Tổng quan văn bản chính sách">
                    <article className="summary-card">
                      <span>Văn bản trong chuyên mục</span>
                      <strong>{visibleDocuments.length}</strong>
                      <small>Tệp gốc chuẩn đã đăng ký</small>
                    </article>
                    <article className="summary-card success-card">
                      <span>Phiên bản đang áp dụng</span>
                      <strong>{applicableCount}</strong>
                      <small>Trong PostgreSQL allow-list</small>
                    </article>
                    <article className="summary-card processing-card">
                      <span>Đang xử lý chỉ mục</span>
                      <strong>{processingCount}</strong>
                      <small>Extract → Chunk → Embed</small>
                    </article>
                  </section>

                  {!IS_DEMO_MODE && (
                    <UploadPanel
                      subjects={subjects}
                      subjectId={selectedSubjectId}
                      documents={visibleDocuments}
                      onSubjectChange={setSelectedSubjectId}
                      onSubjectCreated={handleSubjectCreated}
                      onUploaded={refreshDocuments}
                    />
                  )}

                  <section className="document-panel" aria-label="Danh sách văn bản chính sách">
                    <div className="panel-heading">
                      <div>
                        <span className="panel-kicker">Danh mục văn bản & kiểm soát hiệu lực</span>
                        <h2>Tài liệu thuộc {selectedSubject?.name ?? 'chuyên mục'}</h2>
                        <p>
                          Chỉ những văn bản có trạng thái Đã lập chỉ mục (INDEXED) và Đang áp dụng mới được đưa vào phạm vi tra cứu của nhân viên mới.
                        </p>
                      </div>
                    </div>

                    {isLoading ? (
                      <p className="state-message">Đang tải danh sách văn bản...</p>
                    ) : visibleDocuments.length === 0 ? (
                      <div className="state-message">
                        <strong>Chưa có văn bản chính sách</strong>
                        <span>Nạp tài liệu nội quy đầu tiên để mở phạm vi tra cứu cho chuyên mục này.</span>
                      </div>
                    ) : (
                      <div className="table-wrapper">
                        <table>
                          <thead>
                            <tr>
                              <th>Văn bản chính sách</th>
                              <th>Phiên bản</th>
                              <th>Khoảng hiệu lực</th>
                              <th>Hiệu lực tra cứu</th>
                              <th>Trạng thái chỉ mục</th>
                              <th>Ngày nạp</th>
                              {!IS_DEMO_MODE && <th><span className="sr-only">Thao tác</span></th>}
                            </tr>
                          </thead>
                          <tbody>
                            {visibleDocuments.map((document) => {
                              const isApplicable = isDocumentApplicableNow(document)
                              const effectiveFrom = document.effective_from ?? document.effective_date

                              return (
                                <tr key={document.document_id}>
                                  <td>
                                    <strong>{document.filename}</strong>
                                    <span className="document-type">
                                      {document.file_type.toUpperCase()}
                                    </span>
                                  </td>
                                  <td>
                                    <span className="version-pill">
                                      {document.chapter ? `v${document.chapter}.0` : 'v1.0'}
                                    </span>
                                  </td>
                                  <td>
                                    {effectiveFrom ? (
                                      <span>
                                        Từ {effectiveFrom}
                                        {document.effective_until ? ` → ${document.effective_until}` : ''}
                                      </span>
                                    ) : (
                                      <span className="text-muted">Chưa kích hoạt</span>
                                    )}
                                  </td>
                                  <td>
                                    <span
                                      className={`status ${
                                        isApplicable ? 'status-indexed' : 'status-deleted'
                                      }`}
                                    >
                                      {isApplicable ? 'Đang áp dụng' : 'Ngừng / Chưa áp dụng'}
                                    </span>
                                  </td>
                                  <td>
                                    <span className={`status status-${document.status.toLowerCase()}`}>
                                      {STATUS_LABELS[document.status]}
                                    </span>
                                  </td>
                                  <td>{formatDate(document.uploaded_at)}</td>
                                  {!IS_DEMO_MODE && (
                                    <td className="actions quiz-table-actions">
                                      {document.status === 'INDEXED' && !isApplicable && (
                                        <button
                                          className="secondary-button"
                                          type="button"
                                          disabled={activatingId === document.document_id}
                                          onClick={() => void handleActivateDocument(document)}
                                        >
                                          {activatingId === document.document_id
                                            ? 'Đang kích hoạt...'
                                            : 'Kích hoạt áp dụng'}
                                        </button>
                                      )}
                                      <button
                                        className="danger-button"
                                        type="button"
                                        disabled={deletingId === document.document_id}
                                        onClick={() => void handleDelete(document)}
                                      >
                                        {deletingId === document.document_id ? 'Đang xóa...' : 'Xóa'}
                                      </button>
                                    </td>
                                  )}
                                </tr>
                              )
                            })}
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
          )}

          {activePage === 'authoring' && (
            <>
              <header className="page-header">
                <div>
                  <span className="eyebrow">Dành cho người phụ trách đào tạo</span>
                  <h1>Biên soạn & Phát hành đề</h1>
                  <p>
                    Khởi tạo đề kiểm tra, nạp nhanh câu hỏi mẫu hoặc thêm câu hỏi mới gắn với văn bản nguồn, và phát hành chính thức cho nhân viên.
                  </p>
                </div>
              </header>
              <OnboardingQuizPanel
                key={`authoring-${selectedSubjectId}`}
                subjectId={selectedSubjectId}
                subjectName={selectedSubject?.name ?? ''}
                documents={visibleDocuments}
                isDemoMode={IS_DEMO_MODE}
                fixedMode="review"
                onAttemptSubmitted={() => setOverviewRefreshKey((k) => k + 1)}
              />
            </>
          )}

          {activePage === 'overview' && (
            <>
              <header className="page-header">
                <div>
                  <span className="eyebrow">Báo cáo dành cho người phụ trách đào tạo</span>
                  <h1>Tổng quan kết quả</h1>
                  <p>
                    Theo dõi kết quả hoàn thành và điểm số bài kiểm tra onboarding ở mức tổng quan
                    trong phạm vi doanh nghiệp mẫu.
                  </p>
                </div>
              </header>
              <TrainingOverviewPanel
                subjects={subjects}
                selectedSubjectId={selectedSubjectId}
                refreshKey={overviewRefreshKey}
              />
            </>
          )}

          {activePage === 'chat' && (
            <>
              <header className="page-header chat-page-header">
                <div>
                  <span className="eyebrow">Dành cho nhân viên mới</span>
                  <h1>Tra cứu nội quy</h1>
                  <p>
                    Nhân viên mới đặt câu hỏi bằng ngôn ngữ tự nhiên trong phạm vi{' '}
                    <strong>{selectedSubject?.name ?? 'chuyên mục đã chọn'}</strong>
                    {' '}và kiểm tra trực tiếp văn bản cùng vị trí trích dẫn.
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

          {activePage === 'quiz' && (
            <>
              <header className="page-header">
                <div>
                  <span className="eyebrow">Dành cho nhân viên mới</span>
                  <h1>Làm bài kiểm tra Onboarding</h1>
                  <p>
                    Thực hiện bài kiểm tra trắc nghiệm theo các quy định và chính sách đã học; hệ thống sẽ chấm điểm và phản hồi kết quả tức thì.
                  </p>
                </div>
              </header>
              <OnboardingQuizPanel
                key={`quiz-${selectedSubjectId}`}
                subjectId={selectedSubjectId}
                subjectName={selectedSubject?.name ?? ''}
                documents={visibleDocuments}
                isDemoMode={IS_DEMO_MODE}
                fixedMode="take"
                onAttemptSubmitted={() => setOverviewRefreshKey((k) => k + 1)}
              />
            </>
          )}

          {activePage === 'my-results' && (
            <>
              <header className="page-header">
                <div>
                  <span className="eyebrow">Lịch sử cá nhân</span>
                  <h1>Kết quả bài làm của tôi</h1>
                  <p>
                    Đối chiếu các câu đã làm, kiểm tra câu đúng/sai và xem lại các điều khoản chính sách cần ôn tập thêm.
                  </p>
                </div>
              </header>
              <MyResultsPanel onGoToQuiz={() => setActivePage('quiz')} />
            </>
          )}
        </main>
      </div>
    </div>
  )
}

export default WorkspaceApp
