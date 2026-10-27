<template>
  <q-layout view="hHh lpR fFf">
    <q-header bordered="" class="bg-primary text-white">
      <q-toolbar>
        <q-toolbar-title> Homefield </q-toolbar-title>
        <span v-if="signedInUser" class="q-mr-md">{{
          signedInUser.username
        }}</span>
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
</script>
