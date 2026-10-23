export class ApiError extends Error {
  constructor(message, status) {
    super(message)
    this.status = status
  }
}

export function createApi(token = '', onExpired = () => {}, fetcher = fetch) {
  const base = (import.meta.env?.VITE_API_BASE_URL || '/api/v1').replace(/\/$/, '')
  return async function api(path, options = {}) {
    const { body, blob = false, ...rest } = options
    const headers = new Headers(rest.headers)
    if (token) headers.set('Authorization', `Bearer ${token}`)
    let payload = body
    if (body && !(body instanceof FormData) && !(body instanceof URLSearchParams)) {
      headers.set('Content-Type', 'application/json')
      payload = JSON.stringify(body)
    }
    let response
    try {
      response = await fetcher(`${base}${path}`, { ...rest, headers, body: payload })
    } catch (error) {
      if (error.name === 'AbortError') throw error
      throw new ApiError('Cannot reach the server. Please try again shortly.', 0)
    }
    if (!response.ok) {
      if (response.status === 401 && token) onExpired()
      if (response.status === 503 && (path === '/search/ai' || path.endsWith('/matches'))) {
        throw new ApiError('AI matching is currently unavailable. You can still search reports and contact the reporter.', 503)
      }
      const data = await response.json().catch(() => ({}))
      const detail = data.detail
      const message = Array.isArray(detail)
        ? detail.map(entry => `${entry.loc?.slice(1).join('.') || 'Request'}: ${entry.msg}`).join('; ')
        : typeof detail === 'string' ? detail : 'The request could not be completed.'
      throw new ApiError(message, response.status)
    }
    if (response.status === 204) return null
    return blob ? response.blob() : response.json()
  }
}
