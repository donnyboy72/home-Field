<template>
  <q-page class="q-ma-md">
    <p v-if="error" class="text-negative" role="alert">{{ error }}</p>
    <p v-if="notice" class="text-positive" role="status">{{ notice }}</p>
    <div>
      <q-table
        flat
        bordered
        card-class="bg-accent"
        hide-bottom
        row-key="id"
        :pagination="{ rowsPerPage: 0 }"
        :loading="loading"
        :rows="tasks"
        :columns="columns"
        no-data-label="No tasks yet"
      />
    </div>
    <div
      class="absolute-bottom-right q-ma-lg"
      style="width: 360px; max-width: calc(100% - 32px)"
    >
      <q-expansion-item
        expand-separator
        outlined
        label="Create Task"
        header-class="bg-primary text-accent"
        class="q-ma-lg"
      >
        <q-form ref="form" class="q-ma-sm" @submit="submitTask">
          <q-input
            dense
            outlined
            v-model="text"
            label="Title"
            :disable="submitting"
            :rules="[value => !!value.trim() || 'Enter a task title']"
          />
          <q-btn
            dense
            type="submit"
            label="Submit"
            class="bg-primary text-accent full-width"
            :loading="submitting"
          />
        </q-form>
      </q-expansion-item>
    </div>
  </q-page>
</template>

<script setup>
import { ref, onMounted, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import { createTask, loadTasks } from '../services/tasks'
import { clearSession } from '../services/auth'

const router = useRouter()
const tasks = ref([]),
  text = ref(''),
  form = ref(null)
const loading = ref(false),
  submitting = ref(false)
const error = ref(''),
  notice = ref('')
const columns = [
  {
    name: 'title',
    label: 'Title',
    field: 'title',
    align: 'left',
    sortable: true
  },
  {
    name: 'status',
    label: 'Status',
    field: row =>
      ({
        todo: 'To Do',
        in_progress: 'In Progress',
        review: 'Review',
        done: 'Complete'
      })[row.status] || row.status,
    align: 'left'
  }
]

function handleError(err) {
  if (err.response?.status === 401) {
    clearSession()
    router.replace({ path: '/login', query: { reason: 'expired' } })
    return
  }
  error.value =
    err.response?.data?.error ||
    (err.isAxiosError
      ? 'Could not reach the host. Check that Flask is running and try again.'
      : err.message)
}

async function refreshTasks() {
  loading.value = true
  try {
    tasks.value = await loadTasks()
  } catch (err) {
    handleError(err)
  } finally {
    loading.value = false
  }
}

async function submitTask() {
  if (submitting.value || !text.value.trim()) return
  submitting.value = true
  error.value = ''
  notice.value = ''
  try {
    const task = await createTask(text.value)
    // Add the saved server record immediately, without a second POST or GET.
    tasks.value = [...tasks.value.filter(row => row.id !== task.id), task]
    text.value = ''
    await nextTick()
    form.value?.resetValidation()
    notice.value = 'Task created.'
  } catch (err) {
    handleError(err)
  } finally {
    submitting.value = false
  }
}

onMounted(refreshTasks)
</script>
