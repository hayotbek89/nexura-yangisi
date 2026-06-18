export function getApiKey() {
  return localStorage.getItem('nexura_api_key') || ''
}

export function getAuthHeaders(extra = {}) {
  const key = getApiKey()
  return {
    ...extra,
    ...(key ? { Authorization: `Bearer ${key}` } : {}),
  }
}

export function apiFetch(url, options = {}) {
  return fetch(url, {
    ...options,
    headers: getAuthHeaders(options.headers || {}),
  })
}
