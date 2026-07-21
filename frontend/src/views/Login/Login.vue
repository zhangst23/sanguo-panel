<template>
  <div class="login-container">
    <a-card title="Sanguo Panel Login" :style="{ width: '400px' }">
      <a-form :model="form" @submit="handleSubmit">
        <a-form-item field="username" label="Username">
          <a-input v-model="form.username" placeholder="Enter username" />
        </a-form-item>
        <a-form-item field="password" label="Password">
          <a-input-password v-model="form.password" placeholder="Enter password" />
        </a-form-item>
        <a-form-item>
          <a-button type="primary" html-type="submit" long>Login</a-button>
        </a-form-item>
      </a-form>
    </a-card>
  </div>
</template>

<script setup>
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import request from '@/utils/request'
import { Message } from '@arco-design/web-vue'

const router = useRouter()
const loading = ref(false)
const form = reactive({
  username: '',
  password: '',
})

const handleSubmit = async () => {
  if (!form.username || !form.password) {
    Message.warning('Please enter username and password')
    return
  }
  
  loading.value = true
  try {
    const params = new URLSearchParams()
    params.append('username', form.username)
    params.append('password', form.password)
    
    const res = await request.post('/login/access-token', params)
    localStorage.setItem('token', res.access_token)
    Message.success('Login success')
    router.push('/dashboard')
  } catch (error) {
    console.error(error)
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-container {
  display: flex;
  justify-content: center;
  align-items: center;
  height: 100vh;
}
</style>
