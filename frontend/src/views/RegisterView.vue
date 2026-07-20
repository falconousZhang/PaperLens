<template>
  <div class="auth-page">
    <form class="auth-form" @submit.prevent="handleRegister">
      <h1>注册</h1>
      <div v-if="error" class="error">{{ error }}</div>
      <label>
        邮箱
        <input v-model="email" type="email" required autocomplete="email" />
      </label>
      <label>
        显示名称
        <input v-model="displayName" type="text" required maxlength="100" />
      </label>
      <label>
        密码（至少 8 个字符）
        <input v-model="password" type="password" required minlength="8" maxlength="128" autocomplete="new-password" />
      </label>
      <label>
        确认密码
        <input v-model="confirmPassword" type="password" required autocomplete="new-password" />
      </label>
      <button type="submit" :disabled="loading">{{ loading ? '注册中...' : '注册' }}</button>
      <div class="auth-links">
        <router-link to="/login" class="button-link">已有账号？登录</router-link>
      </div>
    </form>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { passwordCodePointLength } from '../utils/password'

const auth = useAuthStore()
const router = useRouter()

const email = ref('')
const displayName = ref('')
const password = ref('')
const confirmPassword = ref('')
const error = ref('')
const loading = ref(false)

async function handleRegister() {
  if (loading.value) return
  error.value = ''
  if (!email.value.includes('@')) {
    error.value = '请输入有效邮箱'
    return
  }
  if (!displayName.value.trim()) {
    error.value = '显示名称不能为空'
    return
  }
  if (password.value !== confirmPassword.value) {
    error.value = '两次输入的密码不一致'
    return
  }
  const passwordLength = passwordCodePointLength(password.value)
  if (passwordLength < 8) {
    error.value = '密码至少需要 8 个字符'
    return
  }
  if (passwordLength > 128) {
    error.value = '密码不能超过 128 个字符'
    return
  }
  loading.value = true
  try {
    await auth.register(email.value, password.value, displayName.value)
    await router.push('/papers')
  } catch (e: any) {
    error.value = e.response?.data?.error?.message || e.message || '注册失败'
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
  margin-top: 1rem;
  font-size: 0.85rem;
}
.auth-links a {
  color: #1a1a2e;
}
</style>
