import { createRouter, createWebHistory } from 'vue-router'
import HomeView from '../views/HomeView.vue'
import UploadView from '../views/UploadView.vue'
import PaperListView from '../views/PaperListView.vue'
import PaperDetailView from '../views/PaperDetailView.vue'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', name: 'home', component: HomeView },
    { path: '/upload', name: 'upload', component: UploadView },
    { path: '/papers', name: 'papers', component: PaperListView },
    { path: '/papers/:id', name: 'paper-detail', component: PaperDetailView },
  ],
})

export default router
