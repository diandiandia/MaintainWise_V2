<template>
  <div class="knowledge-page">
    <el-card shadow="hover">
      <div class="toolbar">
        <div class="search-inputs">
          <el-input
            v-model="search"
            placeholder="搜索排故案例关键字 (电机、变频器、轴承、异响...)"
            clearable
            style="width: 380px;"
            @keyup.enter="fetchCases"
            @clear="fetchCases"
          >
            <template #append>
              <el-button @click="fetchCases">检索</el-button>
            </template>
          </el-input>
          <el-checkbox v-model="onlyFeatured" label="仅看置顶金标典型案例" border style="margin-left: 15px;" @change="fetchCases" />
        </div>
        <el-button v-if="userStore.isEngineer" type="primary" @click="openCreateCase">+ 录入排故经验</el-button>
      </div>

      <div class="cases-grid" v-loading="loading">
        <div v-if="cases.length === 0" class="empty-cases">
          未检索到符合条件的排故案例
        </div>
        <el-card v-for="c in cases" :key="c.id" shadow="hover" class="case-card">
          <div class="case-header">
            <span class="case-title">
              <el-tag v-if="c.is_featured" type="warning" effect="dark" size="small">⭐ 置顶典型</el-tag>
              {{ c.title }}
            </span>
            <el-tag size="small" type="info">{{ c.equipment_category }}</el-tag>
          </div>
          <div class="phenomenon-block">
            <strong>故障现象：</strong>{{ c.phenomenon }}
          </div>
          <div class="cause-block">
            <strong>根本原因：</strong>{{ c.root_cause }}
          </div>
          <div class="steps-block">
            <strong>排查与解决步骤：</strong>
            <pre class="steps-pre">{{ c.solution_steps }}</pre>
          </div>
          <div class="case-footer">
            <span class="tags-txt">标签: {{ c.tags || '通用经验' }}</span>
            <el-button v-if="userStore.isEngineer" link type="danger" size="small" @click="handleDeleteCase(c)">删除案例</el-button>
          </div>
        </el-card>
      </div>
    </el-card>

    <!-- 新建案例对话框 -->
    <el-dialog v-model="createDialogVisible" title="录入排故经验案例" width="600px">
      <el-form :model="caseForm" label-width="100px">
        <el-form-item label="案例标题" required>
          <el-input v-model="caseForm.title" placeholder="如：变频主电机过流(OC)排查指南" />
        </el-form-item>
        <el-form-item label="设备大类">
          <el-input v-model="caseForm.equipment_category" placeholder="如：电机 / 泵阀 / 风机 / PLC" />
        </el-form-item>
        <el-form-item label="典型现象" required>
          <el-input v-model="caseForm.phenomenon" type="textarea" :rows="2" placeholder="详细描述常见故障现象" />
        </el-form-item>
        <el-form-item label="根本原因" required>
          <el-input v-model="caseForm.root_cause" type="textarea" :rows="2" placeholder="分析导致故障的核心机理" />
        </el-form-item>
        <el-form-item label="解决步骤" required>
          <el-input v-model="caseForm.solution_steps" type="textarea" :rows="4" placeholder="按编号提供清晰排障步骤" />
        </el-form-item>
        <el-form-item label="标签">
          <el-input v-model="caseForm.tags" placeholder="逗号分隔，如：变频器,跳闸,过流" />
        </el-form-item>
        <el-form-item label="置顶金标">
          <el-switch v-model="caseForm.is_featured" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="createDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="createLoading" @click="submitCreateCase">保 存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import apiClient from '../../api/client'
import { useUserStore } from '../../stores/user'

const userStore = useUserStore()
const loading = ref(false)
const search = ref('')
const onlyFeatured = ref(false)
const cases = ref<any[]>([])

const createDialogVisible = ref(false)
const createLoading = ref(false)
const caseForm = reactive({
  title: '',
  equipment_category: '通用',
  phenomenon: '',
  root_cause: '',
  solution_steps: '',
  tags: '',
  is_featured: false
})

async function fetchCases() {
  loading.value = true
  try {
    const params: any = {}
    if (search.value) params.search = search.value
    if (onlyFeatured.value) params.featured = true
    const res = await apiClient.get('/knowledge', { params })
    cases.value = res.data
  } catch (e) {
  } finally {
    loading.value = false
  }
}

function openCreateCase() {
  caseForm.title = ''
  caseForm.equipment_category = '通用'
  caseForm.phenomenon = ''
  caseForm.root_cause = ''
  caseForm.solution_steps = ''
  caseForm.tags = ''
  caseForm.is_featured = false
  createDialogVisible.value = true
}

async function submitCreateCase() {
  if (!caseForm.title || !caseForm.phenomenon || !caseForm.root_cause || !caseForm.solution_steps) {
    ElMessage.warning('请补全案例标题、现象、根因与解决步骤')
    return
  }
  createLoading.value = true
  try {
    await apiClient.post('/knowledge', caseForm)
    ElMessage.success('排故经验沉淀成功！')
    createDialogVisible.value = false
    fetchCases()
  } catch (e) {
  } finally {
    createLoading.value = false
  }
}

function handleDeleteCase(c: any) {
  ElMessageBox.confirm(`确定删除案例 [${c.title}] 吗？`, '提示', { type: 'warning' }).then(async () => {
    await apiClient.delete(`/knowledge/${c.id}`)
    ElMessage.success('案例已删除')
    fetchCases()
  }).catch(() => {})
}

onMounted(() => {
  fetchCases()
})
</script>

<style scoped>
.toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}
.search-inputs {
  display: flex;
  align-items: center;
}
.cases-grid {
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.empty-cases {
  text-align: center;
  color: #94a3b8;
  padding: 40px;
}
.case-card {
  border-radius: 8px;
}
.case-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
}
.case-title {
  font-size: 16px;
  font-weight: bold;
  color: #0f172a;
  display: flex;
  align-items: center;
  gap: 8px;
}
.phenomenon-block {
  font-size: 13px;
  color: #334155;
  margin-bottom: 6px;
}
.cause-block {
  background-color: #fef2f2;
  border-left: 3px solid #ef4444;
  padding: 6px 10px;
  font-size: 13px;
  color: #991b1b;
  margin-bottom: 8px;
  border-radius: 4px;
}
.steps-block {
  background-color: #f0fdf4;
  border-left: 3px solid #22c55e;
  padding: 8px 10px;
  border-radius: 4px;
}
.steps-pre {
  margin: 4px 0 0;
  font-family: inherit;
  white-space: pre-wrap;
  font-size: 13px;
  color: #14532d;
}
.case-footer {
  margin-top: 10px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 12px;
  color: #64748b;
}
</style>
