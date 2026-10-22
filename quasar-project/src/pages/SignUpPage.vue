<template>
  <q-page class="q-ma-lg">
    <q-form
      class="fixed-center"
      style="width: 280px; max-width: 90vw"
      @submit="submit"
    >
      <q-input
        v-model="username"
        label="Username"
        autocomplete="username"
        :rules="[value => !!value.trim() || 'Enter your username']"
      />
      <q-input
        v-model="password"
        type="password"
        label="Password"
        autocomplete="new-password"
        :rules="[value => !!value || 'Enter your password']"
      />
      <p class="text-caption">
        Username: 3–30 letters, numbers, or underscores. Password: 15–128
        characters.
      </p>
      <p v-if="error" class="text-negative" role="alert">{{ error }}</p>
      <q-btn
        type="submit"
        label="Sign Up"
        class="q-mt-sm full-width"
        :loading="submitting"
      />
      <q-btn flat to="/login" label="Log In" class="full-width" />
      <q-btn flat to="/" label="Change host connection" class="full-width" />
    </q-form>
  </q-page>
</template>

<script setup>
import axios from 'axios'
import { ref } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()
const username = ref('')
const password = ref('')
const submitting = ref(false)
const error = ref('')

async function submit() {
  if (submitting.value) return
  error.value = ''
  const apiBaseUrl = localStorage.getItem('apiBaseUrl')
  if (!apiBaseUrl) {
    error.value = 'Connect to a host first using Change host connection.'
    return
  }

  submitting.value = true
  try {
    await axios.post(
      `${apiBaseUrl}/api/auth/signup`,
      { username: username.value.trim(), password: password.value },
      { timeout: 5000 }
    )
    password.value = ''
    await router.push({ path: '/login', query: { registered: '1' } })
  } catch (err) {
    error.value =
      err.response?.data?.error ||
      'Could not reach the host. Check your connection and try again.'
  } finally {
    submitting.value = false
  }
}
</script>
