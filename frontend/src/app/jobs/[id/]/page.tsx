'use client'

import { useState, useEffect } from 'react'
import { useParams, useRouter } from 'next/navigation'

interface Segment {
  id: string
  start_time: number
  end_time: number
  transcript_text?: string
  llm_total_score: number
  energy_score: number
}

interface JobDetail {
  id: string
  status: string
  original_filename: string
  metadata_json: Record<string, any>
  error_message?: string
  created_at: string
  updated_at: string
}

export default function JobDetailPage() {
  const params = useParams()
  const router = useRouter()
  const jobId = params.id as string
  const [job, setJob] = useState<JobDetail | null>(null)
  const [segments, setSegments] = useState<Segment[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    const token = localStorage.getItem('token')
    if (!token) {
      router.push('/')
      return
    }
    fetchJobDetail(token)
    fetchSegments(token)
  }, [jobId, router])

  const fetchJobDetail = async (token: string) => {
    try {
      const res = await fetch(`/api/v1/jobs/${jobId}`, {
        headers: { 'Authorization': `Bearer ${token}` }
      })
      if (res.ok) {
        const data = await res.json()
        setJob(data)
      } else {
        throw new Error('Gagal memuat detail job')
      }
    } catch (err: any) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  const fetchSegments = async (token: string) => {
    try {
      const res = await fetch(`/api/v1/jobs/${jobId}/segments`, {
        headers: { 'Authorization': `Bearer ${token}` }
      })
      if (res.ok) {
        const data = await res.json()
        setSegments(data)
      }
    } catch (err) {
      console.error(err)
    }
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'done': return 'bg-green-100 text-green-800'
      case 'processing': return 'bg-yellow-100 text-yellow-800'
      case 'failed': return 'bg-red-100 text-red-800'
      default: return 'bg-gray-100 text-gray-800'
    }
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <p className="text-gray-600">Memuat...</p>
      </div>
    )
  }

  if (error || !job) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <p className="text-red-600">{error || 'Job tidak ditemukan'}</p>
      </div>
    )
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
              <h1 className="text-xl font-bold text-gray-900">Detail Job</h1>
            </div>
          </div>
        </div>
      </nav>

      <main className="max-w-7xl mx-auto py-6 sm:px-6 lg:px-8">
        <div className="px-4 py-6 sm:px-0">
          {/* Job Info */}
          <div className="bg-white shadow rounded-lg p-6 mb-6">
            <div className="flex justify-between items-start">
              <div>
                <h2 className="text-lg font-medium text-gray-900">{job.original_filename}</h2>
                <p className="mt-1 text-sm text-gray-500">ID: {job.id}</p>
              </div>
              <span className={`px-2 py-1 inline-flex text-xs leading-5 font-semibold rounded-full ${getStatusColor(job.status)}`}>
                {job.status.toUpperCase()}
              </span>
            </div>
            
            <div className="mt-4 grid grid-cols-2 gap-4">
              <div>
                <p className="text-sm font-medium text-gray-500">Durasi</p>
                <p className="text-sm text-gray-900">{job.metadata_json.duration?.toFixed(2) || '-'} detik</p>
              </div>
              <div>
                <p className="text-sm font-medium text-gray-500">Resolusi</p>
                <p className="text-sm text-gray-900">{job.metadata_json.video_width || '-'} x {job.metadata_json.video_height || '-'}</p>
              </div>
              <div>
                <p className="text-sm font-medium text-gray-500">Codec</p>
                <p className="text-sm text-gray-900">{job.metadata_json.video_codec || '-'}</p>
              </div>
              <div>
                <p className="text-sm font-medium text-gray-500">FPS</p>
                <p className="text-sm text-gray-900">{job.metadata_json.video_fps || '-'}</p>
              </div>
            </div>

            {job.error_message && (
              <div className="mt-4 bg-red-50 text-red-700 p-3 rounded-md text-sm">
                Error: {job.error_message}
              </div>
            )}
          </div>

          {/* Segments */}
          <div className="bg-white shadow rounded-lg p-6">
            <h3 className="text-lg font-medium text-gray-900 mb-4">Segmen Terdeteksi ({segments.length})</h3>
            
            {segments.length === 0 ? (
              <p className="text-gray-500">Belum ada segmen yang terdeteksi.</p>
            ) : (
              <div className="overflow-x-auto">
                <table className="min-w-full divide-y divide-gray-200">
                  <thead>
                    <tr>
                      <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Waktu</th>
                      <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Transkrip</th>
                      <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Skor LLM</th>
                      <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Energi</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-200">
                    {segments.map((segment) => (
                      <tr key={segment.id}>
                        <td className="px-4 py-2 text-sm text-gray-900">
                          {segment.start_time.toFixed(2)}s - {segment.end_time.toFixed(2)}s
                        </td>
                        <td className="px-4 py-2 text-sm text-gray-600 max-w-md truncate">
                          {segment.transcript_text || '-'}
                        </td>
                        <td className="px-4 py-2 text-sm text-gray-900">
                          {segment.llm_total_score.toFixed(2)}
                        </td>
                        <td className="px-4 py-2 text-sm text-gray-900">
                          {segment.energy_score.toFixed(3)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>
      </main>
    </div>
  )
}
