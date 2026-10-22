import axios from 'axios'
import { ref } from 'vue'

export const signedInUser = ref(null)

export function clearSession() {
  localStorage.removeItem('token')
  signedInUser.value = null
}

function baseUrl() {
  const base = localStorage.getItem('apiBaseUrl')
  if (!base) throw new Error('Connect to the host first.')
  return base
}

export async function connectHost(port) {
  if (!/^\d+$/.test(String(port)) || Number(port) < 1 || Number(port) > 65535) {
    throw new Error('Enter a port between 1 and 65535.')
  }
  const base = `http://localhost:${Number(port)}`
  const response = await axios.get(`${base}/api/health`, { timeout: 5000 })
  if (response.data.status !== 'running')
    throw new Error('The host is not ready.')
  if (localStorage.getItem('apiBaseUrl') !== base) clearSession()
  localStorage.setItem('apiBaseUrl', base)
}

export async function login(username, password) {
  clearSession()
  const response = await axios.post(
    `${baseUrl()}/api/auth/login`,
    { username: username.trim(), password },
    { timeout: 5000 }
  )
  if (!response.data.token)
    throw new Error('The host did not return a login session.')
  localStorage.setItem('token', response.data.token)
  try {
    // Confirm the returned token is accepted before opening the task page.
    return await checkSession()
  } catch (error) {
    clearSession()
    throw error
  }
}

export async function checkSession() {
  const token = localStorage.getItem('token')
  if (!token) throw new Error('Please log in.')
  try {
    const response = await axios.get(`${baseUrl()}/api/auth/me`, {
      headers: { Authorization: `Bearer ${token}` },
      timeout: 5000
    })
    signedInUser.value = response.data.user
    return response.data.user
  } catch (error) {
    if (error.response?.status === 401) clearSession()
    throw error
  }
}

export async function logout() {
  const token = localStorage.getItem('token')
  try {
    if (token)
      await axios.post(`${baseUrl()}/api/auth/logout`, null, {
        headers: { Authorization: `Bearer ${token}` },
        timeout: 5000
      })
  } catch (error) {
    if (error.response?.status !== 401) throw error
  }
  clearSession()
}

export function authError(error) {
  if (error.response?.status === 401)
    return 'Incorrect username or password, or your session has expired. Please log in again.'
  return (
    error.response?.data?.error ||
    (error.isAxiosError
      ? 'Could not reach the host. Check that Flask is running and reconnect.'
      : error.message)
  )
}
