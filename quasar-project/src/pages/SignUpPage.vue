
<template>
    <!-- <meta http-equiv="Content-Security-Policy" 
        content="default-src 'self' data: gap: 'unsafe-eval' ws: ;
        style-src 'self 'unsafe-inline';
        script-src *;
        media-src *;
        font-src *;
        connect-src *;
        img-src 'self' data: content:; "
        > -->
  <q-page class="q-ma-lg">
    <div class="fixed-center" style="max-width: 200px">
        <form>
            <label for="signUpUsername">Username:</label>
            <input class ="relative-top" v-model="signUpForm.username" id="signUpUsername" />
            <label for="signUpPassword">Password:</label>
            <input type="password" label="Password" class ="relative-top" v-model="signUpForm.password" id="signUpPassword"/>
        </form>
            <q-btn label="Sign Up" class="q-mt-sm" style="min-width: 200px" @click=""/>
            <q-btn text-color="secondary" flat dense to="/" label="Log In" style="min-width: 200px"/>
    </div>
  </q-page>
</template>


<script>

    import axios from 'axios';

    

    export default{
        data(){
            return{
                signUpForm:{
                    username:''
                    ,password:''
                    ,
                }
            };
        },
        methods:{
            signup(payload){
                const path = "/api/auth/signup";
                axios.post(path, payload)
                .catch((error)=>{
                    console.log(error);
                })
            },
            handleSignUp(){
                let read = false;
                if(this.signUpForm.readp[0]){
                    read=true;
                }
                const payload = {
                    username: this.signUpForm.username,
                    password: this.signUpForm.password,
                };
                console.log("About to send payload...")
                this.signup(payload)
                
            },
        },
    };

    // import { ref } from 'vue'
    
    // async function handleClick(){
    //     const url = "https://localhost:50000/api/auth/signup"
    //     try {

    //         const response = await fetch(url, {
    //             method: "POST",
    //             headers: {
    //                 "Content-Type": "application/json"
    //             },
    //             body: JSON.stringify({username: username.value, password: password.value})
    //         });
    //         if (!response.ok) {
    //             throw new Error(`Response status: ${response.status}`);
    //         }
            
    //         const result = await response.json();
    //         console.log(result);
    //     } catch (error) {
    //         console.error("I broke dude");
    //         console.error(error.message);
    //     }
    // }
</script>