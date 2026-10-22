<template>
  <q-page class="q-ma-lg">
    <q-form class="fixed-center" style="width: 260px" @submit="connect">
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
import { connectHost } from '../services/auth'
import { useRouter } from 'vue-router'

const router = useRouter()
const port = ref('50000')
const connecting = ref(false)
const error = ref('')

async function connect() {
  connecting.value = true
  error.value = ''

  try {
    await connectHost(port.value)
    await router.push('/login')
  } catch {
    error.value =
      'Could not connect to HomeField. Check the port and make sure Flask is running.'
  } finally {
    connecting.value = false
  }
}
</script>
