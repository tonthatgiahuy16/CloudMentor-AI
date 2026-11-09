export type DocumentStatus =
  | 'UPLOADED'
  | 'PROCESSING'
  | 'INDEXED'
  | 'FAILED'
  | 'DELETED'

export interface DocumentRecord {
  document_id: string
  subject_id: string
  filename: string
  file_type: string
  chapter: number | null
  status: DocumentStatus
  uploaded_at: string
  indexed_at: string | null
  effective_from?: string | null
  effective_until?: string | null
  effective_date?: string | null
  is_current?: boolean
}

export interface DeleteDocumentResult {
  document_id: string
  status: 'DELETED'
  deleted_chunks: number
}

export interface UploadDocumentInput {
  file: File
  subjectId: string
  chapter: number | null
  effectiveDate?: string | null
  supersedesDocumentId?: string | null
  activateImmediately?: boolean
}

export interface UploadDocumentResult {
  document_id: string
  filename: string
  chunks: number
}

export interface ActivatePolicyVersionInput {
  documentId: string
  effectiveFrom: string
  supersedesDocumentId?: string | null
}
