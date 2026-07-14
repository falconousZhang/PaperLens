<template>
  <div class="profile-page">
    <div class="profile-card">
      <h1>个人资料</h1>
      <div v-if="auth.user" class="profile-info">
        <div class="info-row">
          <span class="label">邮箱</span>
          <span>{{ auth.user.email }}</span>
        </div>
        <div class="info-row">
          <span class="label">角色</span>
          <span>{{ auth.user.role }}</span>
        </div>
        <div class="info-row">
          <span class="label">状态</span>
          <span>{{ auth.user.status }}</span>
        </div>
        <div class="info-row">
          <span class="label">注册时间</span>
          <span>{{ new Date(auth.user.created_at).toLocaleDateString() }}</span>
        </div>
      </div>

      <form class="profile-form" @submit.prevent="handleUpdateProfile">
        <h2>修改显示名称</h2>
        <div v-if="profileError" class="error">{{ profileError }}</div>
        <div v-if="profileSuccess" class="success">{{ profileSuccess }}</div>
        <label>
          显示名称
          <input v-model="displayName" type="text" required maxlength="100" />
        </label>
        <button type="submit" :disabled="profileLoading">保存</button>
      </form>

      <form class="profile-form" @submit.prevent="handleChangePassword">
        <h2>修改密码</h2>
        <div v-if="pwError" class="error">{{ pwError }}</div>
        <div v-if="pwSuccess" class="success">{{ pwSuccess }}</div>
        <label>
          当前密码
          <input v-model="currentPassword" type="password" required autocomplete="current-password" />
        </label>
        <label>
          新密码（至少 15 个字符）
          <input v-model="newPassword" type="password" required autocomplete="new-password" />
        </label>
        <button type="submit" :disabled="pwLoading">修改密码</button>
      </form>

      <div class="danger-zone">
        <h2>退出登录</h2>
        <button class="btn-danger" @click="handleLogoutAll">退出所有设备</button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { passwordCodePointLength } from '../utils/password'

const auth = useAuthStore()
const router = useRouter()

const displayName = ref(auth.user?.display_name || '')
const profileError = ref('')
const profileSuccess = ref('')
const profileLoading = ref(false)

const currentPassword = ref('')
const newPassword = ref('')
const pwError = ref('')
const pwSuccess = ref('')
const pwLoading = ref(false)

async function handleUpdateProfile() {
  if (profileLoading.value) return
  profileError.value = ''
  profileSuccess.value = ''
  if (!displayName.value.trim()) {
    profileError.value = '显示名称不能为空'
    return
  }
  profileLoading.value = true
  try {
    await auth.updateProfile(displayName.value)
    profileSuccess.value = '已保存'
  } catch (e: any) {
    profileError.value = e.response?.data?.error?.message || e.message || '保存失败'
  } finally {
    profileLoading.value = false
  }
}

async function handleChangePassword() {
  if (pwLoading.value) return
  pwError.value = ''
  pwSuccess.value = ''
  const newPasswordLength = passwordCodePointLength(newPassword.value)
  if (newPasswordLength < 15 || newPasswordLength > 128) {
    pwError.value = '新密码长度必须为 15～128 个字符'
    return
  }
  pwLoading.value = true
  try {
    await auth.changePassword(currentPassword.value, newPassword.value)
    pwSuccess.value = '密码已修改，请重新登录'
    setTimeout(() => router.push('/login'), 1500)
  } catch (e: any) {
    pwError.value = e.response?.data?.error?.message || e.message || '修改失败'
  } finally {
    pwLoading.value = false
  }
}

async function handleLogoutAll() {
  await auth.logoutAll()
  router.push('/login')
}
</script>

<style scoped>
.profile-page {
  display: flex;
  justify-content: center;
  padding: 2rem;
}
.profile-card {
  width: 480px;
  background: #fff;
  border-radius: 8px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.1);
  padding: 2rem;
}
.profile-card h1 {
  margin-bottom: 1rem;
}
.profile-info {
  margin-bottom: 2rem;
}
.info-row {
  display: flex;
  gap: 1rem;
  padding: 0.5rem 0;
  border-bottom: 1px solid #eee;
}
.info-row .label {
  width: 80px;
  color: #888;
  font-size: 0.9rem;
}
.profile-form {
  margin-top: 1.5rem;
  padding-top: 1.5rem;
  border-top: 1px solid #eee;
}
.profile-form h2 {
  font-size: 1.1rem;
  margin-bottom: 1rem;
}
.profile-form label {
  display: block;
  margin-bottom: 0.75rem;
  font-size: 0.9rem;
  color: #555;
}
.profile-form input {
  display: block;
  width: 100%;
  margin-top: 0.3rem;
  padding: 0.5rem 0.75rem;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-size: 1rem;
}
.profile-form button {
  margin-top: 0.5rem;
  padding: 0.5rem 1.5rem;
  background: #1a1a2e;
  color: #fff;
  border: none;
  border-radius: 4px;
  cursor: pointer;
}
.profile-form button:disabled {
  opacity: 0.6;
}
.error {
  background: #fee;
  color: #c33;
  padding: 0.5rem;
  border-radius: 4px;
  margin-bottom: 0.75rem;
  font-size: 0.9rem;
}
.success {
  background: #efe;
  color: #3a3;
  padding: 0.5rem;
  border-radius: 4px;
  margin-bottom: 0.75rem;
  font-size: 0.9rem;
}
.danger-zone {
  margin-top: 1.5rem;
  padding-top: 1.5rem;
  border-top: 1px solid #eee;
}
.danger-zone h2 {
  font-size: 1.1rem;
  margin-bottom: 0.75rem;
  color: #c33;
}
.btn-danger {
  padding: 0.5rem 1.5rem;
  background: #c33;
  color: #fff;
  border: none;
  border-radius: 4px;
  cursor: pointer;
}
</style>
