const API_BASE = (import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000').replace(/\/+$/, '')

export function getToken() {
  return localStorage.getItem('servicehub_token') || ''
}

export function setToken(token) {
  if (token) localStorage.setItem('servicehub_token', token)
  else localStorage.removeItem('servicehub_token')
}

export async function api(path, options = {}) {
  const headers = { ...(options.headers || {}) }
  if (options.body && !(options.body instanceof FormData)) headers['Content-Type'] = 'application/json'
  const token = getToken()
  if (token) headers.Authorization = `Bearer ${token}`
  let response
  try {
    response = await fetch(`${API_BASE}${path}`, { ...options, headers })
  } catch {
    throw new Error(`Backend se connection nahi hua. VITE_API_BASE_URL check karein: ${API_BASE}`)
  }
  const raw = await response.text()
  let data = null
  try { data = raw ? JSON.parse(raw) : null } catch { data = raw }
  if (!response.ok) {
    const detail = data?.detail
    const message = Array.isArray(detail) ? detail.map(x => x.msg).join(', ') : (typeof detail === 'string' ? detail : data?.message)
    throw new Error(message || `Request failed (${response.status})`)
  }
  return data
}

export const endpoints = {
  providers: '/providers/',
  doctors: '/doctors/',
  bookings: '/bookings/',
  hotelBookings: '/hotel-bookings/',
  appointments: '/appointments/',
  orders: '/orders/',
  payments: '/payments/create-order',
}

export function asArray(value) {
  if (Array.isArray(value)) return value
  if (Array.isArray(value?.items)) return value.items
  if (Array.isArray(value?.results)) return value.results
  if (Array.isArray(value?.data)) return value.data
  return []
}

export function labelOf(item, fallback = 'Service') {
  return item?.name || item?.title || item?.business_name || item?.provider_name || item?.specialization || item?.email || fallback
}
