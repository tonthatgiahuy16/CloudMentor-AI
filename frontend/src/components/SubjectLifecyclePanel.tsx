import { useEffect, useState } from 'react'

import {
  getSubjects,
  getSubjectTrash,
} from '../services/api'
import type {
  SubjectRecord,
  SubjectTrashRecord,
} from '../types/subject'

function SubjectLifecyclePanel() {
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

  useEffect(() => {
    let isActive = true

    async function loadSubjects() {
      try {
        const [
          activeResult,
          trashResult,
        ] = await Promise.all([
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

  if (isLoading) {
    return (
      <section aria-label="Quản lý môn học">
        <p>Đang tải môn học...</p>
      </section>
    )
  }

  return (
    <section aria-label="Quản lý môn học">
      <h2>Quản lý môn học</h2>

      {error && (
        <p role="alert">
          {error}
        </p>
      )}

      <section>
        <h3>Đang hoạt động</h3>

        {activeSubjects.length === 0 ? (
          <p>Chưa có môn học đang hoạt động.</p>
        ) : (
          <ul>
            {activeSubjects.map((subject) => (
              <li key={subject.subject_id}>
                {subject.name}
              </li>
            ))}
          </ul>
        )}
      </section>

      <section>
        <h3>Thùng rác</h3>

        {trashSubjects.length === 0 ? (
          <p>Thùng rác đang trống.</p>
        ) : (
          <ul>
            {trashSubjects.map((subject) => (
              <li key={subject.subject_id}>
                <span>{subject.name}</span>
                <span>{subject.status}</span>

                {subject.lifecycle_error && (
                  <span>
                    {subject.lifecycle_error}
                  </span>
                )}
              </li>
            ))}
          </ul>
        )}
      </section>
    </section>
  )
}

export default SubjectLifecyclePanel
