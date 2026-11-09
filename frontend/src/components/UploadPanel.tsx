import { useRef, useState } from 'react'
import type {
  DragEvent,
  FormEvent,
} from 'react'

import {
  createSubject,
  uploadDocument,
} from '../services/api'
import { isDocumentApplicableNow } from '../services/onboardingStore'
import type { DocumentRecord } from '../types/document'
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
  documents?: DocumentRecord[]
  onSubjectChange: (subjectId: string) => void
  onSubjectCreated: (subject: SubjectRecord) => void
  onUploaded: () => Promise<void>
}

function UploadPanel({
  subjects,
  subjectId,
  documents = [],
  onSubjectChange,
  onSubjectCreated,
  onUploaded,
}: UploadPanelProps) {
  const formRef = useRef<HTMLFormElement>(null)
  const todayIso = new Intl.DateTimeFormat('en-CA').format(new Date())

  const [newSubjectName, setNewSubjectName] = useState('')
  const [chapter, setChapter] = useState('')
  const [effectiveDate, setEffectiveDate] = useState(todayIso)
  const [supersedesId, setSupersedesId] = useState('')
  const [activateOnUpload, setActivateOnUpload] = useState(true)
  const [file, setFile] = useState<File | null>(null)
  const [isDragging, setIsDragging] = useState(false)
  const [isCreatingSubject, setIsCreatingSubject] = useState(false)
  const [isUploading, setIsUploading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState<string | null>(null)

  const activeSubjectDocs = documents.filter((d) =>
    isDocumentApplicableNow(d),
  )

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
      setSuccess(`Đã tạo chuyên mục chính sách "${created.name}"`)
    } catch (requestError) {
      setError(
        requestError instanceof Error
          ? requestError.message
          : 'Không thể tạo chuyên mục onboarding',
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
        'Chỉ hỗ trợ văn bản PDF, TXT (UTF-8) hoặc DOCX',
      )
      return
    }

    if (nextFile.size > MAX_UPLOAD_BYTES) {
      setFile(null)
      setError(
        'Văn bản không được vượt quá 10 MB',
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
        'Chỉ được tải một văn bản mỗi lần',
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
      setError('Hãy chọn một văn bản chính sách')
      return
    }

    if (!isSupportedDocument(file.name)) {
      setError(
        'Chỉ hỗ trợ văn bản PDF, TXT hoặc DOCX',
      )
      return
    }

    if (file.size > MAX_UPLOAD_BYTES) {
      setError(
        'Văn bản không được vượt quá 10 MB',
      )
      return
    }

    if (!subjectId) {
      setError('Hãy chọn chuyên mục onboarding')
      return
    }

    let chapterNumber: number | null = null

    if (chapter.trim()) {
      chapterNumber = Number(chapter)

      if (
        !Number.isInteger(chapterNumber)
        || chapterNumber < 1
      ) {
        setError('Số phiên bản phải là số nguyên lớn hơn 0')
        return
      }
    }

    setIsUploading(true)

    try {
      const result = await uploadDocument({
        file,
        subjectId,
        chapter: chapterNumber,
        effectiveDate: effectiveDate || todayIso,
        supersedesDocumentId: supersedesId || null,
        activateImmediately: activateOnUpload,
      })

      setSuccess(
        activateOnUpload
          ? `Đã lập chỉ mục và kích hoạt hiệu lực cho ${result.filename} (${result.chunks} đoạn dữ liệu)`
          : `Đã lập chỉ mục ${result.filename} (${result.chunks} đoạn dữ liệu) ở trạng thái chờ kích hoạt`,
      )
      setFile(null)
      setChapter('')
      setSupersedesId('')
      formRef.current?.reset()

      await onUploaded()
    } catch (requestError) {
      setError(
        requestError instanceof Error
          ? requestError.message
          : 'Không thể tải văn bản chính sách lên',
      )
    } finally {
      setIsUploading(false)
    }
  }

  return (
    <section className="upload-panel">
      <div className="upload-heading">
        <div>
          <span className="eyebrow">Quản trị văn bản & phiên bản</span>
          <h2>Nạp tài liệu Onboarding</h2>
          <p>
            Văn bản gốc (PDF, TXT, DOCX) được lưu trữ chuẩn hóa, lập chỉ mục Chroma
            và xác thực số lượng đoạn trước khi kích hoạt hiệu lực trong PostgreSQL.
          </p>
        </div>
        <span className="upload-limit">
          PDF · TXT · DOCX · tối đa 10 MB
        </span>
      </div>

      <div className="ingestion-context">
        <div>
          <span>Chuyên mục chính sách đích</span>
          <strong>
            {subjects.find((subject) => subject.subject_id === subjectId)?.name
              ?? 'Chưa chọn chuyên mục'}
          </strong>
        </div>
        <label className="form-field compact-subject-field">
          <span>Đổi chuyên mục</span>
          <select
            value={subjectId}
            onChange={(event) => onSubjectChange(event.target.value)}
            disabled={subjects.length === 0}
          >
            {subjects.length === 0 ? (
              <option value="">Chưa có chuyên mục</option>
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
          <span>Tạo chuyên mục onboarding mới</span>
          <input
            id="new-subject-name"
            type="text"
            maxLength={255}
            placeholder="Ví dụ: Nội quy lao động, Nghỉ phép & Bảo mật cơ bản"
            value={newSubjectName}
            onChange={(event) => setNewSubjectName(event.target.value)}
          />
        </label>
        <button
          className="secondary-action-button"
          type="submit"
          disabled={!newSubjectName.trim() || isCreatingSubject}
        >
          {isCreatingSubject ? 'Đang tạo...' : 'Thêm chuyên mục'}
        </button>
      </form>

      <div className="upload-divider" aria-hidden="true" />

      <form
        className="upload-form-stack"
        ref={formRef}
        onSubmit={handleSubmit}
      >
        <div className="upload-form upload-form-versioned">
          <label className="form-field chapter-field">
            <span>Phiên bản (v)</span>
            <input
              type="number"
              min="1"
              step="1"
              placeholder="Ví dụ: 1"
              value={chapter}
              onChange={(event) => setChapter(event.target.value)}
            />
          </label>

          <label className="form-field effective-date-field">
            <span>Ngày hiệu lực</span>
            <input
              type="date"
              value={effectiveDate}
              onChange={(event) => setEffectiveDate(event.target.value)}
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
                : 'Chọn hoặc kéo thả văn bản nội quy (PDF, TXT, DOCX) vào đây'}
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
            {isUploading ? 'Đang lập chỉ mục...' : 'Nạp văn bản'}
          </button>
        </div>

        <div className="upload-version-options">
          <label className="checkbox-field">
            <input
              type="checkbox"
              checked={activateOnUpload}
              onChange={(event) => setActivateOnUpload(event.target.checked)}
            />
            <span>Kích hoạt áp dụng ngay sau khi kiểm tra chỉ mục thành công</span>
          </label>

          {activateOnUpload && activeSubjectDocs.length > 0 && (
            <label className="form-field supersedes-field">
              <span>Thay thế văn bản cũ (tùy chọn)</span>
              <select
                value={supersedesId}
                onChange={(event) => setSupersedesId(event.target.value)}
              >
                <option value="">Không thay thế (áp dụng song song)</option>
                {activeSubjectDocs.map((doc) => (
                  <option key={doc.document_id} value={doc.document_id}>
                    Thay thế: {doc.filename} {doc.chapter ? `(v${doc.chapter})` : ''}
                  </option>
                ))}
              </select>
            </label>
          )}
        </div>
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
