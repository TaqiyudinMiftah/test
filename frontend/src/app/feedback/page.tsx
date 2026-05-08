'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'

interface FeedbackItem {
  id: string
  clip_id: string
  action: string
  comment_text?: string
  created_at: string
}

export default function FeedbackPage() {
  const router = useRouter()
  const [feedbacks, setFeedbacks] = useState<FeedbackItem[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const token = localStorage.getItem('token')
    if (!token) {
      router.push('/')
      return
    }
    fetchFeedbacks(token)
  }, [router])

  const fetchFeedbacks = async (token: string) => {
    try {
      const res = await fetch('/api/v1/clips/feedback', {
        headers: { 'Authorization': `Bearer ${token}` }
      })
      if (res.ok) {
        const data = await res.json()
        setFeedbacks(data)
      }
    } catch (err) {
      console.error(err)
    } finally {
      setLoading(false)
    }
  }

  const getActionColor = (action: string) => {
    switch (action) {
      case 'approve': return 'bg-green-100 text-green-800'
      case 'reject': return 'bg-red-100 text-red-800'
      case 'edit': return 'bg-blue-100 text-blue-800'
      default: return 'bg-gray-100 text-gray-800'
    }
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <nav className="bg-white shadow-sm">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between h-16 items-center">
            <div className="flex items-center space-x-4">
              <button
                onClick={() => router.push('/dashboard')}
                className="text-blue-600 hover:text-blue-800"
              >
                ← Kembali
              </button>
              <h1 className="text-xl font-bold text-gray-900">Riwayat Feedback</h1>
            </div>
          </div>
        </div>
      </nav>

      <main className="max-w-7xl mx-auto py-6 sm:px-6 lg:px-8">
        <div className="px-4 py-6 sm:px-0">
          {loading ? (
            <p className="text-gray-600">Memuat...</p>
          ) : feedbacks.length === 0 ? (
            <p className="text-gray-500">Belum ada feedback.</p>
          ) : (
            <div className="bg-white shadow overflow-hidden sm:rounded-md">
              <ul className="divide-y divide-gray-200">
                {feedbacks.map((feedback) => (
                  <li key={feedback.id} className="px-4 py-4">
                    <div className="flex items-center justify-between">
                      <div>
                        <p className="text-sm font-medium text-gray-900">
                          Klip: {feedback.clip_id.slice(0, 8)}...
                        </p>
                        {feedback.comment_text && (
                          <p className="mt-1 text-sm text-gray-600">
                            {feedback.comment_text}
                          </p>
                        )}
                      </div>
                      <div className="flex items-center space-x-2">
                        <span className={`px-2 py-1 text-xs rounded-full ${getActionColor(feedback.action)}`}>
                          {feedback.action}
                        </span>
                        <span className="text-xs text-gray-500">
                          {new Date(feedback.created_at).toLocaleString('id-ID')}
                        </span>
                      </div>
                    </div>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      </main>
    </div>
  )
}
