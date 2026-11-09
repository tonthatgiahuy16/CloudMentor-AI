import { useEffect, useState } from 'react'

import {
  deleteSubject,
  getSubjects,
  getSubjectTrash,
  restoreSubject,
} from '../services/api'
import type {
  SubjectRecord,
  SubjectTrashRecord,
  SubjectTrashStatus,
} from '../types/subject'

interface SubjectLifecyclePanelProps {
  onLifecycleChanged: () => Promise<void>
}

interface PendingAction {
  subjectId: string
  type: 'delete' | 'restore'
}

const STATUS_LABELS: Record<SubjectTrashStatus, string> = {
  DELETING: 'Đang thu hồi',
  DELETED: 'Đã lưu trữ',
  DELETE_FAILED: 'Thu hồi thất bại',
  RESTORING: 'Đang tái tạo chỉ mục',
  RESTORE_FAILED: 'Khôi phục thất bại',
}

const LIFECYCLE_ERROR_MESSAGES: Record<string, string> = {
  'Subject deletion failed':
    'Không thể đưa chuyên mục vào lưu trữ. Xem chi tiết bên dưới.',
  'Subject restoration failed':
    'Không thể khôi phục chuyên mục. Xem chi tiết bên dưới.',
  'Document source metadata is incomplete':
    'Metadata nguồn của văn bản chưa đầy đủ nên chưa thể tái tạo chỉ mục.',
  'Retained source file is missing':
    'Không tìm thấy tệp gốc chuẩn đã lưu để khôi phục văn bản.',
  'Retained source file size does not match':
    'Kích thước tệp gốc không khớp với metadata đã đăng ký.',
  'Retained source checksum does not match':
    'Mã băm SHA-256 của tệp gốc không khớp với metadata đã lưu.',
}

function formatLifecycleError(value: string): string {
  return LIFECYCLE_ERROR_MESSAGES[value] ?? value
}

function formatDeletedAt(value: string | null): string {
  if (!value) return 'Chưa ghi nhận thời gian'

  return new Intl.DateTimeFormat('vi-VN', {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(new Date(value))
}

function SubjectLifecyclePanel({
  onLifecycleChanged,
}: SubjectLifecyclePanelProps) {
  const [activeSubjects, setActiveSubjects] = useState<
    SubjectRecord[]
  >([])
  const [trashSubjects, setTrashSubjects] = useState<
    SubjectTrashRecord[]
  >([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(
    null,
  )
  const [success, setSuccess] = useState<string | null>(null)
  const [pendingAction, setPendingAction] = useState<
    PendingAction | null
  >(null)

  async function refreshSubjects() {
    const [activeResult, trashResult] = await Promise.all([
      getSubjects(),
      getSubjectTrash(),
    ])

    setActiveSubjects(activeResult)
    setTrashSubjects(trashResult)
  }

  useEffect(() => {
    let isActive = true

    async function loadSubjects() {
      try {
        const [activeResult, trashResult] = await Promise.all([
          getSubjects(),
          getSubjectTrash(),
        ])

        if (isActive) {
          setActiveSubjects(activeResult)
          setTrashSubjects(trashResult)
        }
      } catch (requestError) {
        if (isActive) {
          setError(
            requestError instanceof Error
              ? requestError.message
              : 'Không thể tải dữ liệu chuyên mục chính sách',
          )
        }
      } finally {
        if (isActive) {
          setIsLoading(false)
        }
      }
    }

    void loadSubjects()

    return () => {
      isActive = false
    }
  }, [])

  async function reloadAfterAction() {
    await Promise.all([
      refreshSubjects(),
      onLifecycleChanged(),
    ])
  }

  async function handleDelete(subject: SubjectRecord) {
    const confirmed = window.confirm(
      `Thu hồi chuyên mục "${subject.name}" khỏi phạm vi tra cứu?\n\n`
      + 'Chỉ mục Chroma sẽ được gỡ bỏ để nhân viên không tra cứu nhầm, '
      + 'nhưng tệp gốc chuẩn và bản ghi PostgreSQL vẫn được bảo toàn để tái tạo.',
    )

    if (!confirmed || pendingAction) return

    setPendingAction({
      subjectId: subject.subject_id,
      type: 'delete',
    })
    setError(null)
    setSuccess(null)

    try {
      const result = await deleteSubject(subject.subject_id)

      await reloadAfterAction()
      setSuccess(
        `Đã thu hồi chuyên mục ${subject.name}. `
        + `${result.processed_documents} văn bản và `
        + `${result.deleted_chunks} vector dẫn xuất đã được gỡ khỏi Chroma.`,
      )
    } catch (requestError) {
      setError(
        requestError instanceof Error
          ? formatLifecycleError(requestError.message)
          : 'Không thể thu hồi chuyên mục chính sách',
      )

      try {
        await reloadAfterAction()
      } catch {
        // Keep the original lifecycle error visible.
      }
    } finally {
      setPendingAction(null)
    }
  }

  async function handleRestore(subject: SubjectTrashRecord) {
    if (pendingAction) return

    setPendingAction({
      subjectId: subject.subject_id,
      type: 'restore',
    })
    setError(null)
    setSuccess(null)

    try {
      const result = await restoreSubject(subject.subject_id)

      await reloadAfterAction()
      setSuccess(
        `Đã khôi phục chuyên mục ${subject.name} từ tệp gốc chuẩn. `
        + `${result.processed_documents} văn bản và `
        + `${result.indexed_chunks} đoạn trích dẫn đã được tái lập chỉ mục.`,
      )
    } catch (requestError) {
      setError(
        requestError instanceof Error
          ? formatLifecycleError(requestError.message)
          : 'Không thể khôi phục chuyên mục chính sách',
      )

      try {
        await reloadAfterAction()
      } catch {
        // Keep the original lifecycle error visible.
      }
    } finally {
      setPendingAction(null)
    }
  }

  async function handleRefresh() {
    if (pendingAction) return

    setIsLoading(true)
    setError(null)

    try {
      await reloadAfterAction()
    } catch (requestError) {
      setError(
        requestError instanceof Error
          ? requestError.message
          : 'Không thể tải lại dữ liệu chuyên mục',
      )
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <section
      className="subject-lifecycle"
      aria-label="Quản lý vòng đời chuyên mục chính sách"
      aria-busy={pendingAction !== null}
    >
      <div className="subject-overview">
        <article className="subject-overview-card">
          <span>Chuyên mục đang áp dụng</span>
          <strong>{activeSubjects.length}</strong>
          <p>Đang mở cho nhân viên tra cứu và làm bài onboarding.</p>
        </article>

        <article className="subject-overview-card trash-summary">
          <span>Đã thu hồi / Lưu trữ</span>
          <strong>{trashSubjects.length}</strong>
          <p>Đã gỡ vector Chroma, giữ tệp gốc chuẩn để tái tạo.</p>
        </article>

        <button
          className="secondary-button subject-refresh-button"
          type="button"
          onClick={() => void handleRefresh()}
          disabled={isLoading || pendingAction !== null}
        >
          {isLoading ? 'Đang tải...' : 'Đồng bộ trạng thái'}
        </button>
      </div>

      {error && (
        <div className="error-banner" role="alert">
          <span>{error}</span>
        </div>
      )}

      {success && (
        <p className="form-message success-message" role="status">
          {success}
        </p>
      )}

      <div className="subject-lifecycle-grid">
        <section className="subject-column">
          <div className="subject-column-heading">
            <div>
              <span className="subject-column-kicker">Phạm vi hiện hành</span>
              <h2>Chuyên mục đang hoạt động</h2>
            </div>
            <span className="subject-count">{activeSubjects.length}</span>
          </div>

          {isLoading ? (
            <p className="subject-empty">Đang tải chuyên mục...</p>
          ) : activeSubjects.length === 0 ? (
            <div className="subject-empty">
              <strong>Chưa có chuyên mục hoạt động</strong>
              <span>Tạo chuyên mục mới ở tab Văn bản chính sách để bắt đầu.</span>
            </div>
          ) : (
            <ul className="subject-list">
              {activeSubjects.map((subject) => {
                const isDeleting =
                  pendingAction?.subjectId === subject.subject_id
                  && pendingAction.type === 'delete'

                return (
                  <li className="subject-card" key={subject.subject_id}>
                    <div className="subject-card-copy">
                      <span className="subject-avatar" aria-hidden="true">
                        {subject.name.slice(0, 1).toUpperCase()}
                      </span>
                      <div>
                        <strong>{subject.name}</strong>
                        <span>Đang mở tra cứu chính sách</span>
                      </div>
                    </div>

                    <button
                      className="danger-button"
                      type="button"
                      onClick={() => void handleDelete(subject)}
                      disabled={pendingAction !== null}
                    >
                      {isDeleting ? 'Đang thu hồi...' : 'Thu hồi chỉ mục'}
                    </button>
                  </li>
                )
              })}
            </ul>
          )}
        </section>

        <section className="subject-column subject-trash-column">
          <div className="subject-column-heading">
            <div>
              <span className="subject-column-kicker">Tái tạo từ Source Storage</span>
              <h2>Chuyên mục đã lưu trữ</h2>
            </div>
            <span className="subject-count">{trashSubjects.length}</span>
          </div>

          {isLoading ? (
            <p className="subject-empty">Đang tải danh sách lưu trữ...</p>
          ) : trashSubjects.length === 0 ? (
            <div className="subject-empty">
              <strong>Không có chuyên mục nào trong kho lưu trữ</strong>
              <span>Các chuyên mục bị thu hồi chỉ mục sẽ xuất hiện tại đây để tái tạo khi cần.</span>
            </div>
          ) : (
            <ul className="subject-list">
              {trashSubjects.map((subject) => {
                const isRestoring =
                  pendingAction?.subjectId === subject.subject_id
                  && pendingAction.type === 'restore'
                const isTransitioning =
                  subject.status === 'DELETING'
                  || subject.status === 'RESTORING'

                return (
                  <li className="subject-card subject-trash-card" key={subject.subject_id}>
                    <div className="subject-trash-main">
                      <div className="subject-card-copy">
                        <span className="subject-avatar trash-avatar" aria-hidden="true">
                          {subject.name.slice(0, 1).toUpperCase()}
                        </span>
                        <div>
                          <strong>{subject.name}</strong>
                          <span>{formatDeletedAt(subject.deleted_at)}</span>
                        </div>
                      </div>

                      <span
                        className={`subject-status subject-status-${subject.status.toLowerCase()}`}
                      >
                        {STATUS_LABELS[subject.status]}
                      </span>
                    </div>

                    {subject.lifecycle_error && (
                      <p className="subject-lifecycle-error" role="alert">
                        {formatLifecycleError(subject.lifecycle_error)}
                      </p>
                    )}

                    <button
                      className="restore-button"
                      type="button"
                      onClick={() => void handleRestore(subject)}
                      disabled={pendingAction !== null || isTransitioning}
                    >
                      {isRestoring ? 'Đang tái lập chỉ mục...' : 'Tái tạo chỉ mục Chroma'}
                    </button>
                  </li>
                )
              })}
            </ul>
          )}
        </section>
      </div>
    </section>
  )
}

export default SubjectLifecyclePanel
