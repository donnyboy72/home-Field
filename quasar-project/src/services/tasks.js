import axios from 'axios'

function requestConfig() {
  const baseURL = localStorage.getItem('apiBaseUrl')
  const token = localStorage.getItem('token')
  if (!baseURL) throw new Error('Connect to a host first.')
  if (!token) throw new Error('Please log in before creating tasks.')
  return {
    baseURL,
    timeout: 5000,
    headers: { Authorization: `Bearer ${token}` }
  }
}

export async function loadTasks() {
  const response = await axios.get('/api/tasks', requestConfig())
  return response.data.tasks
}

export async function createTask(title) {
  const response = await axios.post(
    '/api/tasks',
    { title: title.trim() },
    requestConfig()
  )
  return response.data.task
}
