<template>
  <q-page class="q-ma-lg">
    <q-form
      class="fixed-center"
      style="width: 280px; max-width: 90vw"
      @submit="submit"
    >
      <p v-if="registered" class="text-positive" role="status">
        Account created. Log in to continue.
      </p>
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
        autocomplete="current-password"
        :rules="[value => !!value || 'Enter your password']"
      />
      <p v-if="error" class="text-negative" role="alert">{{ error }}</p>
      <q-btn
        type="submit"
        label="Log In"
        class="q-mt-sm full-width"
        :loading="submitting"
      />
      <q-btn flat to="/signup" label="Sign Up" class="full-width" />
      <q-btn flat to="/" label="Change host connection" class="full-width" />
    </q-form>
  </q-page>
</template>

<script setup>
import { login, authError } from '../services/auth'
import { computed, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'

const router = useRouter()
const route = useRoute()
const registered = computed(() => route.query.registered === '1')
const username = ref('')
const password = ref('')
const submitting = ref(false)
const error = ref(
  route.query.reason === 'expired'
    ? 'Your session expired. Please log in again.'
    : route.query.reason === 'offline'
      ? 'Could not verify your session. Check the host connection.'
      : ''
)

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
    await login(username.value, password.value)
    password.value = ''
    await router.push('/main')
  } catch (err) {
    error.value = authError(err)
  } finally {
    submitting.value = false
  }
}
</script>
