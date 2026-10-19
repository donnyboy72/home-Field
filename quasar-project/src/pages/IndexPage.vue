<template>
  <q-page class="q-ma-md">
    <div>
      <q-table
        grid
        flat
        bordered
        align="left"
        card-class="bg-accent"
        hide-bottom
        :rows="rows"
        
      />
    </div>

    <div
      class="absolute-bottom-right q-ma-lg"
      style="min-width: 360px">
      <q-expansion-item
        expand-separator
        outlined
        label="Create Task"
        header-class="bg-primary text-accent"
        class="q-ma-lg">
          <div class="q-ma-sm">
            <q-input dense outlined v-model="text" label="Title"/>
            <q-btn dense label="Submit" class="bg-primary text-accent full-width" @click="submitTask(text)"/>
          </div>
        </q-expansion-item>
      </div>
    
  </q-page>
</template>

<script setup>
  import {ref} from 'vue'

  const rows = ref([])

  function submitTask(title){

    const submission = {title}
    rows.value = [...rows.value.slice(0), submission]

  }
</script>
