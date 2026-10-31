<template>
  <q-page padding>
    <q-btn flat label="Back to tasks" to="/main" />
    <h1>Manage users</h1>
    <q-banner v-if="error" role="alert" class="bg-red-1 q-mb-md">{{
      error
    }}</q-banner>
    <template v-if="signedInUser?.role === 'host'">
      <p
        >Register new accounts through Sign up. Deleting an account ends its
        sessions and clears task assignments; its tasks and projects remain.</p
      >
      <q-list bordered separator>
        <q-item v-for="user in users" :key="user.id">
          <q-item-section>
            <q-item-label
              >{{ user.username }} · {{ user.role }} · ID
              {{ user.id }}</q-item-label
            >
            <q-input
              v-model="names[user.id]"
              label="Username"
              :disable="busy"
            />
          </q-item-section>
          <q-item-section side>
            <q-btn
              flat
              label="Save username"
              :disable="busy"
              @click="rename(user)"
            />
            <q-btn
              v-if="user.role !== 'host'"
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
import { ref, onMounted } from 'vue'
import { signedInUser, checkSession } from '../services/auth'
import { loadUsers, renameUser, deleteUser } from '../services/tasks'
const users = ref([]),
  names = ref({}),
  error = ref(''),
  busy = ref(false),
  pending = ref(null)
function report(err) {
  error.value = err.response?.data?.error || err.message
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
onMounted(async () => {
  try {
    await refresh()
  } catch (err) {
    report(err)
  }
})
</script>
