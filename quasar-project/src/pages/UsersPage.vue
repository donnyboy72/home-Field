<template>
  <q-page padding>
    <q-btn flat label="Back to tasks" to="/main" />
    <h1>Manage users</h1>
    <q-banner v-if="error" role="alert" class="bg-red-1 q-mb-md">{{
      error
    }}</q-banner>
    <template v-if="canManageUsers">
      <p v-if="isHost"
        >Register new accounts through Sign up. Deleting an account ends its
        sessions and clears task assignments; its tasks and projects remain.</p
      >
      <p v-else
        >Managers can view accounts and edit usernames except the host
        administrator's. Only the host can delete accounts or change roles.</p
      >
      <q-btn flat label="Refresh users" :disable="busy" @click="reload" />
      <q-list bordered separator>
        <q-item v-for="user in users" :key="user.id">
          <q-item-section>
            <q-item-label
              >{{ user.username }} · {{ user.role }} · ID
              {{ user.id }}</q-item-label
            >
            <q-input
              v-if="canEdit(user)"
              v-model="names[user.id]"
              label="Username"
              :disable="busy"
            />
          </q-item-section>
          <q-item-section side>
            <q-btn
              v-if="isHost && user.role !== 'host'"
              flat
              :label="
                user.role === 'manager' ? 'Remove manager role' : 'Make manager'
              "
              :disable="busy"
              @click="changeRole(user)"
            />
            <q-btn
              flat
              v-if="canEdit(user)"
              label="Save username"
              :disable="busy"
              @click="rename(user)"
            />
            <q-btn
              v-if="isHost && user.role !== 'host'"
              flat
              color="negative"
              label="Delete user"
              :disable="busy"
              @click="pending = user"
            />
          </q-item-section>
        </q-item>
      </q-list>
      <q-dialog
        :model-value="!!pending"
        @update:model-value="pending = null"
        persistent
      >
        <q-card
          ><q-card-section
            >Delete {{ pending?.username }}? Their sessions will end and
            assignments will be cleared.</q-card-section
          >
          <q-card-actions align="right"
            ><q-btn
              flat
              label="Cancel"
              :disable="busy"
              @click="pending = null" /><q-btn
              color="negative"
              label="Delete"
              :loading="busy"
              @click="remove"
          /></q-card-actions>
        </q-card>
      </q-dialog>
    </template>
  </q-page>
</template>
<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { signedInUser, checkSession } from '../services/auth'
import {
  loadUsers,
  renameUser,
  deleteUser,
  setUserRole
} from '../services/tasks'
const users = ref([]),
  names = ref({}),
  error = ref(''),
  busy = ref(false),
  pending = ref(null)
const isHost = computed(() => signedInUser.value?.role === 'host')
const canManageUsers = computed(() =>
  ['host', 'manager'].includes(signedInUser.value?.role)
)
const canEdit = user =>
  isHost.value || (canManageUsers.value && user.role !== 'host')
let timer
function report(err) {
  error.value = err.response?.data?.error || err.message
}
async function changeRole(user) {
  busy.value = true
  error.value = ''
  try {
    await setUserRole(user.id, user.role === 'manager' ? 'user' : 'manager')
    await refresh()
  } catch (err) {
    report(err)
  } finally {
    busy.value = false
  }
}
async function reload() {
  try {
    await refresh()
  } catch (err) {
    report(err)
  }
}
async function refresh() {
  await checkSession()
  users.value = await loadUsers()
  names.value = Object.fromEntries(
    users.value.map(user => [user.id, user.username])
  )
}
async function rename(user) {
  busy.value = true
  error.value = ''
  try {
    await renameUser(user.id, names.value[user.id])
    await refresh()
  } catch (err) {
    report(err)
  } finally {
    busy.value = false
  }
}
async function remove() {
  busy.value = true
  error.value = ''
  try {
    await deleteUser(pending.value.id)
    pending.value = null
    await refresh()
  } catch (err) {
    report(err)
  } finally {
    busy.value = false
  }
}
onMounted(() => {
  reload()
  timer = setInterval(async () => {
    if (busy.value) return
    try {
      await checkSession()
      if (!canManageUsers.value) {
        users.value = []
        pending.value = null
        error.value = 'Host administrator or manager required'
      }
    } catch (err) {
      users.value = []
      pending.value = null
      report(err)
    }
  }, 5000)
})
onUnmounted(() => clearInterval(timer))
</script>
