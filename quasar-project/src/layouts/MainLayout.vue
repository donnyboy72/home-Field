<template>
  <q-layout view="hHh lpR fFf">

    <q-header bordered="" class="bg-primary text-white">
      <q-toolbar>
        <q-toolbar-title>
          Homefield
        </q-toolbar-title>
        <q-btn label="X" to="/"/>
      </q-toolbar>
    </q-header>

    <q-page-container>
      <router-view />
    </q-page-container>

    <q-footer bordered="" class="bg-secondary text-white">
      <q-toolbar>
      </q-toolbar>
    </q-footer>

  </q-layout>
</template>
