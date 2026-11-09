import { useMemo, useState } from 'react'

import {
  getRecordedAttempts,
  type StoredAttemptHistoryItem,
} from '../services/onboardingStore'

interface MyResultsPanelProps {
  onGoToQuiz: () => void
}

function formatDateTime(iso: string): string {
  return new Intl.DateTimeFormat('vi-VN', {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(new Date(iso))
}

function MyResultsPanel({ onGoToQuiz }: MyResultsPanelProps) {
  const [selectedAttemptId, setSelectedAttemptId] = useState<string | null>(
    null,
  )
  const [searchEmployee, setSearchEmployee] = useState('')

  const attempts: StoredAttemptHistoryItem[] = useMemo(() => {
    return getRecordedAttempts()
  }, [])

  const filtered = useMemo(() => {
    const q = searchEmployee.trim().toLowerCase()
    if (!q) return attempts
    return attempts.filter(
      (a) =>
        a.employee_id.toLowerCase().includes(q)
        || a.quiz_title.toLowerCase().includes(q),
    )
  }, [attempts, searchEmployee])

  const selectedAttempt = useMemo(() => {
    if (!selectedAttemptId) return filtered[0] ?? null
    return attempts.find((a) => a.attempt_id === selectedAttemptId) ?? null
  }, [attempts, filtered, selectedAttemptId])

  return (
    <div className="my-results-workspace">
      <section className="summary-grid" aria-label="Tổng kết bài kiểm tra cá nhân">
        <article className="summary-card">
          <span>Lượt làm bài đã ghi nhận</span>
          <strong>{filtered.length}</strong>
          <small>Đã hoàn thành và chấm điểm</small>
        </article>
        <article className="summary-card success-card">
          <span>Số lượt đạt chuẩn (&ge;80%)</span>
          <strong>
            {
              filtered.filter((a) => {
                const pct = a.score <= 1.0 ? a.score * 100 : a.score
                return pct >= 80
              }).length
            }
          </strong>
          <small>Đủ điều kiện nhận thức chính sách</small>
        </article>
        <article className="summary-card processing-card">
          <span>Cần ôn lại (&lt;80%)</span>
          <strong>
            {
              filtered.filter((a) => {
                const pct = a.score <= 1.0 ? a.score * 100 : a.score
                return pct < 80
              }).length
            }
          </strong>
          <small>Cần xem lại điều khoản dẫn chiếu</small>
        </article>
      </section>

      <section className="document-panel" aria-label="Lịch sử bài kiểm tra của nhân viên">
        <div className="panel-heading overview-heading">
          <div>
            <span className="panel-kicker">Hồ sơ hòa nhập & đánh giá cá nhân</span>
            <h2>Kết quả kiểm tra chính sách của bạn</h2>
            <p>
              Đối chiếu điểm số, xem lại các câu trả lời chưa đúng và các điều khoản văn bản chính sách cần đọc lại.
            </p>
          </div>

          <div className="overview-filters">
            <input
              type="search"
              placeholder="Lọc theo tên hoặc mã nhân viên..."
              value={searchEmployee}
              onChange={(e) => setSearchEmployee(e.target.value)}
            />
          </div>
        </div>

        {filtered.length === 0 ? (
          <div className="state-message">
            <strong>Chưa có bài kiểm tra nào được hoàn thành</strong>
            <span>
              Hãy chuyển sang mục &ldquo;Làm bài kiểm tra&rdquo; để thực hiện bài đánh giá nhận thức chính sách.
            </span>
            <div style={{ marginTop: '14px' }}>
              <button
                className="primary-button"
                type="button"
                onClick={onGoToQuiz}
              >
                Làm bài kiểm tra ngay
              </button>
            </div>
          </div>
        ) : (
          <div className="my-results-layout">
            <div className="table-wrapper my-results-table-col">
              <table>
                <thead>
                  <tr>
                    <th>Đề kiểm tra</th>
                    <th>Nhân viên</th>
                    <th>Điểm số</th>
                    <th>Kết quả</th>
                    <th>Thời gian nộp</th>
                    <th>Thao tác</th>
                  </tr>
                </thead>
                <tbody>
                  {filtered.map((attempt) => {
                    const pct =
                      attempt.score <= 1.0
                        ? Math.round(attempt.score * 100)
                        : Math.round(attempt.score)
                    const isPassed = pct >= 80
                    const isSelected =
                      selectedAttempt?.attempt_id === attempt.attempt_id

                    return (
                      <tr
                        key={attempt.attempt_id}
                        className={isSelected ? 'is-active-row' : ''}
                      >
                        <td>
                          <strong>{attempt.quiz_title}</strong>
                          <span className="document-type">{attempt.subject_name}</span>
                        </td>
                        <td>{attempt.employee_id}</td>
                        <td>
                          <strong>{pct}%</strong>
                          <span className="document-type">
                            {attempt.correct_count} / {attempt.total_questions} câu
                          </span>
                        </td>
                        <td>
                          <span
                            className={`status ${
                              isPassed ? 'status-indexed' : 'status-failed'
                            }`}
                          >
                            {isPassed ? 'Đạt chuẩn' : 'Cần ôn lại'}
                          </span>
                        </td>
                        <td>{formatDateTime(attempt.completed_at)}</td>
                        <td className="actions quiz-table-actions">
                          <button
                            type="button"
                            className={isSelected ? 'primary-button' : 'secondary-button'}
                            onClick={() => setSelectedAttemptId(attempt.attempt_id)}
                          >
                            {isSelected ? 'Đang xem' : 'Xem chi tiết'}
                          </button>
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>

            {selectedAttempt && (
              <div className="my-results-detail-card">
                <div className="panel-heading">
                  <div>
                    <span className="panel-kicker">Chi tiết bài làm</span>
                    <h3>{selectedAttempt.quiz_title}</h3>
                    <p>
                      Mã bài: <code>{selectedAttempt.attempt_id.slice(0, 8)}</code> · Người làm:{' '}
                      <strong>{selectedAttempt.employee_id}</strong>
                    </p>
                  </div>
                </div>

                <ol className="quiz-graded-items">
                  {selectedAttempt.answers.map((answer, index) => (
                    <li
                      key={answer.question_id}
                      className={`quiz-graded-card ${
                        answer.is_correct ? 'is-correct' : 'is-wrong'
                      }`}
                    >
                      <div className="quiz-graded-header">
                        <span className="quiz-question-number">Câu {index + 1}</span>
                        <span
                          className={`status ${
                            answer.is_correct ? 'status-indexed' : 'status-failed'
                          }`}
                        >
                          {answer.is_correct ? 'Chính xác' : 'Cần đọc lại quy định'}
                        </span>
                      </div>
                      <div className="quiz-graded-meta">
                        <span>
                          Trạng thái lựa chọn:{' '}
                          <strong>
                            {answer.is_correct
                              ? 'Bạn đã chọn đúng đáp án'
                              : 'Bạn chọn chưa đúng đáp án chuẩn'}
                          </strong>
                        </span>
                      </div>
                    </li>
                  ))}
                </ol>
              </div>
            )}
          </div>
        )}
      </section>
    </div>
  )
}

export default MyResultsPanel
