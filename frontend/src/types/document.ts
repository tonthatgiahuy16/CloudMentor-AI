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
}

export interface DeleteDocumentResult {
  document_id: string
  status: 'DELETED'
  deleted_chunks: number
}