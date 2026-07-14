import { createRouter, createWebHistory } from 'vue-router'
import HomeView from '../views/HomeView.vue'
import UploadView from '../views/UploadView.vue'
import PaperListView from '../views/PaperListView.vue'
import PaperDetailView from '../views/PaperDetailView.vue'
import ReviewResultView from '../views/ReviewResultView.vue'
import MetricAnalysisView from '../views/MetricAnalysisView.vue'
import LoginView from '../views/LoginView.vue'
import RegisterView from '../views/RegisterView.vue'
import ForgotPasswordView from '../views/ForgotPasswordView.vue'
import ResetPasswordView from '../views/ResetPasswordView.vue'
import ProfileView from '../views/ProfileView.vue'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', name: 'home', component: HomeView },
    { path: '/login', name: 'login', component: LoginView, meta: { guest: true } },
    { path: '/register', name: 'register', component: RegisterView, meta: { guest: true } },
    { path: '/forgot-password', name: 'forgot-password', component: ForgotPasswordView, meta: { guest: true } },
    { path: '/reset-password', name: 'reset-password', component: ResetPasswordView, meta: { guest: true } },
    { path: '/profile', name: 'profile', component: ProfileView, meta: { requiresAuth: true } },
    { path: '/upload', name: 'upload', component: UploadView, meta: { requiresAuth: true } },
    { path: '/papers', name: 'papers', component: PaperListView, meta: { requiresAuth: true } },
    { path: '/papers/:id', name: 'paper-detail', component: PaperDetailView, meta: { requiresAuth: true } },
    { path: '/papers/:id/review', name: 'paper-review', component: ReviewResultView, meta: { requiresAuth: true } },
    { path: '/papers/:id/metrics', name: 'paper-metrics', component: MetricAnalysisView, meta: { requiresAuth: true } },
  ],
})

router.beforeEach(async (to, _from, next) => {
  const { useAuthStore } = await import('../stores/auth')
  const auth = useAuthStore()

  if (!auth.bootstrapped) {
    await auth.bootstrap()
  }

  if (to.meta.requiresAuth && !auth.isAuthenticated) {
    return next({ name: 'login', query: { redirect: to.fullPath } })
  }

  if (to.meta.guest && auth.isAuthenticated) {
    return next({ name: 'papers' })
  }

  next()
})

export default router
