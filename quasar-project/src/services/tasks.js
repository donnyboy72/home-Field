import axios from 'axios'

function requestConfig() {
  const baseURL = localStorage.getItem('apiBaseUrl')
  const token = localStorage.getItem('token')
  if (!baseURL) throw new Error('Connect to a host first.')
  if (!token) throw new Error('Please log in again.')
  return {
    baseURL,
    timeout: 8000,
    headers: { Authorization: `Bearer ${token}` }
  }
}

export async function loadTasks() {
  return (await axios.get('/api/tasks', requestConfig())).data.tasks
}
export async function loadDeletedTasks() {
  return (await axios.get('/api/tasks/deleted', requestConfig())).data.tasks
}
export async function createTask(task) {
  return (await axios.post('/api/tasks', task, requestConfig())).data.task
}
export async function updateTask(id, changes) {
  return (await axios.patch(`/api/tasks/${id}`, changes, requestConfig())).data
    .task
}
export async function deleteTask(id) {
  await axios.delete(`/api/tasks/${id}`, requestConfig())
}
export async function restoreTask(id) {
  return (await axios.post(`/api/tasks/${id}/restore`, null, requestConfig()))
    .data.task
}
export async function loadProjects() {
  return (await axios.get('/api/projects', requestConfig())).data.projects
}
export async function createProject(name) {
  return (await axios.post('/api/projects', { name }, requestConfig())).data
    .project
}
export async function renameProject(id, name) {
  return (await axios.patch(`/api/projects/${id}`, { name }, requestConfig()))
    .data.project
}
export async function deleteProject(id) {
  await axios.delete(`/api/projects/${id}`, requestConfig())
}
