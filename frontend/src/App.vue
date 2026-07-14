<template>
  <div class="app-layout">
    <nav v-if="auth.isAuthenticated" class="app-nav">
      <div class="nav-links">
        <router-link to="/">首页</router-link>
        <router-link to="/papers">论文</router-link>
        <router-link to="/upload">上传</router-link>
      </div>
      <div class="nav-user">
        <router-link to="/profile">{{ auth.user?.display_name }}</router-link>
        <button @click="handleLogout">退出</button>
      </div>
    </nav>
    <main>
      <router-view />
    </main>
  </div>
</template>

<script setup lang="ts">
import { useAuthStore } from './stores/auth'
import { useRouter } from 'vue-router'

const auth = useAuthStore()
const router = useRouter()

async function handleLogout() {
  await auth.logout()
  router.push('/login')
}
</script>

<style scoped>
.app-layout {
  min-height: 100vh;
}
.app-nav {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0 1.5rem;
  height: 48px;
  background: #1a1a2e;
  color: #fff;
}
.nav-links {
  display: flex;
  gap: 1rem;
}
.nav-links a {
  color: #ccc;
  text-decoration: none;
}
.nav-links a:hover,
.nav-links a.router-link-active {
  color: #fff;
}
.nav-user {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}
.nav-user a {
  color: #ccc;
  text-decoration: none;
}
.nav-user a:hover {
  color: #fff;
}
.nav-user button {
  background: none;
  border: 1px solid #666;
  color: #ccc;
  padding: 0.2rem 0.6rem;
  border-radius: 4px;
  cursor: pointer;
  font-size: 0.85rem;
}
.nav-user button:hover {
  color: #fff;
  border-color: #999;
}
</style>
