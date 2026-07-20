<template>
  <div class="auth-page">
    <form class="auth-form" @submit.prevent="handleSubmit">
      <h1>忘记密码</h1>
      <div v-if="success" class="success">{{ success }}</div>
      <div v-if="error" class="error">{{ error }}</div>
      <label>
        邮箱
        <input v-model="email" type="email" required autocomplete="email" />
      </label>
      <button type="submit" :disabled="loading">{{ loading ? '发送中...' : '发送重置链接' }}</button>
      <div class="auth-links">
        <router-link to="/login" class="button-link">返回登录</router-link>
      </div>
    </form>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useAuthStore } from '../stores/auth'

const auth = useAuthStore()

const email = ref('')
const error = ref('')
const success = ref('')
const loading = ref(false)

async function handleSubmit() {
  if (loading.value) return
  error.value = ''
  success.value = ''
  if (!email.value.includes('@')) {
    error.value = '请输入有效邮箱'
    return
  }
  loading.value = true
  try {
    await auth.forgotPassword(email.value)
    success.value = '若账号存在且通知服务可用，将发送密码重置指引'
  } catch (e: any) {
    error.value = e.response?.data?.error?.message || e.message || '请求失败'
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.auth-page {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 80vh;
}
.auth-form {
  width: 360px;
  padding: 2rem;
  background: #fff;
  border-radius: 8px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.1);
}
.auth-form h1 {
  text-align: center;
  margin-bottom: 1.5rem;
  font-size: 1.5rem;
}
.auth-form label {
  display: block;
  margin-bottom: 1rem;
  font-size: 0.9rem;
  color: #555;
}
.auth-form input {
  display: block;
  width: 100%;
  margin-top: 0.3rem;
  padding: 0.5rem 0.75rem;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-size: 1rem;
}
.auth-form button {
  width: 100%;
  padding: 0.6rem;
  background: #1a1a2e;
  color: #fff;
  border: none;
  border-radius: 4px;
  font-size: 1rem;
  cursor: pointer;
}
.auth-form button:disabled {
  opacity: 0.6;
}
.error {
  background: #fee;
  color: #c33;
  padding: 0.5rem;
  border-radius: 4px;
  margin-bottom: 1rem;
  font-size: 0.9rem;
}
.success {
  background: #efe;
  color: #3a3;
  padding: 0.5rem;
  border-radius: 4px;
  margin-bottom: 1rem;
  font-size: 0.9rem;
}
.auth-links {
  margin-top: 1rem;
  font-size: 0.85rem;
}
.auth-links a {
  color: #1a1a2e;
}
</style>
