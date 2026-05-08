import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'

export function useAuth() {
  const [user, setUser] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const router = useRouter()

  useEffect(() => {
    const token = localStorage.getItem('token')
    if (!token) {
      setLoading(false)
      return
    }

    fetch('/api/v1/auth/me', {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then((res) => {
        if (!res.ok) throw new Error('Unauthorized')
        return res.json()
      })
      .then((data) => {
        setUser(data)
      })
      .catch(() => {
        localStorage.removeItem('token')
        router.push('/')
      })
      .finally(() => setLoading(false))
  }, [router])

  const logout = () => {
    localStorage.removeItem('token')
    router.push('/')
  }

  return { user, loading, logout }
}
