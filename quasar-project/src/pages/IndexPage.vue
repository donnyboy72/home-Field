<template>
  <q-page class="q-ma-lg">
    <q-form
      class="fixed-center"
      style="width: 260px"
      @submit="connect"
    >
      <q-input
        v-model="port"
        label="Port #"
        mask="#####"
        :rules="[
          value =>
            (/^\d+$/.test(value) &&
              Number(value) >= 1 &&
              Number(value) <= 65535) ||
            'Enter a port between 1 and 65535'
        ]"
      />

      <q-btn
        type="submit"
        label="Connect"
        class="q-mt-sm full-width"
        :loading="connecting"
      />

      <p v-if="error" class="text-negative q-mt-md">
        {{ error }}
      </p>
    </q-form>
  </q-page>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()
const port = ref('50000')
const connecting = ref(false)
const error = ref('')

async function connect() {
  connecting.value = true
  error.value = ''

  // Assumes Flask runs on the same computer as this browser.
  const apiBaseUrl = `http://localhost:${Number(port.value)}`

  try {
    const response = await fetch(`${apiBaseUrl}/api/health`, {
      signal: AbortSignal.timeout(5000)
    })

    if (!response.ok) {
      throw new Error('Health check failed')
    }

    const data = await response.json()

    if (data.status !== 'running') {
      throw new Error('Unexpected health response')
    }

    localStorage.setItem('apiBaseUrl', apiBaseUrl)
    await router.push('/login')
  } catch {
    error.value =
      'Could not connect to HomeField. Check the port and make sure Flask is running.'
  } finally {
    connecting.value = false
  }
}
</script>