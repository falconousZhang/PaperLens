<template>
  <div class="auth-page">
    <form class="auth-form" @submit.prevent="handleLogin">
      <h1>登录</h1>
      <div v-if="error" class="error">{{ error }}</div>
      <label>
        邮箱
        <input v-model="email" type="email" required autocomplete="email" />
      </label>
      <label>
        密码
        <input v-model="password" type="password" required autocomplete="current-password" />
      </label>
      <button type="submit" :disabled="loading">{{ loading ? '登录中...' : '登录' }}</button>
      <div class="auth-links">
        <router-link to="/forgot-password" class="button-link">忘记密码？</router-link>
        <router-link to="/register" class="button-link">注册账号</router-link>
      </div>
    </form>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { safeInternalRedirect } from '../router/safeRedirect'
import { passwordCodePointLength } from '../utils/password'

const auth = useAuthStore()
const router = useRouter()
const route = useRoute()

const email = ref('')
const password = ref('')
const error = ref('')
const loading = ref(false)

async function handleLogin() {
  if (loading.value) return
  error.value = ''
  if (!email.value.includes('@')) {
    error.value = '请输入有效邮箱'
    return
  }
  if (!password.value || passwordCodePointLength(password.value) > 128) {
    error.value = '请输入有效密码'
    return
  }
  loading.value = true
  try {
    await auth.login(email.value, password.value)
    await router.push(safeInternalRedirect(route.query.redirect))
  } catch (e: any) {
    error.value = e.response?.data?.error?.message || e.message || '登录失败'
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
.auth-links {
  display: flex;
  justify-content: space-between;
  margin-top: 1rem;
  font-size: 0.85rem;
}
.auth-links a {
  color: #1a1a2e;
}
</style>
