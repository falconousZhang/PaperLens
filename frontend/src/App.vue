<template>
  <div class="app-layout">
    <nav v-if="auth.isAuthenticated" class="app-nav">
      <div class="nav-links">
        <router-link to="/papers">论文库</router-link>
        <router-link to="/upload">上传</router-link>
        <router-link v-if="auth.isAdmin" to="/admin">管理后台</router-link>
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
:global(*) {
  box-sizing: border-box;
}
:global(html),
:global(body),
:global(#app) {
  min-height: 100%;
  margin: 0;
}
:global(.button-link) {
  display: inline-flex;
  min-height: 34px;
  align-items: center;
  justify-content: center;
  padding: 0.45rem 0.9rem;
  border: 1px solid #d7dbe7;
  border-radius: 8px;
  color: #293352;
  background: #fff;
  text-decoration: none;
  font-size: 0.88rem;
  font-weight: 600;
  line-height: 1.2;
  cursor: pointer;
  transition: border-color 150ms ease, background 150ms ease, transform 150ms ease;
}
:global(.button-link:hover) {
  border-color: #9fa9c4;
  background: #f6f7fb;
  transform: translateY(-1px);
}
:global(.button-link--primary) {
  border-color: #1a1a2e;
  color: #fff;
  background: #1a1a2e;
}
:global(.button-link--primary:hover) {
  border-color: #2c3158;
  background: #2c3158;
}
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
