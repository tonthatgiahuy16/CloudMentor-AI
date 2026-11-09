export interface QuizOptionCreateInput {
  text: string
  is_correct: boolean
}

export interface QuizQuestionCreateInput {
  prompt: string
  options: QuizOptionCreateInput[]
  source_document_id: string | null
  source_document_version: string | null
}

export interface QuizOptionPublic {
  option_id: string
  text: string
  position: number
}

export interface QuizQuestionPublic {
  question_id: string
  prompt: string
  position: number
  options: QuizOptionPublic[]
  source_document_id: string | null
  source_document_version: string | null
}

export interface QuizPublic {
  quiz_id: string
  subject_id: string
  title: string
  status: 'PUBLISHED'
  question_count: number
  questions: QuizQuestionPublic[]
}

export interface QuizSummary {
  quiz_id: string
  subject_id: string
  title: string
  status: 'DRAFT' | 'PUBLISHED' | 'ARCHIVED'
  question_count: number
}

export interface QuizCreateResponse {
  quiz_id: string
  subject_id: string
  title: string
  status: 'DRAFT' | 'PUBLISHED' | 'ARCHIVED'
}

export interface QuizPublishResponse {
  quiz_id: string
  status: 'PUBLISHED'
  question_count: number
}

export interface AttemptStartResponse {
  attempt_id: string
  quiz_id: string
  employee_id: string
  status: 'IN_PROGRESS'
}

export interface AttemptAnswerSubmitInput {
  question_id: string
  option_id: string | null
}

export interface AttemptAnswerResult {
  question_id: string
  selected_option_id: string | null
  correct_option_id: string
  is_correct: boolean
}

export interface AttemptResult {
  attempt_id: string
  quiz_id: string
  employee_id: string
  status: 'GRADED'
  score: number
  correct_count: number
  total_questions: number
  graded_at?: string | null
  answers: AttemptAnswerResult[]
}

export interface QuizOverview {
  quiz_id: string
  attempt_count: number
  graded_attempt_count: number
  average_score: number | null
}
