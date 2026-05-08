'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'

interface ClipItem {
  id: string
  job_id: string
  editor_decision: string
  start_time?: number
  end_time?: number
  output_paths_json: Record<string, string>
  created_at: string
}

export default function ClipsPage() {
  const router = useRouter()
  const [clips, setClips] = useState<ClipItem[]>([])
  const [loading, setLoading] = useState(true)
  const [filter, setFilter] = useState('')

  useEffect(() => {
    const token = localStorage.getItem('token')
    if (!token) {
      router.push('/')
      return
    }
    fetchClips(token)
  }, [router])

  const fetchClips = async (token: string) => {
    try {
      const res = await fetch('/api/v1/clips', {
        headers: { 'Authorization': `Bearer ${token}` }
      })
      if (res.ok) {
        const data = await res.json()
        setClips(data)
      }
    } catch (err) {
      console.error(err)
    } finally {
      setLoading(false)
    }
  }

  const updateDecision = async (clipId: string, decision: string) => {
    const token = localStorage.getItem('token')
    if (!token) return

    try {
      const res = await fetch(`/api/v1/clips/${clipId}/decision`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ decision }),
      })

      if (res.ok) {
        await fetchClips(token)
      }
    } catch (err) {
      console.error(err)
    }
  }

  const getDecisionColor = (decision: string) => {
    switch (decision) {
      case 'approved': return 'bg-green-100 text-green-800'
      case 'rejected': return 'bg-red-100 text-red-800'
      case 'edited': return 'bg-blue-100 text-blue-800'
      default: return 'bg-gray-100 text-gray-800'
    }
  }

  const filteredClips = filter
    ? clips.filter(c => c.editor_decision === filter)
    : clips

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
              <h1 className="text-xl font-bold text-gray-900">Review Klip</h1>
            </div>
          </div>
        </div>
      </nav>

      <main className="max-w-7xl mx-auto py-6 sm:px-6 lg:px-8">
        <div className="px-4 py-6 sm:px-0">
          {/* Filter */}
          <div className="mb-6 flex space-x-2">
            <button
              onClick={() => setFilter('')}
              className={`px-3 py-1 rounded-full text-sm ${!filter ? 'bg-blue-600 text-white' : 'bg-gray-200 text-gray-700'}`}
            >
              Semua
            </button>
            <button
              onClick={() => setFilter('pending')}
              className={`px-3 py-1 rounded-full text-sm ${filter === 'pending' ? 'bg-blue-600 text-white' : 'bg-gray-200 text-gray-700'}`}
            >
              Menunggu
            </button>
            <button
              onClick={() => setFilter('approved')}
              className={`px-3 py-1 rounded-full text-sm ${filter === 'approved' ? 'bg-blue-600 text-white' : 'bg-gray-200 text-gray-700'}`}
            >
              Disetujui
            </button>
            <button
              onClick={() => setFilter('rejected')}
              className={`px-3 py-1 rounded-full text-sm ${filter === 'rejected' ? 'bg-blue-600 text-white' : 'bg-gray-200 text-gray-700'}`}
            >
              Ditolak
            </button>
          </div>

          {loading ? (
            <p className="text-gray-600">Memuat...</p>
          ) : filteredClips.length === 0 ? (
            <p className="text-gray-500">Tidak ada klip.</p>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {filteredClips.map((clip) => (
                <div key={clip.id} className="bg-white shadow rounded-lg overflow-hidden">
                  <div className="p-4">
                    <div className="flex justify-between items-start mb-2">
                      <h3 className="text-sm font-medium text-gray-900">
                        Klip {clip.id.slice(0, 8)}
                      </h3>
                      <span className={`px-2 py-0.5 text-xs rounded-full ${getDecisionColor(clip.editor_decision)}`}>
                        {clip.editor_decision}
                      </span>
                    </div>
                    
                    <p className="text-sm text-gray-500 mb-2">
                      {clip.start_time?.toFixed(1)}s - {clip.end_time?.toFixed(1)}s
                    </p>

                    {clip.output_paths_json && Object.keys(clip.output_paths_json).length > 0 && (
                      <div className="mt-2 space-y-1">
                        {Object.entries(clip.output_paths_json).map(([format, url]) => (
                          <a
                            key={format}
                            href={url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="block text-xs text-blue-600 hover:text-blue-800"
                          >
                            Download {format}
                          </a>
                        ))}
                      </div>
                    )}

                    <div className="mt-4 flex space-x-2">
                      <button
                        onClick={() => updateDecision(clip.id, 'approved')}
                        className="flex-1 px-2 py-1 text-xs bg-green-600 text-white rounded hover:bg-green-700"
                      >
                        Setujui
                      </button>
                      <button
                        onClick={() => updateDecision(clip.id, 'rejected')}
                        className="flex-1 px-2 py-1 text-xs bg-red-600 text-white rounded hover:bg-red-700"
                      >
                        Tolak
                      </button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </main>
    </div>
  )
}
