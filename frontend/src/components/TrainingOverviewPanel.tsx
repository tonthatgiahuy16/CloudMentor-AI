import { useEffect, useMemo, useState } from 'react'

import {
  getPublishedQuizzes,
  getQuizAttemptResults,
  getQuizOverview,
} from '../services/api'
import {
  getRecordedAttempts,
  type StoredAttemptHistoryItem,
} from '../services/onboardingStore'
import type {
  AttemptResult,
  QuizOverview,
  QuizSummary,
} from '../types/quiz'
import type { SubjectRecord } from '../types/subject'

interface TrainingOverviewPanelProps {
  subjects: SubjectRecord[]
  selectedSubjectId: string
  refreshKey: number
}

interface QuizOverviewRow {
  quiz: QuizSummary
  subjectName: string
  overview: QuizOverview
}

interface AttemptHistoryRow extends AttemptResult {
  subject_id: string
  quiz_title: string
  subject_name: string
  completed_at: string
}

function formatDateTime(iso: string): string {
  return new Intl.DateTimeFormat('vi-VN', {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(new Date(iso))
}

function TrainingOverviewPanel({
  subjects,
  selectedSubjectId,
  refreshKey,
}: TrainingOverviewPanelProps) {
  const [filterMode, setFilterMode] = useState<'all' | 'current'>('all')
  const [searchEmployee, setSearchEmployee] = useState('')
  const [quizRows, setQuizRows] = useState<QuizOverviewRow[]>([])
  const [serverAttempts, setServerAttempts] = useState<AttemptHistoryRow[]>([])
  const [isLoadingOverview, setIsLoadingOverview] = useState(false)
  const [overviewError, setOverviewError] = useState<string | null>(null)

  useEffect(() => {
    let isMounted = true

    async function loadServerOverview() {
      if (subjects.length === 0) {
        setQuizRows([])
        setServerAttempts([])
        return
      }

      setIsLoadingOverview(true)
      setOverviewError(null)

      try {
        const targetSubjects =
          filterMode === 'current' && selectedSubjectId
            ? subjects.filter((s) => s.subject_id === selectedSubjectId)
            : subjects

        const rows: QuizOverviewRow[] = []
        const attempts: AttemptHistoryRow[] = []

        for (const subject of targetSubjects) {
          const quizzes = await getPublishedQuizzes(subject.subject_id)
          const details = await Promise.all(
            quizzes.map(async (quiz) => {
              const [overview, quizAttempts] = await Promise.all([
                getQuizOverview(quiz.quiz_id),
                getQuizAttemptResults(quiz.quiz_id),
              ])
              return {
                row: {
                  quiz,
                  subjectName: subject.name,
                  overview,
                } satisfies QuizOverviewRow,
                attempts: quizAttempts.map(
                  (attempt): AttemptHistoryRow => ({
                    ...attempt,
                    subject_id: subject.subject_id,
                    quiz_title: quiz.title,
                    subject_name: subject.name,
                    completed_at:
                      attempt.graded_at ?? new Date(0).toISOString(),
                  }),
                ),
              }
            }),
          )

          for (const detail of details) {
            rows.push(detail.row)
            attempts.push(...detail.attempts)
          }
        }

        if (isMounted) {
          setQuizRows(rows)
          setServerAttempts(attempts)
        }
      } catch (requestError) {
        if (isMounted) {
          setOverviewError(
            requestError instanceof Error
              ? requestError.message
              : 'Không thể tải báo cáo tổng quan từ máy chủ',
          )
        }
      } finally {
        if (isMounted) {
          setIsLoadingOverview(false)
        }
      }
    }

    void loadServerOverview()

    return () => {
      isMounted = false
    }
  }, [subjects, selectedSubjectId, filterMode, refreshKey])

  const recordedAttempts: StoredAttemptHistoryItem[] = useMemo(() => {
    void refreshKey
    return getRecordedAttempts()
  }, [refreshKey])

  const mergedAttempts = useMemo(() => {
    const byId = new Map<string, AttemptHistoryRow>()

    for (const attempt of serverAttempts) {
      byId.set(attempt.attempt_id, attempt)
    }

    // Local records are a fallback for attempts submitted before the
    // server-side history endpoint existed. Server data always wins.
    for (const attempt of recordedAttempts) {
      if (!byId.has(attempt.attempt_id)) {
        byId.set(attempt.attempt_id, attempt)
      }
    }

    return [...byId.values()].sort(
      (left, right) =>
        new Date(right.completed_at).getTime()
        - new Date(left.completed_at).getTime(),
    )
  }, [serverAttempts, recordedAttempts])

  const filteredAttempts = useMemo(() => {
    return mergedAttempts.filter((attempt) => {
      const matchesSubject =
        filterMode === 'all' || attempt.subject_id === selectedSubjectId
      const matchesSearch =
        !searchEmployee.trim()
        || attempt.employee_id
          .toLowerCase()
          .includes(searchEmployee.trim().toLowerCase())
        || attempt.quiz_title
          .toLowerCase()
          .includes(searchEmployee.trim().toLowerCase())
      return matchesSubject && matchesSearch
    })
  }, [mergedAttempts, filterMode, selectedSubjectId, searchEmployee])

  const aggregateStats = useMemo(() => {
    const totalServerAttempts = quizRows.reduce(
      (sum, item) => sum + item.overview.attempt_count,
      0,
    )
    const totalGraded = quizRows.reduce(
      (sum, item) => sum + item.overview.graded_attempt_count,
      0,
    )

    const weightedScoreSum = quizRows.reduce(
      (sum, item) =>
        sum
        + (item.overview.average_score ?? 0)
          * item.overview.graded_attempt_count,
      0,
    )

    const rawAvg =
      totalGraded > 0 ? weightedScoreSum / totalGraded : 0
    const avgScore =
      rawAvg <= 1.0 ? Math.round(rawAvg * 100) : Math.round(rawAvg)

    return {
      publishedQuizCount: quizRows.length,
      totalServerAttempts,
      totalGraded,
      avgScore,
    }
  }, [quizRows])

  return (
    <div className="overview-workspace">
      <section className="summary-grid" aria-label="Chỉ số tổng quan đào tạo từ PostgreSQL">
        <article className="summary-card">
          <span>Đề đã phát hành & lượt làm</span>
          <strong>{aggregateStats.totalGraded}</strong>
          <small>
            Trên tổng số {aggregateStats.publishedQuizCount} đề chính thức ({aggregateStats.totalServerAttempts} lượt mở đề)
          </small>
        </article>
        <article className="summary-card success-card">
          <span>Điểm trung bình toàn đơn vị</span>
          <strong>{aggregateStats.avgScore}%</strong>
          <small>Tổng hợp trực tiếp từ API /quizzes/&#123;id&#125;/overview</small>
        </article>
        <article className="summary-card processing-card">
          <span>Lượt chấm lưu chi tiết tại phiên</span>
          <strong>{filteredAttempts.length}</strong>
          <small>Đối chiếu kết quả từng nhân viên mới</small>
        </article>
      </section>

      {overviewError && (
        <div className="error-banner" role="alert">
          <span>{overviewError}</span>
        </div>
      )}

      <section className="document-panel" aria-label="Thống kê theo đề kiểm tra từ máy chủ">
        <div className="panel-heading overview-heading">
          <div>
            <span className="panel-kicker">PostgreSQL Aggregated Metrics</span>
            <h2>Báo cáo hoàn thành theo đề kiểm tra chính sách</h2>
            <p>
              Số liệu tổng hợp trực tiếp từ bảng lượt làm bài trên máy chủ cho từng đề kiểm tra đã phát hành.
            </p>
          </div>

          <div className="overview-filters">
            <select
              aria-label="Phạm vi chuyên mục"
              value={filterMode}
              onChange={(e) => setFilterMode(e.target.value as 'all' | 'current')}
            >
              <option value="all">Tất cả chuyên mục ({subjects.length})</option>
              <option value="current">Chỉ chuyên mục đang chọn</option>
            </select>
          </div>
        </div>

        {isLoadingOverview ? (
          <div className="state-message">
            <strong>Đang tải thống kê từ máy chủ...</strong>
            <span>Đang tổng hợp số lượt hoàn thành và điểm số trung bình.</span>
          </div>
        ) : quizRows.length === 0 ? (
          <div className="state-message">
            <strong>Chưa có đề kiểm tra nào được phát hành</strong>
            <span>Hãy phát hành ít nhất một đề kiểm tra ở mục Kiểm tra Onboarding để xem thống kê.</span>
          </div>
        ) : (
          <div className="table-wrapper">
            <table>
              <thead>
                <tr>
                  <th>Đề kiểm tra chính sách</th>
                  <th>Chuyên mục</th>
                  <th>Số câu hỏi</th>
                  <th>Lượt bắt đầu</th>
                  <th>Lượt đã chấm (GRADED)</th>
                  <th>Điểm trung bình</th>
                </tr>
              </thead>
              <tbody>
                {quizRows.map(({ quiz, subjectName, overview }) => (
                  <tr key={quiz.quiz_id}>
                    <td>
                      <strong>{quiz.title}</strong>
                      <span className="document-type">ID: {quiz.quiz_id.slice(0, 8)}</span>
                    </td>
                    <td>{subjectName}</td>
                    <td>{quiz.question_count} câu</td>
                    <td>{overview.attempt_count} lượt</td>
                    <td>
                      <span className="version-pill">
                        {overview.graded_attempt_count} lượt hoàn thành
                      </span>
                    </td>
                    <td>
                      {overview.average_score !== null ? (() => {
                        const rowPercent =
                          overview.average_score <= 1.0
                            ? Math.round(overview.average_score * 100)
                            : Math.round(overview.average_score)
                        return (
                          <span
                            className={`status ${
                              rowPercent >= 80
                                ? 'status-indexed'
                                : 'status-processing'
                            }`}
                          >
                            {rowPercent}%
                          </span>
                        )
                      })() : (
                        <span className="status status-deleted">Chưa có bài nộp</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      <section className="document-panel" aria-label="Bảng kết quả chi tiết của nhân viên">
        <div className="panel-heading overview-heading">
          <div>
            <span className="panel-kicker">Nhật ký bài nộp gần đây</span>
            <h2>Chi tiết lượt hoàn thành của nhân viên mới</h2>
            <p>
              Ghi nhận các bài kiểm tra vừa thực hiện để người phụ trách đối chiếu điểm số và câu trả lời.
            </p>
          </div>

          <div className="overview-filters">
            <input
              type="search"
              placeholder="Tìm theo mã/tên nhân viên hoặc tên đề..."
              value={searchEmployee}
              onChange={(e) => setSearchEmployee(e.target.value)}
            />
          </div>
        </div>

        {filteredAttempts.length === 0 ? (
          <div className="state-message">
            <strong>Chưa có bài nộp chi tiết trong bộ lọc này</strong>
            <span>Khi nhân viên mới hoàn thành bài kiểm tra, kết quả chi tiết sẽ hiển thị tại đây.</span>
          </div>
        ) : (
          <div className="table-wrapper">
            <table>
              <thead>
                <tr>
                  <th>Nhân viên mới</th>
                  <th>Đề kiểm tra</th>
                  <th>Chuyên mục</th>
                  <th>Số câu đúng</th>
                  <th>Điểm số</th>
                  <th>Đánh giá</th>
                  <th>Thời gian nộp</th>
                </tr>
              </thead>
              <tbody>
                {filteredAttempts.map((attempt) => {
                  const percentScore =
                    attempt.score <= 1.0
                      ? Math.round(attempt.score * 100)
                      : Math.round(attempt.score)
                  const passed = percentScore >= 80
                  return (
                    <tr key={attempt.attempt_id}>
                      <td>
                        <strong>{attempt.employee_id}</strong>
                        <span className="document-type">
                          Mã bài làm: {attempt.attempt_id.slice(0, 8)}
                        </span>
                      </td>
                      <td>{attempt.quiz_title}</td>
                      <td>{attempt.subject_name}</td>
                      <td>
                        <span className="version-pill">
                          {attempt.correct_count} / {attempt.total_questions} câu
                        </span>
                      </td>
                      <td>
                        <strong>{percentScore}%</strong>
                      </td>
                      <td>
                        <span
                          className={`status ${
                            passed ? 'status-indexed' : 'status-failed'
                          }`}
                        >
                          {passed ? 'Đạt chuẩn (≥80%)' : 'Cần học lại (<80%)'}
                        </span>
                      </td>
                      <td>{formatDateTime(attempt.completed_at)}</td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  )
}

export default TrainingOverviewPanel
