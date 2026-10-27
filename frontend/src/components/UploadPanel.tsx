import { useRef, useState } from 'react'
import type {
  DragEvent,
  FormEvent,
} from 'react'

import {
  createSubject,
  uploadDocument,
} from '../services/api'
import type { SubjectRecord } from '../types/subject'

const MAX_UPLOAD_BYTES = 10 * 1024 * 1024

const SUPPORTED_DOCUMENT_EXTENSIONS = [
  '.pdf',
  '.txt',
  '.docx',
] as const

const DOCUMENT_ACCEPT = [
  '.pdf',
  'application/pdf',
  '.txt',
  'text/plain',
  '.docx',
  'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
].join(',')

function isSupportedDocument(
  filename: string,
): boolean {
  const normalizedName = filename.toLowerCase()

  return SUPPORTED_DOCUMENT_EXTENSIONS.some(
    (extension) => (
      normalizedName.endsWith(extension)
    ),
  )
}

interface UploadPanelProps {
  subjects: SubjectRecord[]
  subjectId: string
  onSubjectChange: (subjectId: string) => void
  onSubjectCreated: (subject: SubjectRecord) => void
  onUploaded: () => Promise<void>
}

function UploadPanel({
  subjects,
  subjectId,
  onSubjectChange,
  onSubjectCreated,
  onUploaded,
}: UploadPanelProps) {
  const formRef = useRef<HTMLFormElement>(null)

  const [newSubjectName, setNewSubjectName] = useState('')
  const [chapter, setChapter] = useState('')
  const [file, setFile] = useState<File | null>(null)
  const [isDragging, setIsDragging] = useState(false)
  const [isCreatingSubject, setIsCreatingSubject] = useState(false)
  const [isUploading, setIsUploading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState<string | null>(null)

  async function handleCreateSubject(
    event: FormEvent<HTMLFormElement>,
  ) {
    event.preventDefault()

    const name = newSubjectName.trim()
    if (!name || isCreatingSubject) return

    setIsCreatingSubject(true)
    setError(null)
    setSuccess(null)

    try {
      const created = await createSubject(name)

      onSubjectCreated(created)
      setNewSubjectName('')
      setSuccess(`Đã thêm môn học ${created.name}`)
    } catch (requestError) {
      setError(
        requestError instanceof Error
          ? requestError.message
          : 'Không thể tạo môn học',
      )
    } finally {
      setIsCreatingSubject(false)
    }
  }


  function handleSelectedFile(
    nextFile: File | null,
  ) {
    setError(null)
    setSuccess(null)

    if (nextFile === null) {
      setFile(null)
      return
    }

    if (!isSupportedDocument(nextFile.name)) {
      setFile(null)
      setError(
        'Chỉ hỗ trợ file PDF, TXT hoặc DOCX',
      )
      return
    }

    if (nextFile.size > MAX_UPLOAD_BYTES) {
      setFile(null)
      setError(
        'Tài liệu không được vượt quá 10 MB',
      )
      return
    }

    setFile(nextFile)
  }


  function handleDragOver(
    event: DragEvent<HTMLLabelElement>,
  ) {
    event.preventDefault()
    event.dataTransfer.dropEffect = 'copy'
    setIsDragging(true)
  }


  function handleDragLeave(
    event: DragEvent<HTMLLabelElement>,
  ) {
    event.preventDefault()
    setIsDragging(false)
  }


  function handleDrop(
    event: DragEvent<HTMLLabelElement>,
  ) {
    event.preventDefault()
    setIsDragging(false)

    const droppedFiles = event.dataTransfer.files

    if (droppedFiles.length !== 1) {
      setFile(null)
      setError(
        'Chỉ được tải một tài liệu mỗi lần',
      )
      setSuccess(null)
      return
    }

    handleSelectedFile(
      droppedFiles[0] ?? null,
    )
  }


  async function handleSubmit(
    event: FormEvent<HTMLFormElement>,
  ) {
    event.preventDefault()
    setError(null)
    setSuccess(null)

    if (!file) {
      setError('Hãy chọn một tài liệu')
      return
    }

    if (!isSupportedDocument(file.name)) {
      setError(
        'Chỉ hỗ trợ file PDF, TXT hoặc DOCX',
      )
      return
    }

    if (file.size > MAX_UPLOAD_BYTES) {
      setError(
        'Tài liệu không được vượt quá 10 MB',
      )
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
        `Đã xử lý ${result.filename} thành ${result.chunks} đoạn dữ liệu`,
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
          <span className="eyebrow">Nạp dữ liệu</span>
          <h2>Tải tài liệu mới</h2>
          <p>
            PDF, TXT và DOCX sẽ được xử lý, chia đoạn dữ liệu
            và lập chỉ mục tìm kiếm.
          </p>
        </div>
        <span className="upload-limit">
          PDF · TXT · DOCX · tối đa 10 MB
        </span>
      </div>

      <div className="ingestion-context">
        <div>
          <span>Đích nạp dữ liệu</span>
          <strong>
            {subjects.find((subject) => subject.subject_id === subjectId)?.name
              ?? 'Chưa chọn môn học'}
          </strong>
        </div>
        <label className="form-field compact-subject-field">
          <span>Đổi môn học</span>
          <select
            value={subjectId}
            onChange={(event) => onSubjectChange(event.target.value)}
            disabled={subjects.length === 0}
          >
            {subjects.length === 0 ? (
              <option value="">Chưa có môn học</option>
            ) : subjects.map((subject) => (
              <option key={subject.subject_id} value={subject.subject_id}>
                {subject.name}
              </option>
            ))}
          </select>
        </label>
      </div>

      <form
        className="subject-create-form"
        onSubmit={handleCreateSubject}
      >
        <label className="form-field" htmlFor="new-subject-name">
          <span>Thêm môn học mới</span>
          <input
            id="new-subject-name"
            type="text"
            maxLength={255}
            placeholder="Ví dụ: Data Engineering"
            value={newSubjectName}
            onChange={(event) => setNewSubjectName(event.target.value)}
          />
        </label>
        <button
          className="secondary-action-button"
          type="submit"
          disabled={!newSubjectName.trim() || isCreatingSubject}
        >
          {isCreatingSubject ? 'Đang thêm...' : 'Thêm môn'}
        </button>
      </form>

      <div className="upload-divider" aria-hidden="true" />

      <form
        className="upload-form"
        ref={formRef}
        onSubmit={handleSubmit}
      >
        <label className="form-field chapter-field">
          <span>Chương</span>
          <input
            type="number"
            min="1"
            step="1"
            placeholder="Ví dụ: 3"
            value={chapter}
            onChange={(event) => setChapter(event.target.value)}
          />
        </label>

<label
  className={`file-field ${
    isDragging ? 'is-dragging' : ''
  }`}
  onDragEnter={handleDragOver}
  onDragOver={handleDragOver}
  onDragLeave={handleDragLeave}
  onDrop={handleDrop}
>
  <span>
    {file
      ? file.name
      : 'Chọn hoặc kéo thả PDF, TXT hoặc DOCX vào đây'}
  </span>

  <input
    type="file"
    accept={DOCUMENT_ACCEPT}
    onChange={(event) => {
      handleSelectedFile(
        event.target.files?.[0] ?? null,
      )
    }}
  />
</label>

        <button
          className="primary-button"
          type="submit"
          disabled={
            isUploading
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
