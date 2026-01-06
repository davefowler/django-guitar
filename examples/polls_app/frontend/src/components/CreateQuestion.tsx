import { useState } from 'react'
import { Question, Choice } from '../guitar'
import './CreateQuestion.css'

interface CreateQuestionProps {
  onCancel: () => void
  onSuccess: () => void
}

function CreateQuestion({ onCancel, onSuccess }: CreateQuestionProps): JSX.Element {
  const [questionText, setQuestionText] = useState('')
  const [choices, setChoices] = useState<string[]>(['', ''])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleAddChoice = (): void => {
    setChoices([...choices, ''])
  }

  const handleRemoveChoice = (index: number): void => {
    if (choices.length > 2) {
      setChoices(choices.filter((_, i) => i !== index))
    }
  }

  const handleChoiceChange = (index: number, value: string): void => {
    const newChoices = [...choices]
    newChoices[index] = value
    setChoices(newChoices)
  }

  const handleSubmit = async (e: React.FormEvent): Promise<void> => {
    e.preventDefault()
    setError(null)

    if (!questionText.trim()) {
      setError('Question text is required')
      return
    }

    const validChoices = choices.filter(c => c.trim())
    if (validChoices.length < 2) {
      setError('At least 2 choices are required')
      return
    }

    try {
      setLoading(true)

      // Create question with future date (draft/unpublished)
      // This allows editing later
      const futureDate = new Date()
      futureDate.setFullYear(futureDate.getFullYear() + 1) // Set to next year

      const question = await Question.objects.create({
        question_text: questionText.trim(),
        pub_date: futureDate.toISOString(),
      })

      // Create choices
      for (const choiceText of validChoices) {
        await Choice.objects.create({
          question_id: question.id,
          choice_text: choiceText.trim(),
        })
      }

      // Publish the question (set pub_date to now)
      await Question.objects.update({ id: question.id }, {
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

          <div className="form-group">
            <label>Choices</label>
            {choices.map((choice, index) => (
              <div key={index} className="choice-input-group">
                <input
                  type="text"
                  value={choice}
                  onChange={(e) => handleChoiceChange(index, e.target.value)}
                  placeholder={`Choice ${index + 1}`}
                  maxLength={200}
                  required={index < 2}
                />
                {choices.length > 2 && (
                  <button
                    type="button"
                    onClick={() => handleRemoveChoice(index)}
                    className="remove-choice-button"
                  >
                    Remove
                  </button>
                )}
              </div>
            ))}
            <button
              type="button"
              onClick={handleAddChoice}
              className="add-choice-button"
            >
              + Add Choice
            </button>
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

