export interface ChatSource {
  chunk_id: string
  document_id: string
  chunk_index: number
  source: string
  page: number | null
  line_range: [number, number] | null
  paragraph_range: [number, number] | null
  distance: number
}

export interface ChatResponse {
  question: string
  answer: string
  sources: ChatSource[]
}