import { useState, useEffect } from 'react'
import { Question, Choice } from './guitar'
import QuestionList from './components/QuestionList'
import QuestionDetail from './components/QuestionDetail'
import CreateQuestion from './components/CreateQuestion'
import './App.css'

type View = 'list' | 'detail' | 'create'

interface QuestionType {
  id: number
  question_text: string
  pub_date: string
}

function App(): JSX.Element {
  const [view, setView] = useState<View>('list')
  const [selectedQuestionId, setSelectedQuestionId] = useState<number | null>(null)
  const [questions, setQuestions] = useState<QuestionType[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    loadQuestions()
  }, [])

  const loadQuestions = async (): Promise<void> => {
    try {
      setLoading(true)
      setError(null)
      const data = await Question.objects.all()
      setQuestions(data)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load questions')
      console.error('Error loading questions:', err)
    } finally {
      setLoading(false)
    }
  }

  const handleQuestionClick = (questionId: number): void => {
    setSelectedQuestionId(questionId)
    setView('detail')
  }

  const handleBackToList = (): void => {
    setView('list')
    setSelectedQuestionId(null)
    loadQuestions() // Refresh list
  }

  const handleCreateQuestion = (): void => {
    setView('create')
  }

  const handleQuestionCreated = (): void => {
    setView('list')
    loadQuestions()
  }

  const handleVote = async (choiceId: number): Promise<void> => {
    try {
      // Note: In a real app, you'd have a custom vote endpoint
      // For now, we'll simulate voting by showing a message
      // The votes field is read-only in the API
      alert('Vote recorded! (In a real app, this would increment the vote count via a custom endpoint)')
      if (selectedQuestionId) {
        // Reload the question detail to show updated vote counts
        setView('detail')
      }
    } catch (err) {
      console.error('Error voting:', err)
      alert('Failed to record vote')
    }
  }

  return (
    <div className="app">
      <header className="app-header">
        <h1>🎸 Django Guitar Polls</h1>
        <nav>
          <button onClick={handleBackToList} className={view === 'list' ? 'active' : ''}>
            Questions
          </button>
          <button onClick={handleCreateQuestion} className={view === 'create' ? 'active' : ''}>
            Create Question
          </button>
        </nav>
      </header>

      <main className="app-main">
        {error && (
          <div className="error-message">
            <p>Error: {error}</p>
            <button onClick={loadQuestions}>Retry</button>
          </div>
        )}

        {view === 'list' && (
          <QuestionList
            questions={questions}
            loading={loading}
            onQuestionClick={handleQuestionClick}
            onRefresh={loadQuestions}
          />
        )}

        {view === 'detail' && selectedQuestionId && (
          <QuestionDetail
            questionId={selectedQuestionId}
            onBack={handleBackToList}
            onVote={handleVote}
          />
        )}

        {view === 'create' && (
          <CreateQuestion
            onCancel={handleBackToList}
            onSuccess={handleQuestionCreated}
          />
        )}
      </main>
    </div>
  )
}

export default App

