export interface SubjectRecord {
  subject_id: string
  name: string
}

export type SubjectTrashStatus =
  | 'DELETING'
  | 'DELETED'
  | 'DELETE_FAILED'
  | 'RESTORING'
  | 'RESTORE_FAILED'

export interface SubjectTrashRecord extends SubjectRecord {
  status: SubjectTrashStatus
  deleted_at: string | null
  lifecycle_error: string | null
}

export interface DeleteSubjectResult {
  subject_id: string
  status: 'DELETED'
  processed_documents: number
  deleted_chunks: number
}

export interface RestoreSubjectResult {
  subject_id: string
  status: 'ACTIVE'
  processed_documents: number
  indexed_chunks: number
}
