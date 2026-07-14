import { computed, ref } from 'vue'
import { defineStore } from 'pinia'
import {
  changePassword as apiChangePassword,
  forgotPassword as apiForgotPassword,
  login as apiLogin,
  logout as apiLogout,
  logoutAll as apiLogoutAll,
  refreshToken,
  register as apiRegister,
  resetPassword as apiResetPassword,
  setAccessToken,
  updateMe as apiUpdateMe,
  type AuthUser,
} from '../api'


export const useAuthStore = defineStore('auth', () => {
  const user = ref<AuthUser | null>(null)
  const accessToken = ref<string | null>(null)
  const bootstrapped = ref(false)
  let bootstrapPromise: Promise<void> | null = null

  const isAuthenticated = computed(() => Boolean(accessToken.value && user.value))
  const isAdmin = computed(() => user.value?.role === 'ADMIN')

  function applySession(token: string, sessionUser: AuthUser): void {
    accessToken.value = token
    user.value = sessionUser
    setAccessToken(token)
  }

  function clearAuth(): void {
    accessToken.value = null
    user.value = null
    setAccessToken(null)
  }

  async function bootstrap(): Promise<void> {
    if (bootstrapped.value) return
    if (!bootstrapPromise) {
      bootstrapPromise = (async () => {
        try {
          const result = await refreshToken()
          applySession(result.access_token, result.user)
        } catch {
          clearAuth()
        } finally {
          bootstrapped.value = true
        }
      })().finally(() => {
        bootstrapPromise = null
      })
    }
    await bootstrapPromise
  }

  async function login(email: string, password: string): Promise<void> {
    const result = await apiLogin(email, password)
    applySession(result.access_token, result.user)
  }

  async function register(
    email: string,
    password: string,
    displayName: string,
  ): Promise<void> {
    const result = await apiRegister(email, password, displayName)
    applySession(result.access_token, result.user)
  }

  async function logout(): Promise<void> {
    try {
      await apiLogout()
    } catch {
      return
    } finally {
      clearAuth()
    }
  }

  async function logoutAll(): Promise<void> {
    try {
      await apiLogoutAll()
    } catch {
      return
    } finally {
      clearAuth()
    }
  }

  async function updateProfile(displayName?: string): Promise<void> {
    user.value = await apiUpdateMe(displayName)
  }

  async function changePassword(oldPassword: string, newPassword: string): Promise<void> {
    await apiChangePassword(oldPassword, newPassword)
    clearAuth()
  }

  async function forgotPassword(email: string): Promise<void> {
    await apiForgotPassword(email)
  }

  async function resetPassword(token: string, newPassword: string): Promise<void> {
    await apiResetPassword(token, newPassword)
  }

  return {
    user,
    accessToken,
    bootstrapped,
    isAuthenticated,
    isAdmin,
    bootstrap,
    clearAuth,
    login,
    register,
    logout,
    logoutAll,
    updateProfile,
    changePassword,
    forgotPassword,
    resetPassword,
  }
})
