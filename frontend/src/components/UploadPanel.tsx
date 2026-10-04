import { useEffect, useRef, useState } from 'react'
import type { FormEvent } from 'react'

import {
  getSubjects,
  uploadDocument,
} from '../services/api'
import type { SubjectRecord } from '../types/subject'

const MAX_UPLOAD_BYTES = 10 * 1024 * 1024

interface UploadPanelProps {
  onUploaded: () => Promise<void>
}

function UploadPanel({
  onUploaded,
}: UploadPanelProps) {
  const formRef = useRef<HTMLFormElement>(null)

  const [subjects, setSubjects] = useState<SubjectRecord[]>([])
  const [subjectId, setSubjectId] = useState('')
  const [chapter, setChapter] = useState('')
  const [file, setFile] = useState<File | null>(null)
  const [isLoadingSubjects, setIsLoadingSubjects] = useState(true)
  const [isUploading, setIsUploading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState<string | null>(null)

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

  async function handleSubmit(
    event: FormEvent<HTMLFormElement>,
  ) {
    event.preventDefault()
    setError(null)
    setSuccess(null)

    if (!file) {
      setError('Hãy chọn một file PDF')
      return
    }

    if (!file.name.toLowerCase().endsWith('.pdf')) {
      setError('Chỉ hỗ trợ file PDF')
      return
    }

    if (file.size > MAX_UPLOAD_BYTES) {
      setError('File PDF không được vượt quá 10 MB')
      return
    }

    if (!subjectId) {
      setError('Hãy chọn môn học')
      return
    }

    let chapterNumber: number | null = null

    if (chapter.trim()) {
      chapterNumber = Number(chapter)

      if (
        !Number.isInteger(chapterNumber)
        || chapterNumber < 1
      ) {
        setError('Chapter phải là số nguyên lớn hơn 0')
        return
      }
    }

    setIsUploading(true)

    try {
      const result = await uploadDocument({
        file,
        subjectId,
        chapter: chapterNumber,
      })

      setSuccess(
        `Đã xử lý ${result.filename} thành ${result.chunks} chunks`,
      )
      setFile(null)
      setChapter('')
      formRef.current?.reset()

      await onUploaded()
    } catch (requestError) {
      setError(
        requestError instanceof Error
          ? requestError.message
          : 'Không thể tải tài liệu lên',
      )
    } finally {
      setIsUploading(false)
    }
  }

  return (
    <section className="upload-panel">
      <div className="upload-heading">
        <div>
          <span className="eyebrow">Document ingestion</span>
          <h2>Tải tài liệu mới</h2>
          <p>
            PDF sẽ được xử lý, chia chunks và lập chỉ mục tìm kiếm.
          </p>
        </div>
        <span className="upload-limit">PDF · tối đa 10 MB</span>
      </div>

      <form ref={formRef} onSubmit={handleSubmit}>
        <label className="form-field">
          <span>Môn học</span>
          <select
            value={subjectId}
            onChange={(event) => setSubjectId(event.target.value)}
            disabled={isLoadingSubjects || subjects.length === 0}
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
        </label>

        <label className="form-field chapter-field">
          <span>Chapter</span>
          <input
            type="number"
            min="1"
            step="1"
            placeholder="Ví dụ: 3"
            value={chapter}
            onChange={(event) => setChapter(event.target.value)}
          />
        </label>

        <label className="file-field">
          <span>{file ? file.name : 'Chọn file PDF'}</span>
          <input
            type="file"
            accept=".pdf,application/pdf"
            onChange={(event) => {
              setFile(event.target.files?.[0] ?? null)
              setError(null)
              setSuccess(null)
            }}
          />
        </label>

        <button
          className="primary-button"
          type="submit"
          disabled={
            isUploading
            || isLoadingSubjects
            || subjects.length === 0
          }
        >
          {isUploading ? 'Đang xử lý...' : 'Tải lên'}
        </button>
      </form>

      {error && (
        <p className="form-message error-message" role="alert">
          {error}
        </p>
      )}

      {success && (
        <p className="form-message success-message">
          {success}
        </p>
      )}
    </section>
  )
}

export default UploadPanel