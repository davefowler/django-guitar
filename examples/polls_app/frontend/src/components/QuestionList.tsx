import './QuestionList.css'

interface QuestionListProps {
  questions: Array<{ id: number; question_text: string; pub_date: string }>
  loading: boolean
  onQuestionClick: (questionId: number) => void
  onRefresh: () => void
}

function QuestionList({ questions, loading, onQuestionClick, onRefresh }: QuestionListProps): JSX.Element {
  const formatDate = (dateString: string): string => {
    const date = new Date(dateString)
    return date.toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    })
  }

  if (loading) {
    return (
      <div className="question-list">
        <div className="loading">Loading questions...</div>
      </div>
    )
  }

  if (questions.length === 0) {
    return (
      <div className="question-list">
        <div className="empty-state">
          <h2>No questions yet</h2>
          <p>Create your first poll question to get started!</p>
        </div>
      </div>
    )
  }

  return (
    <div className="question-list">
      <div className="question-list-header">
        <h2>Published Questions</h2>
        <button onClick={onRefresh} className="refresh-button">
          Refresh
        </button>
      </div>
      <div className="questions-grid">
        {questions.map((question) => (
          <div
            key={question.id}
            className="question-card"
            onClick={() => onQuestionClick(question.id)}
          >
            <h3>{question.question_text}</h3>
            <p className="question-date">Published: {formatDate(question.pub_date)}</p>
            <div className="question-arrow">→</div>
          </div>
        ))}
      </div>
    </div>
  )
}

export default QuestionList

