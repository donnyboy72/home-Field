<template>
  <q-page class="workspace">
    <div class="workspace-shell">
      <div class="heading row items-center justify-between q-col-gutter-md">
        <div class="col-12 col-sm"
          ><div class="eyebrow">YOUR WORKSPACE</div><h1>Tasks & projects</h1
          ><p>Keep your team's work in one place.</p></div
        >
        <div class="col-auto"
          ><q-btn
            unelevated
            color="primary"
            icon="add"
            label="New task"
            no-caps
            @click="openTask()"
        /></div>
      </div>
      <q-banner v-if="error" class="error-banner q-mb-md" role="alert" rounded
        ><template #avatar><q-icon name="error_outline" /></template>{{ error
        }}<template #action
          ><q-btn flat dense label="Dismiss" @click="error = ''" /></template
      ></q-banner>
      <div class="stats-grid">
        <div class="stat"
          ><span>All tasks</span><strong>{{ tasks.length }}</strong></div
        >
        <div class="stat"
          ><span>To do</span
          ><strong>{{
            tasks.filter(t => t.status === 'todo').length
          }}</strong></div
        >
        <div class="stat"
          ><span>In progress</span
          ><strong>{{
            tasks.filter(
              t => t.status === 'in_progress' || t.status === 'review'
            ).length
          }}</strong></div
        >
        <div class="stat"
          ><span>Complete</span
          ><strong>{{
            tasks.filter(t => t.status === 'done').length
          }}</strong></div
        >
      </div>
      <div class="content-grid">
        <aside class="panel projects-panel">
          <div class="panel-heading"
            ><h2>Projects</h2
            ><q-btn
              flat
              dense
              round
              icon="add"
              aria-label="Create project"
              @click="openProject()"
          /></div>
          <button
            class="project-link"
            :class="{ selected: filter === 'all' }"
            @click="selectProject('all')"
            ><q-icon name="view_list" /> All tasks
            <span>{{ tasks.length }}</span></button
          >
          <button
            class="project-link"
            :class="{ selected: filter === 'unassigned' }"
            @click="selectProject('unassigned')"
            ><q-icon name="inbox" /> No project
            <span>{{
              tasks.filter(t => t.project_id === null).length
            }}</span></button
          >
          <div class="section-label">PROJECTS</div>
          <p v-if="!projects.length" class="empty-projects">No projects yet.</p>
          <div
            v-for="project in projects"
            :key="project.id"
            class="project-row"
          >
            <button
              class="project-link"
              :class="{ selected: filter === project.id }"
              @click="selectProject(project.id)"
              ><q-icon name="folder_open" /><span class="project-name">{{
                project.name
              }}</span
              ><span>{{
                tasks.filter(t => t.project_id === project.id).length
              }}</span></button
            >
            <q-btn
              flat
              dense
              round
              size="sm"
              icon="more_horiz"
              :aria-label="`Options for ${project.name}`"
              ><q-menu
                ><q-list dense style="min-width: 130px"
                  ><q-item clickable v-close-popup @click="openProject(project)"
                    ><q-item-section>Rename</q-item-section></q-item
                  ><q-item
                    clickable
                    v-close-popup
                    @click="confirmProjectDelete(project)"
                    ><q-item-section class="text-negative"
                      >Delete</q-item-section
                    ></q-item
                  ></q-list
                ></q-menu
              ></q-btn
            >
          </div>
        </aside>
        <main class="panel tasks-panel">
          <div class="task-top"
            ><div
              ><h2>{{
                tab === 'deleted' ? 'Recently deleted' : currentTitle
              }}</h2
              ><p>{{
                tab === 'deleted'
                  ? 'Tasks can be restored within 24 hours.'
                  : 'View and manage your tasks.'
              }}</p></div
            ><q-btn
              flat
              dense
              icon="refresh"
              aria-label="Refresh"
              :loading="loading"
              @click="refresh(true)"
          /></div>
          <div class="toolbar"
            ><q-tabs
              v-model="tab"
              dense
              no-caps
              active-color="primary"
              indicator-color="primary"
              align="left"
              ><q-tab name="active" label="Active" /><q-tab
                name="deleted"
                :label="`Deleted (${deleted.length})`" /></q-tabs
            ><q-input
              v-model="search"
              dense
              outlined
              debounce="200"
              placeholder="Search tasks"
              class="search-field"
              aria-label="Search tasks"
              ><template #prepend
                ><q-icon name="search" size="20px" /></template></q-input
          ></div>
          <div v-if="loading && !loaded" class="empty-state"
            >Loading tasks…</div
          >
          <div v-else-if="!visibleTasks.length" class="empty-state"
            ><q-icon
              :name="tab === 'deleted' ? 'restore_from_trash' : 'task_alt'"
              size="32px"
            /><strong>{{
              search
                ? 'No matching tasks'
                : tab === 'deleted'
                  ? 'No recently deleted tasks'
                  : 'No tasks here yet'
            }}</strong
            ><span>{{
              search
                ? 'Try another search.'
                : tab === 'deleted'
                  ? 'Deleted tasks will appear here.'
                  : 'Create a task to get started.'
            }}</span></div
          >
          <div v-else class="task-list">
            <article
              v-for="task in visibleTasks"
              :key="task.id"
              class="task-row"
            >
              <div class="task-main"
                ><div class="task-title">{{ task.title }}</div
                ><div v-if="task.description" class="task-description">{{
                  task.description
                }}</div
                ><div class="task-meta"
                  ><span
                    ><q-icon name="folder_open" />
                    {{ projectName(task.project_id) }}</span
                  ><span v-if="task.deadline"
                    ><q-icon name="event" /> {{ task.deadline }}</span
                  ><span v-if="task.assigned_to"
                    ><q-icon name="person_outline" /> User #{{
                      task.assigned_to
                    }}</span
                  ></div
                ></div
              >
              <div class="task-actions"
                ><span class="status" :class="`status-${task.status}`">{{
                  statusLabel(task.status)
                }}</span
                ><template v-if="tab === 'active'"
                  ><q-btn
                    v-if="task.status !== 'done'"
                    flat
                    dense
                    round
                    icon="check_circle_outline"
                    :disable="busy"
                    aria-label="Mark complete"
                    @click="markComplete(task)" /><q-btn
                    flat
                    dense
                    round
                    icon="edit"
                    :disable="busy"
                    aria-label="Edit task"
                    @click="openTask(task)" /><q-btn
                    flat
                    dense
                    round
                    icon="delete_outline"
                    :disable="busy"
                    aria-label="Delete task"
                    @click="confirmTaskDelete(task)" /></template
                ><q-btn
                  v-else
                  flat
                  dense
                  color="primary"
                  no-caps
                  label="Restore"
                  :disable="busy"
                  @click="restore(task)"
              /></div>
            </article>
          </div>
        </main>
      </div>
    </div>
    <q-dialog v-model="taskDialog" persistent
      ><q-card class="dialog-card"
        ><q-form @submit="saveTask"
          ><q-card-section class="dialog-heading"
            ><div class="text-h6">{{
              editingTask ? 'Edit task' : 'New task'
            }}</div
            ><q-btn
              flat
              round
              dense
              icon="close"
              aria-label="Close"
              :disable="busy"
              @click="taskDialog = false" /></q-card-section
          ><q-card-section v-if="error" class="text-negative" role="alert">{{
            error
          }}</q-card-section
          ><q-card-section class="q-gutter-md"
            ><q-input
              v-model="draft.title"
              outlined
              label="Title"
              autofocus
              :rules="[v => !!v.trim() || 'Enter a title']" /><q-input
              v-model="draft.description"
              outlined
              type="textarea"
              autogrow
              label="Description (optional)" /><div class="row q-col-gutter-md"
              ><q-input
                v-model="draft.deadline"
                class="col-12 col-sm-6"
                outlined
                type="date"
                label="Due date"
                stack-label /><q-select
                v-model="draft.status"
                class="col-12 col-sm-6"
                outlined
                label="Status"
                :options="statusOptions"
                emit-value
                map-options /></div
            ><q-select
              v-if="!editingTask"
              v-model="draft.project_id"
              outlined
              label="Project"
              :options="projectOptions"
              emit-value
              map-options /><q-input
              v-model="draft.assigned_to"
              outlined
              type="number"
              min="1"
              label="Assigned user ID (optional)"
              hint="Enter the ID of an existing user" /></q-card-section
          ><q-card-actions align="right" class="q-pa-md"
            ><q-btn
              flat
              no-caps
              label="Cancel"
              :disable="busy"
              @click="taskDialog = false" /><q-btn
              unelevated
              no-caps
              color="primary"
              type="submit"
              :loading="busy"
              :label="
                editingTask ? 'Save changes' : 'Create task'
              " /></q-card-actions></q-form></q-card
    ></q-dialog>
    <q-dialog v-model="projectDialog" persistent
      ><q-card class="dialog-card"
        ><q-form @submit="saveProject"
          ><q-card-section class="dialog-heading"
            ><div class="text-h6">{{
              editingProject ? 'Rename project' : 'New project'
            }}</div
            ><q-btn
              flat
              round
              dense
              icon="close"
              aria-label="Close"
              :disable="busy"
              @click="projectDialog = false" /></q-card-section
          ><q-card-section v-if="error" class="text-negative" role="alert">{{
            error
          }}</q-card-section
          ><q-card-section
            ><q-input
              v-model="projectDraft"
              outlined
              autofocus
              label="Project name"
              :rules="[
                v => !!v.trim() || 'Enter a project name'
              ]" /></q-card-section
          ><q-card-actions align="right" class="q-pa-md"
            ><q-btn
              flat
              no-caps
              label="Cancel"
              :disable="busy"
              @click="projectDialog = false" /><q-btn
              unelevated
              no-caps
              color="primary"
              type="submit"
              :loading="busy"
              :label="
                editingProject ? 'Save changes' : 'Create project'
              " /></q-card-actions></q-form></q-card
    ></q-dialog>
    <q-dialog v-model="confirmDialog" persistent
      ><q-card class="dialog-card"
        ><q-card-section class="text-h6">{{
          confirmation.title
        }}</q-card-section
        ><q-card-section>{{ confirmation.message }}</q-card-section
        ><q-card-section v-if="error" class="text-negative" role="alert">{{
          error
        }}</q-card-section
        ><q-card-actions align="right" class="q-pa-md"
          ><q-btn
            flat
            no-caps
            label="Cancel"
            :disable="busy"
            @click="confirmDialog = false" /><q-btn
            unelevated
            no-caps
            color="negative"
            label="Delete"
            :loading="busy"
            @click="runDelete" /></q-card-actions></q-card
    ></q-dialog>
  </q-page>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { clearSession } from '../services/auth'
import * as api from '../services/tasks'

const router = useRouter()
const tasks = ref([]),
  deleted = ref([]),
  projects = ref([])
const loading = ref(false),
  loaded = ref(false),
  busy = ref(false),
  error = ref('')
const filter = ref('all'),
  tab = ref('active'),
  search = ref('')
const taskDialog = ref(false),
  editingTask = ref(null),
  draft = ref({})
const projectDialog = ref(false),
  editingProject = ref(null),
  projectDraft = ref('')
const confirmDialog = ref(false),
  confirmation = ref({}),
  pending = ref(null)
let timer,
  alive = true,
  refreshSequence = 0
const statuses = [
  { label: 'To do', value: 'todo' },
  { label: 'In progress', value: 'in_progress' },
  { label: 'Review', value: 'review' },
  { label: 'Complete', value: 'done' }
]
const statusOptions = computed(() =>
  editingTask.value ? statuses : statuses.filter(s => s.value !== 'done')
)
const projectOptions = computed(() => [
  { label: 'No project', value: null },
  ...projects.value.map(p => ({ label: p.name, value: p.id }))
])
const currentTitle = computed(() =>
  filter.value === 'all'
    ? 'All tasks'
    : filter.value === 'unassigned'
      ? 'No project'
      : projects.value.find(p => p.id === filter.value)?.name || 'Project'
)
const visibleTasks = computed(() => {
  const query = search.value.trim().toLowerCase()
  return (tab.value === 'deleted' ? deleted.value : tasks.value).filter(t => {
    const matchesProject =
      tab.value === 'deleted' ||
      filter.value === 'all' ||
      (filter.value === 'unassigned'
        ? t.project_id === null
        : t.project_id === filter.value)
    return (
      matchesProject &&
      (!query ||
        `${t.title} ${t.description || ''}`.toLowerCase().includes(query))
    )
  })
})
function selectProject(value) {
  filter.value = value
  tab.value = 'active'
}
function statusLabel(status) {
  return statuses.find(s => s.value === status)?.label || status
}
function projectName(id) {
  return id == null
    ? 'No project'
    : projects.value.find(p => p.id === id)?.name || 'Unavailable project'
}
function showError(err) {
  if (err.response?.status === 401) {
    clearSession()
    router.replace({ path: '/login', query: { reason: 'expired' } })
    return
  }
  error.value =
    err.response?.data?.error ||
    (err.isAxiosError
      ? 'Could not reach the host. Check that it is running and try again.'
      : err.message)
}
async function refresh(manual = false) {
  if (!alive || (busy.value && !manual)) return
  const sequence = ++refreshSequence
  if (manual || !loaded.value) loading.value = true
  try {
    const [active, trash, projectList] = await Promise.all([
      api.loadTasks(),
      api.loadDeletedTasks(),
      api.loadProjects()
    ])
    if (!alive || sequence !== refreshSequence) return
    tasks.value = active
    deleted.value = trash
    projects.value = projectList
    loaded.value = true
    error.value = ''
    if (
      typeof filter.value === 'number' &&
      !projectList.some(p => p.id === filter.value)
    )
      filter.value = 'all'
  } catch (err) {
    if (alive && sequence === refreshSequence) showError(err)
  } finally {
    if (sequence === refreshSequence) loading.value = false
  }
}
function openTask(task = null) {
  editingTask.value = task
  draft.value = {
    title: task?.title || '',
    description: task?.description || '',
    deadline: task?.deadline || '',
    status: task?.status || 'todo',
    project_id:
      task?.project_id ??
      (typeof filter.value === 'number' ? filter.value : null),
    assigned_to: task?.assigned_to == null ? '' : String(task.assigned_to)
  }
  taskDialog.value = true
}
async function saveTask() {
  if (busy.value || !draft.value.title.trim()) return
  const rawAssignee = String(draft.value.assigned_to ?? '').trim()
  if (
    rawAssignee &&
    (!/^\d+$/.test(rawAssignee) ||
      !Number.isSafeInteger(Number(rawAssignee)) ||
      Number(rawAssignee) < 1)
  ) {
    error.value = 'Assigned user ID must be a positive whole number.'
    return
  }
  busy.value = true
  error.value = ''
  const data = {
    title: draft.value.title.trim(),
    description: draft.value.description,
    deadline: draft.value.deadline || null,
    status: draft.value.status,
    assigned_to: rawAssignee ? Number(rawAssignee) : null
  }
  try {
    if (editingTask.value) await api.updateTask(editingTask.value.id, data)
    else await api.createTask({ ...data, project_id: draft.value.project_id })
    taskDialog.value = false
    await refresh(true)
  } catch (err) {
    showError(err)
  } finally {
    busy.value = false
  }
}
async function markComplete(task) {
  if (busy.value) return
  busy.value = true
  error.value = ''
  try {
    await api.updateTask(task.id, { status: 'done' })
    await refresh(true)
  } catch (err) {
    showError(err)
  } finally {
    busy.value = false
  }
}
function confirmTaskDelete(task) {
  pending.value = { type: 'task', id: task.id }
  confirmation.value = {
    title: 'Delete task?',
    message: `Delete “${task.title}”? You can restore it within 24 hours.`
  }
  confirmDialog.value = true
}
function confirmProjectDelete(project) {
  pending.value = { type: 'project', id: project.id }
  confirmation.value = {
    title: 'Delete project?',
    message: `Delete “${project.name}”? Its tasks will remain, but the project will no longer be available.`
  }
  confirmDialog.value = true
}
async function runDelete() {
  if (busy.value || !pending.value) return
  busy.value = true
  error.value = ''
  try {
    if (pending.value.type === 'task') await api.deleteTask(pending.value.id)
    else await api.deleteProject(pending.value.id)
    confirmDialog.value = false
    await refresh(true)
  } catch (err) {
    showError(err)
  } finally {
    busy.value = false
  }
}
async function restore(task) {
  if (busy.value) return
  busy.value = true
  error.value = ''
  try {
    await api.restoreTask(task.id)
    await refresh(true)
  } catch (err) {
    await refresh(true)
    showError(err)
  } finally {
    busy.value = false
  }
}
function openProject(project = null) {
  editingProject.value = project
  projectDraft.value = project?.name || ''
  projectDialog.value = true
}
async function saveProject() {
  if (busy.value || !projectDraft.value.trim()) return
  busy.value = true
  error.value = ''
  try {
    if (editingProject.value)
      await api.renameProject(
        editingProject.value.id,
        projectDraft.value.trim()
      )
    else await api.createProject(projectDraft.value.trim())
    projectDialog.value = false
    await refresh(true)
  } catch (err) {
    showError(err)
  } finally {
    busy.value = false
  }
}
onMounted(() => {
  refresh(true)
  timer = setInterval(() => refresh(), 5000)
})
onUnmounted(() => {
  alive = false
  clearInterval(timer)
})
</script>
