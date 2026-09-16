<template>
  <div class="docs-page">
    <el-row :gutter="16" class="docs-layout">
      <!-- 左侧：系统文档目录导航与检索 -->
      <el-col :span="7" class="docs-nav-col">
        <el-card shadow="hover" class="docs-nav-card">
          <template #header>
            <div class="nav-header">
              <span class="nav-title">📚 工业系统设计文档库</span>
              <el-tag size="small" type="primary" effect="plain">{{ docList.length }} 篇标准文档</el-tag>
            </div>
          </template>

          <div class="search-box">
            <el-input
              v-model="searchKeyword"
              placeholder="搜索文档名称 / 规范条目..."
              clearable
              prefix-icon="Search"
            />
          </div>

          <div class="category-tabs">
            <el-radio-group v-model="selectedCategory" size="small">
              <el-radio-button value="ALL">全部</el-radio-button>
              <el-radio-button value="需求规格">需求</el-radio-button>
              <el-radio-button value="系统设计">系统</el-radio-button>
              <el-radio-button value="软件设计">软件</el-radio-button>
              <el-radio-button value="部署运维">运维</el-radio-button>
              <el-radio-button value="现场实操">实操SOP</el-radio-button>
            </el-radio-group>
          </div>

          <div class="doc-items-container" v-loading="listLoading">
            <div
              v-for="item in filteredDocList"
              :key="item.id"
              class="doc-nav-item"
              :class="{ 'is-active': currentDocId === item.id }"
              @click="selectDoc(item.id)"
            >
              <div class="doc-item-top">
                <el-tag size="small" :type="item.badge_type" effect="dark">
                  {{ item.badge }}
                </el-tag>
                <span class="doc-size">{{ (item.size_bytes / 1024).toFixed(1) }} KB</span>
              </div>
              <div class="doc-item-title">{{ item.title }}</div>
              <div class="doc-item-desc">{{ item.description }}</div>
              <div class="doc-item-meta">
                <span>📄 {{ item.file_name }}</span>
              </div>
            </div>

            <div v-if="filteredDocList.length === 0" class="empty-docs">
              未找到匹配的设计文档
            </div>
          </div>
        </el-card>
      </el-col>

      <!-- 右侧：高清 Markdown 在线渲染与阅读器 -->
      <el-col :span="17" class="docs-content-col">
        <el-card shadow="hover" class="docs-reader-card" v-loading="contentLoading">
          <template #header>
            <div class="reader-header">
              <div class="reader-header-left">
                <el-tag v-if="currentDoc" :type="currentDoc.badge_type" effect="dark" style="margin-right: 8px;">
                  {{ currentDoc.badge }}
                </el-tag>
                <span class="reader-title">{{ currentDoc?.title || '正在加载系统设计文档...' }}</span>
              </div>
              <div class="reader-header-right">
                <span v-if="currentDoc" class="reader-time">
                  🕒 更新时间：{{ currentDoc.updated_at }}
                </span>
                <el-button size="small" @click="fetchDocContent(currentDocId)">
                  🔄 刷新
                </el-button>
              </div>
            </div>
          </template>

          <div class="reader-scroll-area">
            <div v-if="currentHtml" class="markdown-body" v-html="currentHtml"></div>
            <div v-else-if="!contentLoading" class="empty-content">
              <el-empty description="请选择左侧文档以在线浏览" />
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { marked } from 'marked'
import { ElMessage } from 'element-plus'
import apiClient from '../../api/client'

const listLoading = ref(false)
const contentLoading = ref(false)
const docList = ref<any[]>([])
const currentDocId = ref('crs')
const currentDoc = ref<any>(null)
const currentHtml = ref('')
const searchKeyword = ref('')
const selectedCategory = ref('ALL')

// 配置 marked 解析器
marked.setOptions({
  gfm: true,
  breaks: true
})

const filteredDocList = computed(() => {
  return docList.value.filter(doc => {
    const matchCat = selectedCategory.value === 'ALL' || doc.category === selectedCategory.value
    const matchKw = !searchKeyword.value || 
      doc.title.toLowerCase().includes(searchKeyword.value.toLowerCase()) ||
      doc.description.toLowerCase().includes(searchKeyword.value.toLowerCase()) ||
      doc.file_name.toLowerCase().includes(searchKeyword.value.toLowerCase())
    return matchCat && matchKw
  })
})

async function fetchDocList() {
  listLoading.value = true
  try {
    const res = await apiClient.get('/docs')
    docList.value = res.data
    if (docList.value.length > 0 && !currentDocId.value) {
      currentDocId.value = docList.value[0].id
    }
    if (currentDocId.value) {
      await fetchDocContent(currentDocId.value)
    }
  } catch (e) {
    ElMessage.error('获取系统文档目录失败')
  } finally {
    listLoading.value = false
  }
}

async function fetchDocContent(docId: string) {
  if (!docId) return
  contentLoading.value = true
  try {
    const res = await apiClient.get(`/docs/${docId}`)
    currentDoc.value = res.data
    const parsed = marked.parse(res.data.content || '')
    currentHtml.value = typeof parsed === 'string' ? parsed : await parsed
  } catch (e: any) {
    ElMessage.error(e.response?.data?.detail || '读取文档内容失败')
  } finally {
    contentLoading.value = false
  }
}

function selectDoc(docId: string) {
  currentDocId.value = docId
  fetchDocContent(docId)
}

onMounted(() => {
  fetchDocList()
})
</script>

<style scoped>
.docs-page {
  height: calc(100vh - 110px);
}
.docs-layout {
  height: 100%;
}
.docs-nav-col, .docs-content-col {
  height: 100%;
}
.docs-nav-card, .docs-reader-card {
  height: 100%;
  display: flex;
  flex-direction: column;
}
.docs-nav-card :deep(.el-card__body),
.docs-reader-card :deep(.el-card__body) {
  flex: 1;
  overflow: hidden;
  padding: 16px;
  display: flex;
  flex-direction: column;
}

.nav-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.nav-title {
  font-weight: bold;
  font-size: 15px;
  color: #1e293b;
}

.search-box {
  margin-bottom: 12px;
}
.category-tabs {
  margin-bottom: 12px;
  display: flex;
  justify-content: center;
}

.doc-items-container {
  flex: 1;
  overflow-y: auto;
  padding-right: 4px;
}
.doc-nav-item {
  padding: 12px;
  border-radius: 8px;
  border: 1px solid #e2e8f0;
  margin-bottom: 10px;
  background-color: #ffffff;
  cursor: pointer;
  transition: all 0.2s ease;
}
.doc-nav-item:hover {
  border-color: #3b82f6;
  background-color: #f8fafc;
}
.doc-nav-item.is-active {
  border-color: #2563eb;
  background-color: #eff6ff;
  box-shadow: 0 1px 3px rgba(37, 99, 235, 0.15);
}

.doc-item-top {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 6px;
}
.doc-size {
  font-size: 11px;
  color: #94a3b8;
}
.doc-item-title {
  font-size: 14px;
  font-weight: 600;
  color: #1e293b;
  margin-bottom: 4px;
}
.doc-item-desc {
  font-size: 12px;
  color: #64748b;
  line-height: 1.4;
  margin-bottom: 6px;
}
.doc-item-meta {
  font-size: 11px;
  color: #94a3b8;
  font-family: monospace;
}

.empty-docs {
  text-align: center;
  padding: 30px;
  color: #94a3b8;
  font-size: 13px;
}

.reader-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.reader-header-left {
  display: flex;
  align-items: center;
}
.reader-title {
  font-weight: bold;
  font-size: 16px;
  color: #0f172a;
}
.reader-time {
  font-size: 12px;
  color: #94a3b8;
  margin-right: 12px;
}

.reader-scroll-area {
  flex: 1;
  overflow-y: auto;
  padding: 10px 24px 30px 14px;
}
.empty-content {
  display: flex;
  justify-content: center;
  align-items: center;
  height: 100%;
}

/* GitHub 风格 Markdown 渲染样式规范 */
.markdown-body {
  font-size: 14px;
  line-height: 1.7;
  color: #334155;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif;
}
.markdown-body :deep(h1) {
  font-size: 24px;
  font-weight: 700;
  padding-bottom: 8px;
  border-bottom: 2px solid #e2e8f0;
  margin-top: 16px;
  margin-bottom: 16px;
  color: #0f172a;
}
.markdown-body :deep(h2) {
  font-size: 20px;
  font-weight: 600;
  padding-bottom: 6px;
  border-bottom: 1px solid #e2e8f0;
  margin-top: 24px;
  margin-bottom: 14px;
  color: #1e293b;
}
.markdown-body :deep(h3) {
  font-size: 16px;
  font-weight: 600;
  margin-top: 20px;
  margin-bottom: 10px;
  color: #1e293b;
}
.markdown-body :deep(h4) {
  font-size: 14px;
  font-weight: 600;
  margin-top: 14px;
  margin-bottom: 8px;
  color: #334155;
}
.markdown-body :deep(p) {
  margin-bottom: 12px;
}
.markdown-body :deep(ul), .markdown-body :deep(ol) {
  padding-left: 24px;
  margin-bottom: 12px;
}
.markdown-body :deep(li) {
  margin-bottom: 4px;
}
.markdown-body :deep(table) {
  width: 100%;
  border-collapse: collapse;
  margin: 16px 0;
  font-size: 13px;
}
.markdown-body :deep(th), .markdown-body :deep(td) {
  border: 1px solid #cbd5e1;
  padding: 8px 12px;
  text-align: left;
}
.markdown-body :deep(th) {
  background-color: #f1f5f9;
  font-weight: 600;
  color: #1e293b;
}
.markdown-body :deep(tr:nth-child(even)) {
  background-color: #f8fafc;
}
.markdown-body :deep(blockquote) {
  border-left: 4px solid #3b82f6;
  background-color: #f8fafc;
  padding: 8px 16px;
  margin: 12px 0;
  color: #475569;
  border-radius: 0 4px 4px 0;
}
.markdown-body :deep(code) {
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  background-color: #f1f5f9;
  color: #0f172a;
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 12px;
}
.markdown-body :deep(pre) {
  background-color: #1e293b;
  color: #f8fafc;
  padding: 14px 18px;
  border-radius: 8px;
  overflow-x: auto;
  margin: 14px 0;
}
.markdown-body :deep(pre code) {
  background-color: transparent;
  color: inherit;
  padding: 0;
}
.markdown-body :deep(hr) {
  border: 0;
  border-top: 1px solid #e2e8f0;
  margin: 24px 0;
}
</style>
