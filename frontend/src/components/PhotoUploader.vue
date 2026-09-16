<template>
  <div class="photo-uploader">
    <!-- 隐藏式文件输入：拍照 (调用后置摄像头) 与 本地图库/相册导入 -->
    <input
      ref="cameraInputRef"
      type="file"
      accept="image/*"
      capture="environment"
      style="display: none;"
      @change="handleFilesSelected($event)"
    />
    <input
      ref="galleryInputRef"
      type="file"
      accept="image/*"
      multiple
      style="display: none;"
      @change="handleFilesSelected($event)"
    />

    <!-- 操作按钮区 -->
    <div class="action-bar">
      <div class="btn-group">
        <el-button
          type="primary"
          plain
          size="small"
          :loading="uploading"
          :disabled="isMaxReached"
          @click="triggerCamera"
        >
          📷 拍照上传
        </el-button>
        <el-button
          type="success"
          plain
          size="small"
          :loading="uploading"
          :disabled="isMaxReached"
          @click="triggerGallery"
        >
          🖼️ 本地图库导入
        </el-button>
      </div>

      <div class="photo-stats">
        <span v-if="photoList.length > 0" class="count-badge">已选 {{ photoList.length }}/{{ maxCount }} 张</span>
        <el-button link type="info" size="small" @click="showManualInput = !showManualInput">
          {{ showManualInput ? '隐藏文本链接' : '🔗 手动填入URL' }}
        </el-button>
      </div>
    </div>

    <div v-if="tip" class="uploader-tip">{{ tip }}</div>

    <!-- 缩略图预览列表网格 -->
    <div class="photo-grid" v-if="photoList.length > 0 || uploading">
      <div v-for="(url, idx) in photoList" :key="idx" class="photo-item">
        <el-image
          :src="url"
          :preview-src-list="photoList"
          :initial-index="idx"
          fit="cover"
          class="thumb-img"
          preview-teleported
        />
        <div class="photo-badge">{{ idx + 1 }}</div>
        <button
          type="button"
          class="delete-btn"
          title="移除此照片"
          @click.stop="removePhoto(idx)"
        >
          ✕
        </button>
      </div>

      <!-- 上传中占位指示器 -->
      <div v-if="uploading" class="uploading-placeholder">
        <el-icon class="is-loading"><Loading /></el-icon>
        <span class="uploading-text">上传中...</span>
      </div>
    </div>

    <!-- 备用手动编辑 URL 区域 (支持复制、直接粘贴多张逗号分隔的 URL) -->
    <div v-if="showManualInput" class="manual-input-box">
      <el-input
        v-model="manualText"
        type="textarea"
        :rows="2"
        placeholder="照片URL，多张以逗号隔开 (如 /uploads/repairs/motor.jpg)"
        @input="onManualInput"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { Loading } from '@element-plus/icons-vue'
import apiClient from '../api/client'

const props = withDefaults(
  defineProps<{
    modelValue?: string
    maxCount?: number
    tip?: string
  }>(),
  {
    modelValue: '',
    maxCount: 9,
    tip: '支持移动端现场直接拍照或从本地相册导入，记录真实排除达标现场'
  }
)

const emit = defineEmits<{
  (e: 'update:modelValue', value: string): void
}>()

const cameraInputRef = ref<HTMLInputElement | null>(null)
const galleryInputRef = ref<HTMLInputElement | null>(null)
const uploading = ref(false)
const showManualInput = ref(false)
const manualText = ref('')

// 将逗号分隔的字符串解析为数组
const photoList = computed(() => {
  if (!props.modelValue) return []
  return props.modelValue
    .split(',')
    .map(s => s.trim())
    .filter(Boolean)
})

const isMaxReached = computed(() => photoList.value.length >= props.maxCount)

watch(
  () => props.modelValue,
  newVal => {
    manualText.value = newVal || ''
  },
  { immediate: true }
)

function triggerCamera() {
  if (isMaxReached.value) {
    ElMessage.warning(`最多仅支持上传 ${props.maxCount} 张照片`)
    return
  }
  cameraInputRef.value?.click()
}

function triggerGallery() {
  if (isMaxReached.value) {
    ElMessage.warning(`最多仅支持上传 ${props.maxCount} 张照片`)
    return
  }
  galleryInputRef.value?.click()
}

async function handleFilesSelected(event: Event) {
  const target = event.target as HTMLInputElement
  const files = target.files
  if (!files || files.length === 0) return

  const remainingSlots = props.maxCount - photoList.value.length
  if (remainingSlots <= 0) {
    ElMessage.warning(`最多仅支持上传 ${props.maxCount} 张照片`)
    target.value = ''
    return
  }

  const filesToUpload = Array.from(files).slice(0, remainingSlots)
  uploading.value = true

  const newUrls: string[] = []
  try {
    for (const file of filesToUpload) {
      // 校验大小 (15MB)
      if (file.size > 15 * 1024 * 1024) {
        ElMessage.error(`照片 [${file.name}] 超过 15MB，已跳过`)
        continue
      }

      const formData = new FormData()
      formData.append('file', file)

      const res = await apiClient.post('/work-orders/upload-photo', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      })

      if (res.data?.url) {
        newUrls.push(res.data.url)
      }
    }

    if (newUrls.length > 0) {
      const merged = [...photoList.value, ...newUrls]
      emit('update:modelValue', merged.join(', '))
      ElMessage.success(`成功上传 ${newUrls.length} 张照片`)
    }
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '照片上传失败，请重试')
  } finally {
    uploading.value = false
    target.value = ''
  }
}

function removePhoto(index: number) {
  const updated = photoList.value.filter((_, i) => i !== index)
  emit('update:modelValue', updated.join(', '))
}

function onManualInput(val: string) {
  emit('update:modelValue', val)
}
</script>

<style scoped>
.photo-uploader {
  width: 100%;
}
.action-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
}
.btn-group {
  display: flex;
  gap: 8px;
}
.photo-stats {
  display: flex;
  align-items: center;
  gap: 8px;
}
.count-badge {
  font-size: 12px;
  color: #64748b;
}
.uploader-tip {
  font-size: 12px;
  color: #94a3b8;
  margin-top: 4px;
}
.photo-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin-top: 10px;
}
.photo-item {
  position: relative;
  width: 100px;
  height: 100px;
  border-radius: 6px;
  overflow: hidden;
  border: 1px solid #e2e8f0;
  background-color: #f8fafc;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
}
.thumb-img {
  width: 100%;
  height: 100%;
  display: block;
}
.photo-badge {
  position: absolute;
  bottom: 2px;
  left: 4px;
  background: rgba(0, 0, 0, 0.55);
  color: #fff;
  font-size: 10px;
  padding: 1px 5px;
  border-radius: 4px;
  pointer-events: none;
}
.delete-btn {
  position: absolute;
  top: 3px;
  right: 3px;
  width: 20px;
  height: 20px;
  background: rgba(239, 68, 68, 0.9);
  color: #fff;
  border: none;
  border-radius: 50%;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 11px;
  font-weight: bold;
  line-height: 1;
  transition: transform 0.15s, background 0.15s;
}
.delete-btn:hover {
  background: #dc2626;
  transform: scale(1.15);
}
.uploading-placeholder {
  width: 100px;
  height: 100px;
  border: 1px dashed #38bdf8;
  border-radius: 6px;
  background-color: #f0f9ff;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 6px;
  color: #0284c7;
  font-size: 12px;
}
.manual-input-box {
  margin-top: 8px;
}
</style>
