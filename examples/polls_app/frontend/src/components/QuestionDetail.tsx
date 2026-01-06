import { useState, useEffect } from 'react'
import { Question, Choice } from '../guitar'
import './QuestionDetail.css'

interface QuestionDetailProps {
  questionId: number
  onBack: () => void
  onVote: (choiceId: number) => void
}

interface ChoiceType {
  id: number
  choice_text: string
  votes: number
  question_id: number
}

function QuestionDetail({ questionId, onBack, onVote }: QuestionDetailProps): JSX.Element {
  const [question, setQuestion] = useState<{ id: number; question_text: string; pub_date: string } | null>(null)
  const [choices, setChoices] = useState<ChoiceType[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    loadQuestion()
  }, [questionId])

  const loadQuestion = async (): Promise<void> => {
    try {
      setLoading(true)
      setError(null)
      
      // Load question
      const questionData = await Question.objects.get({ id: questionId })
      setQuestion(questionData)
      
      // Load choices for this question
      const choicesData = await Choice.objects.filter({ question_id: questionId })
      setChoices(choicesData.sort((a, b) => b.votes - a.votes))
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load question')
      console.error('Error loading question:', err)
    } finally {
      setLoading(false)
    }
  }

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

  const totalVotes = choices.reduce((sum, choice) => sum + choice.votes, 0)

  if (loading) {
    return (
      <div className="question-detail">
        <div className="loading">Loading question...</div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="question-detail">
        <div className="error-message">
          <p>{error}</p>
          <button onClick={onBack}>Go Back</button>
        </div>
      </div>
    )
  }

  if (!question) {
    return (
      <div className="question-detail">
        <div className="error-message">
          <p>Question not found</p>
          <button onClick={onBack}>Go Back</button>
        </div>
      </div>
    )
  }

  return (
    <div className="question-detail">
      <button onClick={onBack} className="back-button">
        ← Back to Questions
      </button>

      <div className="question-header">
        <h1>{question.question_text}</h1>
        <p className="question-meta">
          Published: {formatDate(question.pub_date)}
          {totalVotes > 0 && <span className="vote-count"> • {totalVotes} total votes</span>}
        </p>
      </div>

      <div className="choices-section">
        <h2>Choices</h2>
        {choices.length === 0 ? (
          <div className="empty-choices">
            <p>No choices available for this question.</p>
          </div>
        ) : (
          <div className="choices-list">
            {choices.map((choice) => {
              const percentage = totalVotes > 0 ? (choice.votes / totalVotes) * 100 : 0
              return (
                <div key={choice.id} className="choice-item">
                  <div className="choice-header">
                    <span className="choice-text">{choice.choice_text}</span>
                    <span className="choice-votes">{choice.votes} votes</span>
                  </div>
                  <div className="choice-bar-container">
                    <div
                      className="choice-bar"
                      style={{ width: `${percentage}%` }}
                    />
                  </div>
                  <div className="choice-percentage">{percentage.toFixed(1)}%</div>
                  <button
                    onClick={() => onVote(choice.id)}
                    className="vote-button"
                  >
                    Vote
                  </button>
                </div>
              )
            })}
          </div>
        )}
      </div>
    </div>
  )
}

export default QuestionDetail

