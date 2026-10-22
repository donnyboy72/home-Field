<template>
  <q-page class="q-ma-lg">
    <div class="fixed-center" style="max-width: 200px">
      <label for="username">Username:</label>
      <input class ="relative-top" v-model="username" id="username"/>
      <label for="password">Password:</label>
      <input type="password" label="Password" class ="relative-top" v-model="password" id="password"/>
      <q-btn label="Log In" class="q-mt-sm" style="min-width: 200px" @click=""/>
      <q-btn text-color="secondary" flat dense to="/signup" label="Sign Up" style="min-width: 200px"/>
    </div>
  </q-page>
</template>

