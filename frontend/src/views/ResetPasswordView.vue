<template>
  <div class="auth-page">
    <form class="auth-form" @submit.prevent="handleSubmit">
      <h1>重置密码</h1>
      <div v-if="error" class="error">{{ error }}</div>
      <div v-if="success" class="success">{{ success }}</div>
      <label>
        新密码（至少 8 个字符）
        <input v-model="newPassword" type="password" required minlength="8" maxlength="128" autocomplete="new-password" />
      </label>
      <label>
        确认新密码
        <input v-model="confirmPassword" type="password" required autocomplete="new-password" />
      </label>
      <button type="submit" :disabled="loading">{{ loading ? '重置中...' : '重置密码' }}</button>
      <div class="auth-links">
        <router-link to="/login" class="button-link">返回登录</router-link>
      </div>
    </form>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { passwordCodePointLength } from '../utils/password'

const auth = useAuthStore()
const route = useRoute()
const router = useRouter()

const newPassword = ref('')
const confirmPassword = ref('')
const error = ref('')
const success = ref('')
const loading = ref(false)

async function handleSubmit() {
  if (loading.value) return
  error.value = ''
  if (newPassword.value !== confirmPassword.value) {
    error.value = '两次输入的密码不一致'
    return
  }
  const passwordLength = passwordCodePointLength(newPassword.value)
  if (passwordLength < 8) {
    error.value = '密码至少需要 8 个字符'
    return
  }
  if (passwordLength > 128) {
    error.value = '密码不能超过 128 个字符'
    return
  }
  const tokenValue = route.query.token
  if (typeof tokenValue !== 'string' || !tokenValue) {
    error.value = '缺少重置令牌'
    return
  }
  loading.value = true
  try {
    await auth.resetPassword(tokenValue, newPassword.value)
    success.value = '密码已重置，请登录'
    setTimeout(() => router.push('/login'), 1500)
  } catch (e: any) {
    error.value = e.response?.data?.error?.message || e.message || '重置失败'
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
