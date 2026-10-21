<template>
  <q-page class="q-ma-lg">
    <div class="fixed-center" style="max-width: 200px">
      <q-input label="Port #" class ="relative-top" mask="#####"/>
      <q-btn label="Submit" class="q-mt-sm" style="min-width: 200px" @click=""/>
    </div>
  </q-page>
</template>

<script>
  const apiURL = "..\..\backend\app.py"
  fetch(apiURL)
</script>
