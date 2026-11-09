<template>
  <q-page class="q-ma-lg">
    <q-form class="q-mx-auto" style="max-width: 420px" @submit="connect">
      <template v-if="discoveryAvailable">
        <h2 class="text-h6">Available hosts</h2>
        <q-btn
          label="Search again"
          type="button"
          :loading="searching"
          :disable="connecting"
          @click="searchHosts"
        />
        <p class="q-mt-md" role="status">{{ discoveryMessage }}</p>
        <q-list bordered separator v-if="hosts.length">
          <q-item
            v-for="server in hosts"
            :key="`${server.host}:${server.port}`"
          >
            <q-item-section>
              <q-item-label>{{ server.name }}</q-item-label>
              <q-item-label caption
                >{{ server.host }}:{{ server.port }}</q-item-label
              >
            </q-item-section>
            <q-item-section side>
              <q-btn
                label="Connect"
                type="button"
                :disable="connecting"
                @click="connectDiscovered(server)"
              />
            </q-item-section>
          </q-item>
        </q-list>
      </template>
      <h2 class="text-h6">Enter address manually</h2>
      <q-input
        v-model="host"
        label="Host IP address"
        hint="Use localhost when running on the host computer"
        :rules="[value => !!value.trim() || 'Enter the host address']"
      />

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
import { ref, onMounted, onBeforeUnmount } from 'vue'
import { connectHost } from '../services/auth'
import { useRouter } from 'vue-router'

const host = ref('localhost')
const router = useRouter()
const port = ref('50000')
const connecting = ref(false)
const error = ref('')
const discoveryAvailable = !!window.homefield?.discoverHosts
const hosts = ref([])
const searching = ref(false)
const discoveryMessage = ref('')
let active = true

async function searchHosts() {
  if (!discoveryAvailable || searching.value) return
  searching.value = true
  hosts.value = []
  discoveryMessage.value = 'Searching the local network…'
  try {
    const results = await window.homefield.discoverHosts()
    if (!active) return
    hosts.value = results
    discoveryMessage.value = results.length
      ? 'Choose your host to connect.'
      : 'No hosts found. Start Flask on the host, search again, or enter its address below.'
  } catch {
    if (active)
      discoveryMessage.value =
        'Discovery unavailable. Enter the host address below.'
  } finally {
    if (active) searching.value = false
  }
}

function connectDiscovered(server) {
  host.value = server.host
  port.value = String(server.port)
  // Use the same validation and health check as manual entry; never auto-login.
  return connect()
}

onMounted(searchHosts)
onBeforeUnmount(() => {
  active = false
})

async function connect() {
  connecting.value = true
  error.value = ''

  try {
    await connectHost(host.value, port.value)
    await router.push('/login')
  } catch {
    error.value =
      'Could not connect to HomeField. Check the port and make sure Flask is running.'
  } finally {
    connecting.value = false
  }
}
</script>
