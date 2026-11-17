<template>
  <q-layout view="hHh lpR fFf">
    <q-header bordered="" class="bg-primary text-white">
      <q-toolbar>
        <q-toolbar-title> Homefield </q-toolbar-title>
        <span v-if="signedInUser" class="q-mr-md">{{
          signedInUser.username
        }}</span>
        <q-btn
          flat
          round
          color="white"
          :icon="Dark.isActive ? 'light_mode' : 'dark_mode'"
          :aria-label="
            Dark.isActive ? 'Switch to light mode' : 'Switch to dark mode'
          "
          @click="toggleDarkMode"
        >
          <q-tooltip>{{
            Dark.isActive ? 'Switch to light mode' : 'Switch to dark mode'
          }}</q-tooltip>
        </q-btn>
        <q-btn
          v-if="signedInUser"
          label="Log out"
          :loading="loggingOut"
          @click="signOut"
        />
        <q-btn v-else label="Connection" href="/" />
      </q-toolbar>
    </q-header>

    <q-page-container>
      <q-banner
        v-if="logoutError"
        class="bg-red-1 text-negative"
        role="alert"
        >{{ logoutError }}</q-banner
      >
      <router-view />
    </q-page-container>
  </q-layout>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { signedInUser, logout, authError } from '../services/auth'
import { Dark } from 'quasar'

const router = useRouter()
const loggingOut = ref(false)
const logoutError = ref('')
async function signOut() {
  loggingOut.value = true
  logoutError.value = ''
  try {
    await logout()
    await router.replace('/login')
  } catch (error) {
    logoutError.value = authError(error)
  } finally {
    loggingOut.value = false
  }
}
function toggleDarkMode() {
  Dark.toggle()
}
</script>
