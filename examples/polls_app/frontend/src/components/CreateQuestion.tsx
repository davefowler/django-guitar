import { useState } from 'react'
import { Question } from '../guitar'
import './CreateQuestion.css'

interface CreateQuestionProps {
  onCancel: () => void
  onSuccess: () => void
}

function CreateQuestion({ onCancel, onSuccess }: CreateQuestionProps): JSX.Element {
  const [questionText, setQuestionText] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleSubmit = async (e: React.FormEvent): Promise<void> => {
    e.preventDefault()
    setError(null)

    if (!questionText.trim()) {
      setError('Question text is required')
      return
    }

    try {
      setLoading(true)

      // Create question - published immediately
      await Question.objects.create({
        question_text: questionText.trim(),
        pub_date: new Date().toISOString(),
      })

      onSuccess()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create question')
      console.error('Error creating question:', err)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="create-question">
      <button onClick={onCancel} className="back-button">
        ← Cancel
      </button>

      <div className="create-form-container">
        <h1>Create New Question</h1>

        <p className="info-text">
          💡 Questions are published immediately. Add choices via Django admin at{' '}
          <a href="/admin/" target="_blank" rel="noopener noreferrer">/admin/</a>
        </p>

        {error && (
          <div className="error-message">
            <p>{error}</p>
          </div>
        )}

        <form onSubmit={handleSubmit} className="create-form">
          <div className="form-group">
            <label htmlFor="question-text">Question Text</label>
            <input
              id="question-text"
              type="text"
              value={questionText}
              onChange={(e) => setQuestionText(e.target.value)}
              placeholder="e.g., What is your favorite programming language?"
              maxLength={200}
              required
            />
          </div>

          <div className="form-actions">
            <button
              type="button"
              onClick={onCancel}
              className="cancel-button"
              disabled={loading}
            >
              Cancel
            </button>
            <button
              type="submit"
              className="submit-button"
              disabled={loading}
            >
              {loading ? 'Creating...' : 'Create Question'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

export default CreateQuestion
