<template>
  <q-page class="q-ma-md">
    <div>
      <q-table
        
        flat
        bordered
        card-class="bg-accent"
        hide-bottom
        :rows="tasks">
        <template v-slot:body-cell-action="props">
            <q-td :props="props">
                <q-btn label="Hi"/>
            </q-td>
        </template>
    </q-table>
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
            <q-btn dense label="Submit" class="bg-primary text-accent full-width" @click="createTask"/>
          </div>
        </q-expansion-item>
      </div>
    
  </q-page>
</template>

<script>
  import {ref} from 'vue'
  import axios from 'axios'


    export default{
        setup(){
            const tasks = ref([])
            const loadTasks = async() => {
                try{
                const response = await axios.get("/api/tasks")
                tasks.value = response.data.tasks
                }catch (err){
                    console.log(err)
                }
            }

            loadTasks()

            const createTask = () => {
                axios.post("/api/tasks", JSON.stringify({
                    title: "foo"
                })).then(response => {console.log(response)})
            }
            return{
                tasks,
                createTask
            }
        }

    }

  
</script>
