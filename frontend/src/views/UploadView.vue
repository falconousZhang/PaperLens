<template>
  <div class="upload-page">
    <h2>上传论文</h2>
    <div class="drop-zone" :class="{ dragging }" @dragover.prevent="dragging = true" @dragleave="dragging = false" @drop.prevent="onDrop">
      <p v-if="!file">拖拽 PDF 文件到此处，或点击选择文件</p>
      <p v-else>{{ file.name }} ({{ (file.size / 1024 / 1024).toFixed(1) }} MB)</p>
      <input type="file" accept=".pdf" @change="onFileChange" ref="fileInput" style="display:none" />
      <button class="select-btn" @click="(fileInput as HTMLInputElement)?.click()">选择文件</button>
    </div>
    <div v-if="error" class="error">{{ error }}</div>
    <div v-if="uploading" class="progress-bar">
      <div class="progress-fill" :style="{ width: progress + '%' }"></div>
      <span>{{ progress }}%</span>
    </div>
    <button v-if="file && !uploading" class="upload-btn" @click="doUpload">上传</button>
    <router-link to="/papers" class="button-link back-link">返回列表</router-link>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { uploadPaper } from '../api'

const router = useRouter()
const file = ref<File | null>(null)
const fileInput = ref<HTMLInputElement | null>(null)
const uploading = ref(false)
const progress = ref(0)
const error = ref('')
const dragging = ref(false)

function onFileChange(e: Event) {
  const target = e.target as HTMLInputElement
  if (target.files && target.files[0]) selectFile(target.files[0])
}

function onDrop(e: DragEvent) {
  dragging.value = false
  if (e.dataTransfer?.files[0]) selectFile(e.dataTransfer.files[0])
}

function selectFile(f: File) {
  error.value = ''
  if (!f.name.toLowerCase().endsWith('.pdf')) {
    error.value = '仅支持 PDF 文件'
    return
  }
  if (f.size > 50 * 1024 * 1024) {
    error.value = '文件超过 50MB 限制'
    return
  }
  file.value = f
}

async function doUpload() {
  if (!file.value) return
  uploading.value = true
  progress.value = 0
  error.value = ''
  try {
    const result = await uploadPaper(file.value, (pct) => { progress.value = pct })
    router.push(`/papers/${result.id}/read`)
  } catch (e: unknown) {
    const msg = e instanceof Error ? e.message : '上传失败'
    error.value = msg
  } finally {
    uploading.value = false
  }
}
</script>

<style scoped>
.upload-page { max-width: 640px; margin: 2rem auto; padding: 0 1rem; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; }
h2 { color: #1a1a2e; }
.drop-zone { border: 2px dashed #ccc; border-radius: 12px; padding: 3rem; text-align: center; margin: 1.5rem 0; color: #888; }
.drop-zone.dragging { border-color: #1a1a2e; background: #f0f0ff; }
.select-btn { margin-top: 1rem; padding: 0.5rem 1.5rem; border-radius: 6px; border: 1px solid #ccc; background: #fff; cursor: pointer; }
.upload-btn { padding: 0.75rem 2rem; border-radius: 8px; background: #1a1a2e; color: #fff; border: none; cursor: pointer; font-size: 1rem; }
.error { color: #c62828; margin: 1rem 0; }
.progress-bar { position: relative; height: 24px; background: #e0e0e0; border-radius: 12px; margin: 1rem 0; overflow: hidden; }
.progress-fill { height: 100%; background: #4caf50; transition: width 0.3s; }
.progress-bar span { position: absolute; top: 2px; left: 50%; transform: translateX(-50%); font-size: 0.8rem; color: #333; }
.back-link { display: inline-block; margin-top: 1rem; color: #1a1a2e; }
</style>
