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
  DELETING: 'Đang chuyển',
  DELETED: 'Trong thùng rác',
  DELETE_FAILED: 'Xóa thất bại',
  RESTORING: 'Đang khôi phục',
  RESTORE_FAILED: 'Khôi phục thất bại',
}

const LIFECYCLE_ERROR_MESSAGES: Record<string, string> = {
  'Subject deletion failed':
    'Không thể đưa môn học vào thùng rác. Xem chi tiết bên dưới.',
  'Subject restoration failed':
    'Không thể khôi phục môn học. Xem chi tiết bên dưới.',
  'Document source metadata is incomplete':
    'Metadata nguồn của tài liệu chưa đầy đủ nên chưa thể tái tạo chỉ mục.',
  'Retained source file is missing':
    'Không tìm thấy file nguồn đã lưu để khôi phục tài liệu.',
  'Retained source file size does not match':
    'Kích thước file nguồn không khớp với metadata đã lưu.',
  'Retained source checksum does not match':
    'Checksum của file nguồn không khớp với metadata đã lưu.',
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
              : 'Không thể tải dữ liệu môn học',
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
      `Đưa môn học "${subject.name}" vào thùng rác?\n\n`
      + 'Tài liệu sẽ bị ẩn khỏi tìm kiếm nhưng nguồn dữ liệu '
      + 'vẫn được giữ để có thể khôi phục.',
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
        `Đã đưa ${subject.name} vào thùng rác. `
        + `${result.processed_documents} tài liệu và `
        + `${result.deleted_chunks} chunks đã được xử lý.`,
      )
    } catch (requestError) {
      setError(
        requestError instanceof Error
          ? formatLifecycleError(requestError.message)
          : 'Không thể đưa môn học vào thùng rác',
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
        `Đã khôi phục ${subject.name}. `
        + `${result.processed_documents} tài liệu và `
        + `${result.indexed_chunks} chunks đã được lập chỉ mục lại.`,
      )
    } catch (requestError) {
      setError(
        requestError instanceof Error
          ? formatLifecycleError(requestError.message)
          : 'Không thể khôi phục môn học',
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
          : 'Không thể tải lại dữ liệu môn học',
      )
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <section
      className="subject-lifecycle"
      aria-label="Quản lý môn học"
      aria-busy={pendingAction !== null}
    >
      <div className="subject-overview">
        <article className="subject-overview-card">
          <span>Đang hoạt động</span>
          <strong>{activeSubjects.length}</strong>
          <p>Có thể tải tài liệu và truy vấn.</p>
        </article>

        <article className="subject-overview-card trash-summary">
          <span>Trong thùng rác</span>
          <strong>{trashSubjects.length}</strong>
          <p>Nguồn được giữ để khôi phục.</p>
        </article>

        <button
          className="secondary-button subject-refresh-button"
          type="button"
          onClick={() => void handleRefresh()}
          disabled={isLoading || pendingAction !== null}
        >
          {isLoading ? 'Đang tải...' : 'Tải lại dữ liệu'}
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
              <span className="subject-column-kicker">Active</span>
              <h2>Môn học đang hoạt động</h2>
            </div>
            <span className="subject-count">{activeSubjects.length}</span>
          </div>

          {isLoading ? (
            <p className="subject-empty">Đang tải môn học...</p>
          ) : activeSubjects.length === 0 ? (
            <div className="subject-empty">
              <strong>Chưa có môn học hoạt động</strong>
              <span>Tạo môn học ở trang Tài liệu để bắt đầu.</span>
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
                        <span>Sẵn sàng sử dụng</span>
                      </div>
                    </div>

                    <button
                      className="danger-button"
                      type="button"
                      onClick={() => void handleDelete(subject)}
                      disabled={pendingAction !== null}
                    >
                      {isDeleting ? 'Đang chuyển...' : 'Đưa vào thùng rác'}
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
              <span className="subject-column-kicker">Recoverable</span>
              <h2>Thùng rác</h2>
            </div>
            <span className="subject-count">{trashSubjects.length}</span>
          </div>

          {isLoading ? (
            <p className="subject-empty">Đang tải thùng rác...</p>
          ) : trashSubjects.length === 0 ? (
            <div className="subject-empty">
              <strong>Thùng rác đang trống</strong>
              <span>Các môn học có thể khôi phục sẽ xuất hiện tại đây.</span>
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
                      {isRestoring ? 'Đang khôi phục...' : 'Khôi phục'}
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
