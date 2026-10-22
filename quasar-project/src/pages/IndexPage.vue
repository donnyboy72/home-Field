<template>
  <q-page class="q-ma-lg">
    <div class="fixed-center" style="max-width: 200px">
      <q-input label="Port #" class ="relative-top" mask="#####"/>
      <q-btn label="Submit" class="q-mt-sm" style="min-width: 200px" @click=""/>
    </div>
  </q-page>
</template>

<script>
  import axios from 'axios';

  export default{
    data(){
      return {
        status,
      };
    },
    methods: {
      health_check(){
        const path = 'http://localhost:50000/api/health';
        axios.get(path)
          .then((res)=>{
            this.status=res.data.status;
          })
          .catch((error)=>{
            console.error(error);
          });
      },
    },
    created(){
      this.health_check();
    },
  };
</script>
