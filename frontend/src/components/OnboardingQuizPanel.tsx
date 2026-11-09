import { type FormEvent, useEffect, useState } from 'react'

import {
  addQuestionToQuiz,
  createDraftQuiz,
  getPublishedQuizDetail,
  getPublishedQuizzes,
  publishDraftQuiz,
  startQuizAttempt,
  submitQuizAttempt,
} from '../services/api'
import {
  type DraftQuizSession,
  getSavedDraftQuizzes,
  recordCompletedAttempt,
  removeDraftQuizSession,
  saveDraftQuizSession,
} from '../services/onboardingStore'
import type { DocumentRecord } from '../types/document'
import type {
  AttemptResult,
  QuizPublic,
  QuizSummary,
} from '../types/quiz'

interface OnboardingQuizPanelProps {
  subjectId: string
  subjectName: string
  documents: DocumentRecord[]
  isDemoMode: boolean
  onAttemptSubmitted: () => void
  fixedMode?: 'take' | 'review'
}

type QuizTabMode = 'take' | 'review'

const POSITION_KEYS = ['A', 'B', 'C', 'D']

const SAMPLE_ONBOARDING_PRESETS = [
  {
    prompt:
      'Khi xin nghỉ phép từ 03 ngày làm việc liên tiếp trở lên, nhân viên cần gửi đơn và được quản lý phê duyệt trước bao lâu?',
    options: [
      { text: 'Trước ít nhất 24 giờ', is_correct: false },
      { text: 'Trước ít nhất 03 ngày làm việc', is_correct: true },
      { text: 'Trước ít nhất 07 ngày làm việc', is_correct: false },
      { text: 'Không cần báo trước nếu đã bàn giao xong', is_correct: false },
    ],
    version: 'v1.0 - Điều 4',
  },
  {
    prompt:
      'Theo quy định bảo mật, mật khẩu tài khoản doanh nghiệp bắt buộc có độ dài tối thiểu bao nhiêu ký tự và đổi định kỳ mấy ngày một lần?',
    options: [
      { text: 'Tối thiểu 8 ký tự, đổi định kỳ 30 ngày một lần', is_correct: false },
      { text: 'Tối thiểu 10 ký tự, đổi định kỳ 60 ngày một lần', is_correct: false },
      { text: 'Tối thiểu 12 ký tự, đổi định kỳ 90 ngày một lần', is_correct: true },
      { text: 'Tối thiểu 16 ký tự, không bắt buộc đổi nếu có 2FA', is_correct: false },
    ],
    version: 'v1.0 - Điều 5',
  },
  {
    prompt:
      'Sau khi hoàn thành 02 tháng thử việc, nhân viên chính thức được phép làm việc từ xa (Work From Home) tối đa bao nhiêu ngày mỗi tuần?',
    options: [
      { text: 'Tối đa 02 ngày mỗi tuần', is_correct: true },
      { text: 'Tối đa 03 ngày mỗi tuần', is_correct: false },
      { text: 'Tối đa 01 ngày mỗi tuần', is_correct: false },
      { text: 'Không giới hạn số ngày làm việc từ xa', is_correct: false },
    ],
    version: 'v1.0 - Điều 2',
  },
]

function OnboardingQuizPanel({
  subjectId,
  subjectName,
  documents,
  isDemoMode,
  onAttemptSubmitted,
  fixedMode,
}: OnboardingQuizPanelProps) {
  const [internalMode, setInternalMode] = useState<QuizTabMode>(
    fixedMode ?? 'take',
  )
  const mode = fixedMode ?? internalMode

  const [publishedQuizzes, setPublishedQuizzes] = useState<QuizSummary[]>([])
  const [selectedQuizId, setSelectedQuizId] = useState('')
  const [activeQuiz, setActiveQuiz] = useState<QuizPublic | null>(null)
  const [isLoadingQuizzes, setIsLoadingQuizzes] = useState(false)
  const [isLoadingQuizDetail, setIsLoadingQuizDetail] = useState(false)

  // Employee Quiz-taking state
  const [employeeId, setEmployeeId] = useState('')
  const [selectedOptionMap, setSelectedOptionMap] = useState<
    Record<string, string>
  >({})
  const [submittedResult, setSubmittedResult] = useState<AttemptResult | null>(
    null,
  )
  const [isSubmittingAttempt, setIsSubmittingAttempt] = useState(false)
  const [takeError, setTakeError] = useState<string | null>(null)

  // Admin / Reviewer Quiz-authoring state
  const [draftQuizzes, setDraftQuizzes] = useState<DraftQuizSession[]>(() =>
    getSavedDraftQuizzes(subjectId),
  )
  const [selectedDraftQuizId, setSelectedDraftQuizId] = useState(
    () => getSavedDraftQuizzes(subjectId)[0]?.quiz_id ?? '',
  )
  const [newQuizTitle, setNewQuizTitle] = useState('')
  const [isCreatingQuiz, setIsCreatingQuiz] = useState(false)
  const [isPublishingQuiz, setIsPublishingQuiz] = useState(false)
  const [isPopulatingPresets, setIsPopulatingPresets] = useState(false)

  // Question Authoring inside selected draft quiz
  const [questionPrompt, setQuestionPrompt] = useState('')
  const [optionA, setOptionA] = useState('')
  const [optionB, setOptionB] = useState('')
  const [optionC, setOptionC] = useState('')
  const [optionD, setOptionD] = useState('')
  const [correctIndex, setCorrectIndex] = useState<number>(0)
  const [sourceDocId, setSourceDocId] = useState('')
  const [sourceVersion, setSourceVersion] = useState('v1.0')
  const [isAddingQuestion, setIsAddingQuestion] = useState(false)
  const [authorFeedback, setAuthorFeedback] = useState<string | null>(null)
  const [authorError, setAuthorError] = useState<string | null>(null)

  async function loadQuizzesForSubject(targetSubjectId: string) {
    if (!targetSubjectId) {
      setPublishedQuizzes([])
      setSelectedQuizId('')
      setActiveQuiz(null)
      return
    }

    setIsLoadingQuizzes(true)
    setTakeError(null)

    try {
      const list = await getPublishedQuizzes(targetSubjectId)
      setPublishedQuizzes(list)
      setSelectedQuizId((currentId) => (
        list.some((item) => item.quiz_id === currentId)
          ? currentId
          : list[0]?.quiz_id ?? ''
      ))
    } catch (requestError) {
      setTakeError(
        requestError instanceof Error
          ? requestError.message
          : 'Không thể tải danh sách đề kiểm tra đã phát hành',
      )
    } finally {
      setIsLoadingQuizzes(false)
    }
  }

  useEffect(() => {
    let isMounted = true

    async function fetchInitialQuizzes() {
      if (!subjectId) return
      setIsLoadingQuizzes(true)
      try {
        const list = await getPublishedQuizzes(subjectId)
        if (isMounted) {
          setPublishedQuizzes(list)
          setSelectedQuizId(list[0]?.quiz_id ?? '')
        }
      } catch (requestError) {
        if (isMounted) {
          setTakeError(
            requestError instanceof Error
              ? requestError.message
              : 'Không thể tải danh sách đề kiểm tra đã phát hành',
          )
        }
      } finally {
        if (isMounted) {
          setIsLoadingQuizzes(false)
        }
      }
    }

    void fetchInitialQuizzes()

    return () => {
      isMounted = false
    }
  }, [subjectId])

  useEffect(() => {
    let isMounted = true

    async function loadDetail() {
      if (!selectedQuizId) {
        setActiveQuiz(null)
        return
      }

      setIsLoadingQuizDetail(true)
      setTakeError(null)

      try {
        const detail = await getPublishedQuizDetail(selectedQuizId)
        if (isMounted) {
          setActiveQuiz(detail)
          setSelectedOptionMap({})
          setSubmittedResult(null)
        }
      } catch (requestError) {
        if (isMounted) {
          setTakeError(
            requestError instanceof Error
              ? requestError.message
              : 'Không thể tải chi tiết câu hỏi của đề kiểm tra',
          )
        }
      } finally {
        if (isMounted) {
          setIsLoadingQuizDetail(false)
        }
      }
    }

    void loadDetail()

    return () => {
      isMounted = false
    }
  }, [selectedQuizId])

  const activeDraft = draftQuizzes.find(
    (item) => item.quiz_id === selectedDraftQuizId,
  ) ?? null

  function handleSelectOption(questionId: string, optionId: string) {
    if (submittedResult) return
    setSelectedOptionMap((prev) => ({
      ...prev,
      [questionId]: optionId,
    }))
    setTakeError(null)
  }

  async function handleSubmitAttempt(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()

    if (!activeQuiz) return

    const trimmedEmployee = employeeId.trim()
    if (!trimmedEmployee) {
      setTakeError('Vui lòng nhập Mã nhân viên hoặc Họ tên trước khi nộp bài.')
      return
    }

    const unansweredCount = activeQuiz.questions.filter(
      (q) => !selectedOptionMap[q.question_id],
    ).length

    if (unansweredCount > 0) {
      setTakeError(
        `Bạn còn ${unansweredCount} câu hỏi chưa chọn đáp án. Vui lòng hoàn thành tất cả câu hỏi.`,
      )
      return
    }

    setIsSubmittingAttempt(true)
    setTakeError(null)

    try {
      const attemptStart = await startQuizAttempt(
        activeQuiz.quiz_id,
        trimmedEmployee,
      )
      const answersPayload = activeQuiz.questions.map((question) => ({
        question_id: question.question_id,
        option_id: selectedOptionMap[question.question_id],
      }))

      const result = await submitQuizAttempt(
        attemptStart.attempt_id,
        answersPayload,
      )

      setSubmittedResult(result)
      recordCompletedAttempt({
        ...result,
        quiz_title: activeQuiz.title,
        subject_id: subjectId,
        subject_name: subjectName || 'Chuyên mục chính sách',
        completed_at: new Date().toISOString(),
      })
      onAttemptSubmitted()
    } catch (requestError) {
      setTakeError(
        requestError instanceof Error
          ? requestError.message
          : 'Không thể nộp bài kiểm tra. Vui lòng thử lại.',
      )
    } finally {
      setIsSubmittingAttempt(false)
    }
  }

  function handleResetAttempt() {
    setSelectedOptionMap({})
    setSubmittedResult(null)
    setTakeError(null)
  }

  async function handleCreateDraftQuiz(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setAuthorFeedback(null)
    setAuthorError(null)

    const trimmedTitle = newQuizTitle.trim()
    if (!trimmedTitle) {
      setAuthorError('Vui lòng nhập tiêu đề đề kiểm tra onboarding.')
      return
    }

    setIsCreatingQuiz(true)
    try {
      const created = await createDraftQuiz(subjectId, trimmedTitle)
      const draftSession: DraftQuizSession = {
        quiz_id: created.quiz_id,
        subject_id: created.subject_id,
        title: created.title,
        status: 'DRAFT',
        questions: [],
      }
      saveDraftQuizSession(draftSession)
      const nextDrafts = getSavedDraftQuizzes(subjectId)
      setDraftQuizzes(nextDrafts)
      setSelectedDraftQuizId(created.quiz_id)
      setNewQuizTitle('')
      setAuthorFeedback(
        `Đã khởi tạo đề nháp "${created.title}". Hãy thêm câu hỏi gắn nguồn văn bản rồi bấm Phát hành.`,
      )
    } catch (requestError) {
      setAuthorError(
        requestError instanceof Error
          ? requestError.message
          : 'Không thể tạo đề kiểm tra nháp',
      )
    } finally {
      setIsCreatingQuiz(false)
    }
  }

  async function handleAddQuestion(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setAuthorFeedback(null)
    setAuthorError(null)

    if (!activeDraft) {
      setAuthorError('Vui lòng chọn hoặc tạo một đề kiểm tra nháp trước.')
      return
    }

    if (
      !questionPrompt.trim()
      || !optionA.trim()
      || !optionB.trim()
      || !optionC.trim()
      || !optionD.trim()
    ) {
      setAuthorError('Vui lòng nhập đầy đủ nội dung câu hỏi và 4 phương án lựa chọn.')
      return
    }

    setIsAddingQuestion(true)

    try {
      const optionTexts = [optionA, optionB, optionC, optionD]
      const createdQuestion = await addQuestionToQuiz(activeDraft.quiz_id, {
        prompt: questionPrompt.trim(),
        options: optionTexts.map((text, idx) => ({
          text: text.trim(),
          is_correct: idx === correctIndex,
        })),
        source_document_id: sourceDocId || null,
        source_document_version: sourceVersion.trim() || null,
      })

      const updatedDraft: DraftQuizSession = {
        ...activeDraft,
        questions: [...activeDraft.questions, createdQuestion],
      }
      saveDraftQuizSession(updatedDraft)
      setDraftQuizzes(getSavedDraftQuizzes(subjectId))

      setQuestionPrompt('')
      setOptionA('')
      setOptionB('')
      setOptionC('')
      setOptionD('')
      setCorrectIndex(0)
      setAuthorFeedback(
        `Đã thêm câu hỏi thứ ${updatedDraft.questions.length} vào đề "${activeDraft.title}".`,
      )
    } catch (requestError) {
      setAuthorError(
        requestError instanceof Error
          ? requestError.message
          : 'Không thể thêm câu hỏi vào đề kiểm tra',
      )
    } finally {
      setIsAddingQuestion(false)
    }
  }

  async function handlePopulatePresetQuestions(targetQuizId: string) {
    if (!targetQuizId) return
    setIsPopulatingPresets(true)
    setAuthorError(null)
    setAuthorFeedback(null)

    const defaultDocId = documents[0]?.document_id ?? ''

    try {
      let currentDraft = draftQuizzes.find((d) => d.quiz_id === targetQuizId)
      if (!currentDraft) {
        setAuthorError('Không tìm thấy đề nháp để nạp câu hỏi.')
        return
      }

      for (const preset of SAMPLE_ONBOARDING_PRESETS) {
        const createdQuestion = await addQuestionToQuiz(targetQuizId, {
          prompt: preset.prompt,
          options: preset.options,
          source_document_id: defaultDocId || null,
          source_document_version: preset.version,
        })
        currentDraft = {
          ...currentDraft,
          questions: [...currentDraft.questions, createdQuestion],
        }
        saveDraftQuizSession(currentDraft)
      }

      setDraftQuizzes(getSavedDraftQuizzes(subjectId))
      setAuthorFeedback(
        `Đã nạp thành công bộ 3 câu hỏi mẫu vào đề "${currentDraft.title}". Bạn có thể bấm "Phát hành đề" ngay bên dưới!`,
      )
    } catch (requestError) {
      setAuthorError(
        requestError instanceof Error
          ? requestError.message
          : 'Không thể nạp bộ câu hỏi mẫu tự động',
      )
    } finally {
      setIsPopulatingPresets(false)
    }
  }

  function handleFillPresetIntoForm(index: number) {
    const preset = SAMPLE_ONBOARDING_PRESETS[index]
    if (!preset) return
    setQuestionPrompt(preset.prompt)
    setOptionA(preset.options[0]?.text ?? '')
    setOptionB(preset.options[1]?.text ?? '')
    setOptionC(preset.options[2]?.text ?? '')
    setOptionD(preset.options[3]?.text ?? '')
    const correctIdx = preset.options.findIndex((o) => o.is_correct)
    setCorrectIndex(correctIdx >= 0 ? correctIdx : 0)
    setSourceVersion(preset.version)
    if (!sourceDocId && documents[0]) {
      setSourceDocId(documents[0].document_id)
    }
    setAuthorError(null)
    setAuthorFeedback(
      `Đã điền câu hỏi mẫu ${index + 1} vào form. Bạn có thể kiểm tra và bấm "+ Thêm câu hỏi vào đề nháp".`,
    )
  }

  async function handleQuickCreateAndPopulate() {
    if (!subjectId) {
      setAuthorError('Hãy chọn chuyên mục onboarding trước khi tạo đề.')
      return
    }
    setIsCreatingQuiz(true)
    setAuthorFeedback(null)
    setAuthorError(null)

    try {
      const title = 'Kiểm tra nhận thức Quy định & Bảo mật Onboarding 2026'
      const created = await createDraftQuiz(subjectId, title)
      const draftSession: DraftQuizSession = {
        quiz_id: created.quiz_id,
        subject_id: created.subject_id,
        title: created.title,
        status: 'DRAFT',
        questions: [],
      }
      saveDraftQuizSession(draftSession)
      setDraftQuizzes(getSavedDraftQuizzes(subjectId))
      setSelectedDraftQuizId(created.quiz_id)

      await handlePopulatePresetQuestions(created.quiz_id)
    } catch (requestError) {
      setAuthorError(
        requestError instanceof Error
          ? requestError.message
          : 'Không thể tạo đề mẫu tự động',
      )
    } finally {
      setIsCreatingQuiz(false)
    }
  }

  async function handlePublishDraft(quizId: string) {
    setAuthorFeedback(null)
    setAuthorError(null)
    setIsPublishingQuiz(true)

    try {
      await publishDraftQuiz(quizId)
      removeDraftQuizSession(quizId)
      const nextDrafts = getSavedDraftQuizzes(subjectId)
      setDraftQuizzes(nextDrafts)
      setSelectedDraftQuizId(nextDrafts[0]?.quiz_id ?? '')
      await loadQuizzesForSubject(subjectId)
      setAuthorFeedback(
        'Đã phát hành đề kiểm tra chính thức! Nhân viên mới có thể làm bài ngay ở khu vực Nhân viên.',
      )
    } catch (requestError) {
      setAuthorError(
        requestError instanceof Error
          ? requestError.message
          : 'Không thể phát hành đề kiểm tra (cần ít nhất 1 câu hỏi hợp lệ).',
      )
    } finally {
      setIsPublishingQuiz(false)
    }
  }

  function resolveDocumentLabel(docId: string | null): string {
    if (!docId) return 'Chính sách nội bộ'
    const found = documents.find((d) => d.document_id === docId)
    return found ? found.filename : `Doc ID: ${docId.slice(0, 8)}...`
  }

  return (
    <div className="quiz-workspace">
      {!isDemoMode && !fixedMode && (
        <div className="workspace-tabs" role="tablist" aria-label="Chế độ kiểm tra chính sách">
          <button
            role="tab"
            type="button"
            aria-selected={mode === 'take'}
            className={mode === 'take' ? 'active' : ''}
            onClick={() => setInternalMode('take')}
          >
            Nhân viên làm bài ({publishedQuizzes.length} đề đang mở)
          </button>
          <button
            role="tab"
            type="button"
            aria-selected={mode === 'review'}
            className={mode === 'review' ? 'active' : ''}
            onClick={() => setInternalMode('review')}
          >
            Biên soạn & Phát hành đề ({draftQuizzes.length} bản nháp)
          </button>
        </div>
      )}

      {mode === 'take' ? (
        <div className="quiz-take-container">
          <div className="chat-scope-banner quiz-scope-banner">
            <span className="chat-context-icon" aria-hidden="true">✓</span>
            <div className="chat-scope-copy">
              <span>Bài kiểm tra nhận thức chính sách bắt buộc</span>
              <strong>{subjectName || 'Chưa chọn chuyên mục'}</strong>
              <p>
                Chỉ các đề kiểm tra ở trạng thái Đã phát hành (PUBLISHED) trong PostgreSQL mới hiển thị cho nhân viên mới.
              </p>
            </div>
            {publishedQuizzes.length > 0 && (
              <div className="quiz-selector-box">
                <label htmlFor="published-quiz-select">Chọn đề kiểm tra</label>
                <select
                  id="published-quiz-select"
                  value={selectedQuizId}
                  onChange={(e) => setSelectedQuizId(e.target.value)}
                  disabled={isLoadingQuizzes}
                >
                  {publishedQuizzes.map((q) => (
                    <option key={q.quiz_id} value={q.quiz_id}>
                      {q.title} ({q.question_count} câu)
                    </option>
                  ))}
                </select>
              </div>
            )}
          </div>

          {isLoadingQuizzes || isLoadingQuizDetail ? (
            <section className="document-panel">
              <div className="state-message">
                <strong>Đang tải đề kiểm tra chính sách...</strong>
                <span>Đồng bộ câu hỏi đã duyệt từ máy chủ PostgreSQL.</span>
              </div>
            </section>
          ) : !activeQuiz || activeQuiz.questions.length === 0 ? (
            <section className="document-panel">
              <div className="state-message">
                <strong>Chưa có đề kiểm tra nào được phát hành cho chuyên mục này</strong>
                <span>
                  Người phụ trách đào tạo cần tạo đề và duyệt câu hỏi trước khi nhân viên mới có thể làm bài.
                </span>
              </div>
            </section>
          ) : submittedResult ? (() => {
            const displayScore =
              submittedResult.score <= 1.0
                ? Math.round(submittedResult.score * 100)
                : Math.round(submittedResult.score)
            const isPassed = displayScore >= 80

            return (
              <section className="quiz-result-panel" aria-live="polite">
                <div className="summary-grid quiz-score-summary">
                  <article className="summary-card">
                    <span>Nhân viên thực hiện</span>
                    <strong className="quiz-employee-title">{submittedResult.employee_id}</strong>
                    <small>Mã lượt làm: {submittedResult.attempt_id.slice(0, 8)}</small>
                  </article>
                  <article className="summary-card success-card">
                    <span>Điểm số đạt được</span>
                    <strong>{displayScore}%</strong>
                    <small>
                      Đúng {submittedResult.correct_count} / {submittedResult.total_questions} câu hỏi
                    </small>
                  </article>
                  <article className="summary-card processing-card">
                    <span>Trạng thái chấm</span>
                    <strong className={isPassed ? 'quiz-pass-text' : 'quiz-fail-text'}>
                      {isPassed ? 'ĐẠT YÊU CẦU' : 'CẦN ÔN LẠI'}
                    </strong>
                    <small>Trạng thái lưu: {submittedResult.status}</small>
                  </article>
                </div>

                <div className="quiz-review-list">
                  <div className="panel-heading">
                    <div>
                      <span className="panel-kicker">Chi tiết kết quả & đối chiếu nguồn</span>
                      <h2>Đáp án và văn bản chính sách dẫn chiếu</h2>
                    </div>
                    <button
                      className="secondary-button"
                      type="button"
                      onClick={handleResetAttempt}
                    >
                      Làm lượt mới
                    </button>
                  </div>

                  <ol className="quiz-graded-items">
                    {activeQuiz.questions.map((q, index) => {
                      const answerOutcome = submittedResult.answers.find(
                        (a) => a.question_id === q.question_id,
                      )
                      const isCorrect = answerOutcome?.is_correct ?? false
                      const pickedOption = q.options.find(
                        (o) => o.option_id === answerOutcome?.selected_option_id,
                      )
                      const rightOption = q.options.find(
                        (o) => o.option_id === answerOutcome?.correct_option_id,
                      )

                      return (
                        <li
                          key={q.question_id}
                          className={`quiz-graded-card ${isCorrect ? 'is-correct' : 'is-wrong'}`}
                        >
                          <div className="quiz-graded-header">
                            <span className="quiz-question-number">Câu {index + 1}</span>
                            <span className={`status ${isCorrect ? 'status-indexed' : 'status-failed'}`}>
                              {isCorrect ? 'Chính xác' : 'Chưa đúng'}
                            </span>
                          </div>
                          <p className="quiz-graded-question">{q.prompt}</p>
                          <div className="quiz-graded-meta">
                            <span>
                              Bạn chọn:{' '}
                              <strong>
                                {pickedOption ? pickedOption.text : 'Không xác định'}
                              </strong>
                            </span>
                            {!isCorrect && rightOption && (
                              <span>
                                Đáp án đúng:{' '}
                                <strong>{rightOption.text}</strong>
                              </span>
                            )}
                          </div>
                          <div className="quiz-source-pill">
                            <span>Nguồn đối chiếu:</span>
                            <strong>{resolveDocumentLabel(q.source_document_id)}</strong>
                            {q.source_document_version && (
                              <code>Phiên bản {q.source_document_version}</code>
                            )}
                          </div>
                        </li>
                      )
                    })}
                  </ol>
                </div>
              </section>
            )
          })() : (
            <form className="quiz-take-form" onSubmit={(e) => void handleSubmitAttempt(e)}>
              <div className="quiz-employee-bar">
                <label className="field" htmlFor="employee-identifier">
                  <span>Mã nhân viên / Họ và tên người làm bài</span>
                  <input
                    id="employee-identifier"
                    type="text"
                    placeholder="VD: NV-2026-018 — Nguyễn Văn An (Product Engineer)"
                    value={employeeId}
                    onChange={(e) => setEmployeeId(e.target.value)}
                  />
                </label>
                <div className="quiz-progress-box">
                  <span>Tiến độ trả lời</span>
                  <strong>
                    {Object.keys(selectedOptionMap).length} / {activeQuiz.questions.length} câu
                  </strong>
                </div>
              </div>

              {takeError && (
                <p className="form-message error-message" role="alert">
                  {takeError}
                </p>
              )}

              <ol className="quiz-question-list">
                {activeQuiz.questions.map((q, index) => {
                  const chosenOptionId = selectedOptionMap[q.question_id]

                  return (
                    <li key={q.question_id} className="quiz-question-card">
                      <div className="quiz-question-top">
                        <span className="quiz-question-number">Câu {index + 1}</span>
                        <span className="quiz-lineage-tag">
                          Nguồn: {resolveDocumentLabel(q.source_document_id)}
                          {q.source_document_version ? ` · ${q.source_document_version}` : ''}
                        </span>
                      </div>

                      <h3 className="quiz-question-title">{q.prompt}</h3>

                      <div
                        className="quiz-options-grid"
                        role="radiogroup"
                        aria-label={`Câu ${index + 1}`}
                      >
                        {q.options.map((opt, optIdx) => {
                          const isSelected = chosenOptionId === opt.option_id
                          const keyLabel = POSITION_KEYS[optIdx] ?? String(opt.position)

                          return (
                            <button
                              key={opt.option_id}
                              type="button"
                              role="radio"
                              aria-checked={isSelected}
                              className={`quiz-option-row ${isSelected ? 'is-selected' : ''}`}
                              onClick={() => handleSelectOption(q.question_id, opt.option_id)}
                            >
                              <span className="quiz-option-key">{keyLabel}</span>
                              <span className="quiz-option-text">{opt.text}</span>
                            </button>
                          )
                        })}
                      </div>
                    </li>
                  )
                })}
              </ol>

              <div className="quiz-submit-bar">
                <span>
                  Kết quả bài làm được chấm trực tiếp trên máy chủ và lưu vào lịch sử đào tạo của doanh nghiệp.
                </span>
                <button
                  className="primary-button quiz-submit-button"
                  type="submit"
                  disabled={isSubmittingAttempt}
                >
                  {isSubmittingAttempt
                    ? 'Đang chấm điểm...'
                    : 'Nộp bài & Chấm điểm ngay'}
                </button>
              </div>
            </form>
          )}
        </div>
      ) : (
        <div className="quiz-author-container">
          <section className="upload-panel">
            <div className="upload-heading">
              <div>
                <span className="panel-kicker">Bước 1 · Khởi tạo đề kiểm tra nháp (DRAFT)</span>
                <h2>Tạo đề kiểm tra cho {subjectName}</h2>
                <p>
                  Đề kiểm tra mới luôn bắt đầu ở trạng thái Nháp (DRAFT) để người phụ trách rà soát câu hỏi trước khi phát hành cho nhân viên.
                </p>
              </div>
            </div>

            <form className="subject-create-form" onSubmit={(e) => void handleCreateDraftQuiz(e)}>
              <label className="field" htmlFor="new-quiz-title">
                <span>Tiêu đề đề kiểm tra onboarding</span>
                <input
                  id="new-quiz-title"
                  type="text"
                  placeholder="VD: Kiểm tra nhận thức Bảo mật & Nghỉ phép năm 2026"
                  value={newQuizTitle}
                  onChange={(e) => setNewQuizTitle(e.target.value)}
                  disabled={isCreatingQuiz || isPopulatingPresets || !subjectId}
                />
              </label>
              <div className="quiz-table-actions">
                <button
                  className="primary-button"
                  type="submit"
                  disabled={isCreatingQuiz || isPopulatingPresets || !subjectId}
                >
                  {isCreatingQuiz ? 'Đang tạo...' : 'Tạo đề nháp mới'}
                </button>
                <button
                  className="secondary-button"
                  type="button"
                  disabled={isCreatingQuiz || isPopulatingPresets || !subjectId}
                  onClick={() => void handleQuickCreateAndPopulate()}
                >
                  {isPopulatingPresets ? 'Đang nạp 3 câu hỏi...' : '⚡ Tạo đề & Nạp sẵn 3 câu hỏi mẫu'}
                </button>
              </div>
            </form>

            {authorFeedback && (
              <p className="form-message success-message" role="status">
                {authorFeedback}
              </p>
            )}
            {authorError && (
              <p className="form-message error-message" role="alert">
                {authorError}
              </p>
            )}
          </section>

          {draftQuizzes.length > 0 && (
            <section className="upload-panel">
              <div className="upload-heading">
                <div>
                  <span className="panel-kicker">Bước 2 · Biên soạn câu hỏi có gắn nguồn văn bản</span>
                  <h2>Thêm câu hỏi vào đề nháp đang chọn</h2>
                </div>

                <label className="compact-subject-field" htmlFor="draft-quiz-select">
                  <span>Đề nháp đang biên soạn</span>
                  <select
                    id="draft-quiz-select"
                    value={selectedDraftQuizId}
                    onChange={(e) => setSelectedDraftQuizId(e.target.value)}
                  >
                    {draftQuizzes.map((d) => (
                      <option key={d.quiz_id} value={d.quiz_id}>
                        {d.title} ({d.questions.length} câu)
                      </option>
                    ))}
                  </select>
                </label>
              </div>

              <div className="quick-presets-row">
                <div className="preset-quick-actions">
                  <span className="preset-label">Nạp nhanh dữ liệu:</span>
                  <button
                    type="button"
                    className="secondary-button preset-populate-btn"
                    disabled={isAddingQuestion || isPopulatingPresets || !activeDraft}
                    onClick={() => void handlePopulatePresetQuestions(activeDraft?.quiz_id ?? '')}
                  >
                    {isPopulatingPresets ? 'Đang nạp 3 câu hỏi...' : '⚡ Nạp nhanh bộ 3 câu hỏi mẫu vào đề'}
                  </button>
                </div>
                <div className="preset-fill-pills">
                  <span className="preset-label">Hoặc điền thử vào form:</span>
                  <button
                    type="button"
                    className="prompt-pill"
                    onClick={() => handleFillPresetIntoForm(0)}
                  >
                    Mẫu 1: Nghỉ phép &ge; 3 ngày
                  </button>
                  <button
                    type="button"
                    className="prompt-pill"
                    onClick={() => handleFillPresetIntoForm(1)}
                  >
                    Mẫu 2: Mật khẩu &amp; 2FA
                  </button>
                  <button
                    type="button"
                    className="prompt-pill"
                    onClick={() => handleFillPresetIntoForm(2)}
                  >
                    Mẫu 3: Chế độ Hybrid
                  </button>
                </div>
              </div>

              <form className="quiz-author-form" onSubmit={(e) => void handleAddQuestion(e)}>
                <label className="field" htmlFor="quiz-q-prompt">
                  <span>Nội dung câu hỏi tình huống / quy định</span>
                  <input
                    id="quiz-q-prompt"
                    type="text"
                    placeholder="VD: Theo quy định hiện hành, nhân viên cần báo trước bao lâu khi xin nghỉ phép từ 3 ngày trở lên?"
                    value={questionPrompt}
                    onChange={(e) => setQuestionPrompt(e.target.value)}
                  />
                </label>

                <div className="quiz-author-options-grid">
                  <label className="field" htmlFor="quiz-opt-a">
                    <span>Phương án A</span>
                    <input
                      id="quiz-opt-a"
                      type="text"
                      placeholder="Nhập phương án A..."
                      value={optionA}
                      onChange={(e) => setOptionA(e.target.value)}
                    />
                  </label>
                  <label className="field" htmlFor="quiz-opt-b">
                    <span>Phương án B</span>
                    <input
                      id="quiz-opt-b"
                      type="text"
                      placeholder="Nhập phương án B..."
                      value={optionB}
                      onChange={(e) => setOptionB(e.target.value)}
                    />
                  </label>
                  <label className="field" htmlFor="quiz-opt-c">
                    <span>Phương án C</span>
                    <input
                      id="quiz-opt-c"
                      type="text"
                      placeholder="Nhập phương án C..."
                      value={optionC}
                      onChange={(e) => setOptionC(e.target.value)}
                    />
                  </label>
                  <label className="field" htmlFor="quiz-opt-d">
                    <span>Phương án D</span>
                    <input
                      id="quiz-opt-d"
                      type="text"
                      placeholder="Nhập phương án D..."
                      value={optionD}
                      onChange={(e) => setOptionD(e.target.value)}
                    />
                  </label>
                </div>

                <div className="quiz-author-meta-row">
                  <label className="field" htmlFor="quiz-correct-idx">
                    <span>Đáp án đúng</span>
                    <select
                      id="quiz-correct-idx"
                      value={correctIndex}
                      onChange={(e) => setCorrectIndex(Number(e.target.value))}
                    >
                      <option value={0}>Phương án A</option>
                      <option value={1}>Phương án B</option>
                      <option value={2}>Phương án C</option>
                      <option value={3}>Phương án D</option>
                    </select>
                  </label>

                  <label className="field" htmlFor="quiz-source-doc">
                    <span>Văn bản chính sách gốc (Lineage)</span>
                    <select
                      id="quiz-source-doc"
                      value={sourceDocId}
                      onChange={(e) => setSourceDocId(e.target.value)}
                    >
                      <option value="">-- Chọn văn bản nguồn --</option>
                      {documents.map((doc) => (
                        <option key={doc.document_id} value={doc.document_id}>
                          {doc.filename}
                        </option>
                      ))}
                    </select>
                  </label>

                  <label className="field" htmlFor="quiz-source-ver">
                    <span>Phiên bản / Điều khoản</span>
                    <input
                      id="quiz-source-ver"
                      type="text"
                      placeholder="VD: v2.0 - Điều 4"
                      value={sourceVersion}
                      onChange={(e) => setSourceVersion(e.target.value)}
                    />
                  </label>
                </div>

                <div className="quiz-author-actions">
                  <button
                    className="secondary-button"
                    type="submit"
                    disabled={isAddingQuestion || isPopulatingPresets}
                  >
                    {isAddingQuestion ? 'Đang lưu câu hỏi...' : '+ Thêm câu hỏi vào đề nháp'}
                  </button>
                  {activeDraft && activeDraft.questions.length > 0 && (
                    <button
                      className="primary-button"
                      type="button"
                      disabled={isPublishingQuiz || isPopulatingPresets}
                      onClick={() => void handlePublishDraft(activeDraft.quiz_id)}
                    >
                      {isPublishingQuiz
                        ? 'Đang phát hành...'
                        : `Phát hành đề "${activeDraft.title}" (${activeDraft.questions.length} câu)`}
                    </button>
                  )}
                </div>
              </form>
            </section>
          )}

          <section className="document-panel">
            <div className="panel-heading">
              <div>
                <span className="panel-kicker">Danh sách đề kiểm tra trên hệ thống</span>
                <h2>Đề đã phát hành ({publishedQuizzes.length}) & Đề nháp ({draftQuizzes.length})</h2>
              </div>
            </div>

            {publishedQuizzes.length === 0 && draftQuizzes.length === 0 ? (
              <p className="state-message">Chưa có đề kiểm tra nào trong chuyên mục này.</p>
            ) : (
              <div className="table-wrapper">
                <table>
                  <thead>
                    <tr>
                      <th>Tiêu đề đề kiểm tra</th>
                      <th>Số câu hỏi</th>
                      <th>Trạng thái</th>
                      <th>Mã định danh (Quiz ID)</th>
                      <th>Thao tác</th>
                    </tr>
                  </thead>
                  <tbody>
                    {draftQuizzes.map((draft) => (
                      <tr key={draft.quiz_id}>
                        <td>
                          <strong>{draft.title}</strong>
                          <span className="document-type">Bản nháp đang biên soạn</span>
                        </td>
                        <td>{draft.questions.length} câu</td>
                        <td>
                          <span className="status status-processing">Chờ duyệt (DRAFT)</span>
                        </td>
                        <td>
                          <code>{draft.quiz_id.slice(0, 12)}...</code>
                        </td>
                        <td className="actions quiz-table-actions">
                          <button
                            type="button"
                            className="primary-button"
                            disabled={draft.questions.length === 0 || isPublishingQuiz}
                            onClick={() => void handlePublishDraft(draft.quiz_id)}
                          >
                            Phát hành ngay
                          </button>
                        </td>
                      </tr>
                    ))}
                    {publishedQuizzes.map((pub) => (
                      <tr key={pub.quiz_id}>
                        <td>
                          <strong>{pub.title}</strong>
                          <span className="document-type">Đề chính thức cho nhân viên</span>
                        </td>
                        <td>{pub.question_count} câu</td>
                        <td>
                          <span className="status status-indexed">Đã phát hành (PUBLISHED)</span>
                        </td>
                        <td>
                          <code>{pub.quiz_id.slice(0, 12)}...</code>
                        </td>
                        <td className="actions quiz-table-actions">
                          <span className="version-pill">Sẵn sàng phục vụ nhân viên</span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </section>
        </div>
      )}
    </div>
  )
}

export default OnboardingQuizPanel
