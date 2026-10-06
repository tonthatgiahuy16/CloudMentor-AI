export interface ChatSource {
  chunk_id: string
  document_id: string
  chunk_index: number
  source: string
  page: number
  distance: number
}

export interface ChatResponse {
  question: string
  answer: string
  sources: ChatSource[]
}