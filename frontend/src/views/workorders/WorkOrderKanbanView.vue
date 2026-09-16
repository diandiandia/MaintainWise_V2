<template>
  <div class="workorders-page">
    <div class="kanban-top">
      <div class="kanban-desc">
        <span class="main-title">⚡ 现场维护单流转看板</span>
        <span class="sub-txt">拒绝冗长审批流，责任到人，闭环留存根因传承后来人</span>
      </div>
      <el-button type="danger" size="large" @click="openReportModal">
        🚨 30秒极速突发报修
      </el-button>
    </div>

    <!-- 四态泳道 -->
    <div class="kanban-board" v-loading="loading">
      <!-- 泳道 1: 待派单 / 待抢单 -->
      <div class="kanban-col pending-col">
        <div class="col-header">
          <span>🔴 待派单 / 待抢单 ({{ pendingList.length }})</span>
        </div>
        <div class="col-body">
          <el-card v-for="wo in pendingList" :key="wo.id" class="wo-card" shadow="hover">
            <div class="wo-header">
              <span class="wo-no">{{ wo.order_no }}</span>
              <el-tag size="small" :type="getUrgencyTag(wo.urgency)">{{ wo.urgency }}</el-tag>
            </div>
            <div class="wo-title" @click="openDetailModal(wo)">{{ wo.title }}</div>
            <div class="wo-eq">设备：<strong>{{ wo.equipment_name }}</strong></div>
            <div class="wo-meta">报修人: {{ wo.reporter_name }} | {{ wo.reported_at }}</div>
            <div class="wo-actions">
              <el-button size="small" link type="primary" @click="openEditModal(wo)">✏️ 编辑</el-button>
              <el-button size="small" link type="info" @click="openDetailModal(wo)">🔍 详情</el-button>
              <el-button size="small" type="primary" @click="handleClaim(wo)">
                {{ userStore.isEngineer ? '派发 / 接单' : '⚡ 自主抢单' }}
              </el-button>
            </div>
          </el-card>
        </div>
      </div>

      <!-- 泳道 2: 排故抢修中 -->
      <div class="kanban-col inprogress-col">
        <div class="col-header">
          <span>🔵 正在排故抢修 ({{ inProgressList.length }})</span>
        </div>
        <div class="col-body">
          <el-card v-for="wo in inProgressList" :key="wo.id" class="wo-card" shadow="hover">
            <div class="wo-header">
              <span class="wo-no">{{ wo.order_no }}</span>
              <el-tag size="small" :type="getUrgencyTag(wo.urgency)">{{ wo.urgency }}</el-tag>
            </div>
            <div class="wo-title" @click="openDetailModal(wo)">{{ wo.title }}</div>
            <div class="wo-eq">设备：<strong>{{ wo.equipment_name }}</strong></div>
            <div class="wo-assignee">承修责任人：<el-tag size="small" type="primary">{{ wo.assignee_name || '抢修中' }}</el-tag></div>
            <div class="wo-actions">
              <el-button size="small" link type="primary" @click="openEditModal(wo)">✏️ 编辑</el-button>
              <el-button size="small" link type="info" @click="openDetailModal(wo)">🔍 详情</el-button>
              <el-button size="small" type="success" @click="openResolveModal(wo)">
                🛠️ 完工填报复盘
              </el-button>
            </div>
          </el-card>
        </div>
      </div>

      <!-- 泳道 3: 完工待验收 -->
      <div class="kanban-col confirm-col">
        <div class="col-header">
          <span>🟡 完工待验收 ({{ confirmList.length }})</span>
        </div>
        <div class="col-body">
          <el-card v-for="wo in confirmList" :key="wo.id" class="wo-card" shadow="hover">
            <div class="wo-header">
              <span class="wo-no">{{ wo.order_no }}</span>
              <el-tag size="small" type="warning">待试车核验</el-tag>
            </div>
            <div class="wo-title" @click="openDetailModal(wo)" style="cursor: pointer;">
              {{ wo.title }} <el-tag size="small" type="info" effect="plain">点击看详情</el-tag>
            </div>
            <div class="wo-eq">设备：<strong>{{ wo.equipment_name }}</strong></div>
            <div class="wo-cause-preview" @click="openDetailModal(wo)" style="cursor: pointer;">
              <strong>根因：</strong>{{ wo.root_cause }}
            </div>
            <div class="wo-actions">
              <el-button size="small" link type="primary" @click="openEditModal(wo)">✏️ 修改</el-button>
              <el-button size="small" link type="info" @click="openDetailModal(wo)">🔍 详细信息</el-button>
              <el-button v-if="userStore.isEngineer" size="small" type="warning" @click="handleConfirmClose(wo)">
                ✅ 试车复核结案
              </el-button>
            </div>
          </el-card>
        </div>
      </div>

      <!-- 泳道 4: 已闭环归档 -->
      <div class="kanban-col closed-col">
        <div class="col-header">
          <span>🟢 已闭环归档 ({{ closedList.length }})</span>
        </div>
        <div class="col-body">
          <el-card v-for="wo in closedList" :key="wo.id" class="wo-card" shadow="hover">
            <div class="wo-header">
              <span class="wo-no">{{ wo.order_no }}</span>
              <el-tag size="small" type="success">已结案</el-tag>
            </div>
            <div class="wo-title" @click="openDetailModal(wo)" style="cursor: pointer;">{{ wo.title }}</div>
            <div class="wo-eq">设备：<strong>{{ wo.equipment_name }}</strong></div>
            <div class="wo-cause-preview" @click="openDetailModal(wo)" style="cursor: pointer;">
              <strong>根因：</strong>{{ wo.root_cause }}
            </div>
            <div class="wo-actions">
              <el-button size="small" link type="info" @click="openDetailModal(wo)">🔍 查看详情</el-button>
              <el-button v-if="userStore.isEngineer && !wo.is_featured_case" size="small" type="warning" plain @click="extractKnowledge(wo)">
                ★ 沉淀为知识库案例
              </el-button>
              <el-tag v-else-if="wo.is_featured_case" size="small" type="warning" effect="dark">
                ⭐ 已沉淀为知识库案例
              </el-tag>
            </div>
          </el-card>
        </div>
      </div>
    </div>

    <!-- 30 秒极速报修弹窗 -->
    <el-dialog v-model="reportModalVisible" title="🚨 30 秒极速突发故障报修" width="600px">
      <el-form :model="reportForm" :rules="reportRules" ref="reportFormRef" label-width="100px">
        <el-form-item label="故障设备" prop="equipment_id">
          <el-select v-model="reportForm.equipment_id" placeholder="选择或搜索故障设备" filterable style="width: 100%;">
            <el-option v-for="eq in equipments" :key="eq.id" :label="`${eq.equipment_name} (${eq.factory}-${eq.department})`" :value="eq.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="故障简述" prop="title">
          <el-input v-model="reportForm.title" placeholder="如：主轴承发烫震动过大 (输入即时检索排查参考)" @input="handleFaultTitleInput" />
        </el-form-item>
        <el-form-item label="紧急程度">
          <el-radio-group v-model="reportForm.urgency">
            <el-radio label="NORMAL">普通 (不影响主线)</el-radio>
            <el-radio label="MAJOR">严重 (降速运行)</el-radio>
            <el-radio label="CRITICAL">紧急 (停机抢修)</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="现象详述">
          <el-input v-model="reportForm.phenomenon" type="textarea" :rows="2" placeholder="选填：异响特征/烟雾/报警代码等" />
        </el-form-item>

        <!-- 实时智能排故联想参考卡片 -->
        <div v-if="recommendedCases.length > 0" class="rec-box">
          <div class="rec-title">💡 后来人智能排查参考 (根据输入文字即时匹配)：</div>
          <div v-for="c in recommendedCases" :key="c.id" class="rec-item">
            <div class="rec-item-title">📌 {{ c.title }}</div>
            <div class="rec-item-cause">可能根因：{{ c.root_cause }}</div>
            <div class="rec-item-step">建议对策：{{ c.solution_steps }}</div>
          </div>
        </div>
      </el-form>
      <template #footer>
        <el-button @click="reportModalVisible = false">取消</el-button>
        <el-button type="danger" :loading="reportLoading" @click="submitReport">立即提交抢修</el-button>
      </template>
    </el-dialog>

    <!-- 工单修改/纠错弹窗 -->
    <el-dialog v-model="editModalVisible" title="✏️ 修改/纠错现场维护单信息" width="580px">
      <el-form :model="editForm" label-width="100px">
        <el-form-item label="故障简述" required>
          <el-input v-model="editForm.title" placeholder="修改故障标题" />
        </el-form-item>
        <el-form-item label="紧急程度">
          <el-radio-group v-model="editForm.urgency">
            <el-radio label="NORMAL">普通</el-radio>
            <el-radio label="MAJOR">严重</el-radio>
            <el-radio label="CRITICAL">紧急</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="故障现象">
          <el-input v-model="editForm.phenomenon" type="textarea" :rows="2" placeholder="修改故障现象详述" />
        </el-form-item>
        <el-form-item v-if="editForm.root_cause !== undefined" label="故障根因">
          <el-input v-model="editForm.root_cause" type="textarea" :rows="2" placeholder="修正根本原因分析" />
        </el-form-item>
        <el-form-item v-if="editForm.solution_steps !== undefined" label="排除步骤">
          <el-input v-model="editForm.solution_steps" type="textarea" :rows="3" placeholder="修正排除步骤" />
        </el-form-item>
        <el-form-item v-if="editForm.spare_parts !== undefined" label="更换备件">
          <el-input v-model="editForm.spare_parts" placeholder="更换备件型号数量" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="editModalVisible = false">取消</el-button>
        <el-button type="primary" :loading="editLoading" @click="submitEditWorkOrder">保存修改</el-button>
      </template>
    </el-dialog>

    <!-- 完工待验收及各态工单详细信息弹窗 (满足用户：完工待验收要可以点击看到详细信息) -->
    <el-dialog v-model="detailModalVisible" title="🔍 现场维护单全流程履历详情" width="680px">
      <div v-if="selectedWo" class="detail-container">
        <div class="detail-header-row">
          <div>
            <span class="detail-no">{{ selectedWo.order_no }}</span>
            <el-tag :type="getUrgencyTag(selectedWo.urgency)" style="margin-left: 8px;">{{ selectedWo.urgency }}</el-tag>
            <el-tag :type="getStatusTagType(selectedWo.status)" style="margin-left: 6px;">{{ getStatusText(selectedWo.status) }}</el-tag>
          </div>
          <span class="detail-time">报修时间：{{ selectedWo.reported_at }}</span>
        </div>

        <div class="detail-section">
          <div class="d-title">📌 故障基本情况</div>
          <div class="d-grid">
            <div><strong>故障设备：</strong>{{ selectedWo.equipment_name }}</div>
            <div><strong>报修人员：</strong>{{ selectedWo.reporter_name }}</div>
            <div><strong>故障标题：</strong>{{ selectedWo.title }}</div>
            <div><strong>故障现象：</strong>{{ selectedWo.phenomenon || '现场未额外补充' }}</div>
          </div>
          <div v-if="selectedWo.fault_photo_path" style="margin-top: 8px;">
            <strong>现场故障照片：</strong>
            <div style="margin-top: 4px;">
              <el-image :src="selectedWo.fault_photo_path" style="width: 120px; height: 120px; border-radius: 4px;" fit="cover" />
            </div>
          </div>
        </div>

        <div class="detail-section" v-if="selectedWo.status !== 'PENDING'">
          <div class="d-title">🛠️ 抢修实施与复盘成果</div>
          <div class="d-grid">
            <div><strong>承修技术员：</strong>{{ selectedWo.assignee_name || '抢修中' }}</div>
            <div><strong>接单时间：</strong>{{ selectedWo.claimed_at || '-' }}</div>
            <div><strong>维修耗时：</strong>{{ selectedWo.repair_duration_minutes }} 分钟</div>
            <div><strong>更换备件：</strong>{{ selectedWo.spare_parts || '无备件更换 / 纯调试' }}</div>
          </div>
          <div class="cause-box">
            <strong>真实根本原因 (留给后来人)：</strong>
            <p>{{ selectedWo.root_cause || '排故中尚未填报' }}</p>
          </div>
          <div class="steps-box">
            <strong>详细排除步骤 (经验沉淀)：</strong>
            <pre class="steps-pre">{{ selectedWo.solution_steps || '排故中尚未填报' }}</pre>
          </div>
          <div v-if="selectedWo.repair_photos" style="margin-top: 10px;">
            <strong>完工修复照片 (试车达标依据)：</strong>
            <div style="display: flex; gap: 8px; margin-top: 6px; flex-wrap: wrap;">
              <span v-for="(p, pIdx) in getPhotoList(selectedWo.repair_photos)" :key="pIdx">
                <el-image :src="p" style="width: 120px; height: 120px; border-radius: 4px; border: 1px solid #e2e8f0;" fit="cover" />
              </span>
            </div>
          </div>
        </div>
      </div>
      <template #footer>
        <el-button @click="detailModalVisible = false">关闭</el-button>
        <el-button v-if="userStore.isEngineer && selectedWo?.status === 'PENDING_CONFIRM'" type="warning" @click="handleConfirmClose(selectedWo)">
          ✅ 主管工程师现场试车验收结案
        </el-button>
        <el-button v-if="userStore.isEngineer && selectedWo?.status === 'CLOSED' && !selectedWo?.is_featured_case" type="warning" plain @click="extractKnowledge(selectedWo)">
          ★ 沉淀为知识库案例
        </el-button>
      </template>
    </el-dialog>

    <!-- 完工复盘填报弹窗 (强制根因与排除步骤 + 上传修复照片) -->
    <el-dialog v-model="resolveModalVisible" title="🛠️ 现场排故完工复盘 (后来人经验闭环)" width="640px">
      <div class="resolve-tip">
        <strong>第一性原理质量铁律：</strong>严禁形式主义填报“已修复”！必须如实记录真实根本原因与排除步骤，为深夜值班人员和后来新员工留下宝贵资产。
      </div>
      <el-form :model="resolveForm" ref="resolveFormRef" label-width="110px" style="margin-top: 15px;">
        <el-form-item label="故障根本原因" required>
          <el-input v-model="resolveForm.root_cause" type="textarea" :rows="2" placeholder="如：润滑油路被异物堵塞造成轴瓦干摩擦损坏 (强制必填)" />
        </el-form-item>
        <el-form-item label="详细排除步骤" required>
          <el-input v-model="resolveForm.solution_steps" type="textarea" :rows="4" placeholder="详细记录：1.拆卸顺序；2.测量参数；3.清洗更换要点；4.调试复位步骤 (强制必填)" />
        </el-form-item>
        <el-form-item label="更换备件">
          <el-input v-model="resolveForm.spare_parts" placeholder="选填，如：NSK-6208 轴承 x 2, 密封圈 x 1" />
        </el-form-item>
        <el-form-item label="维修耗时(分)">
          <el-input-number v-model="resolveForm.repair_duration_minutes" :min="1" />
        </el-form-item>
        <el-form-item label="完工修复照片">
          <el-input v-model="resolveForm.repair_photos" placeholder="输入修复后照片路径或URL (选填，多张用逗号分隔)" />
          <div style="font-size: 11px; color: #94a3b8; margin-top: 4px;">
            示例: /uploads/repairs/motor_fixed.jpg, 可展示修好后的设备运转正常状态
          </div>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="resolveModalVisible = false">取消</el-button>
        <el-button type="primary" :loading="resolveLoading" @click="submitResolve">提交复盘报告</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import apiClient from '../../api/client'
import { useUserStore } from '../../stores/user'

const route = useRoute()
const userStore = useUserStore()
const loading = ref(false)
const workOrders = ref<any[]>([])
const equipments = ref<any[]>([])

// 四态计算属性
const pendingList = computed(() => workOrders.value.filter(w => w.status === 'PENDING'))
const inProgressList = computed(() => workOrders.value.filter(w => w.status === 'IN_PROGRESS'))
const confirmList = computed(() => workOrders.value.filter(w => w.status === 'PENDING_CONFIRM'))
const closedList = computed(() => workOrders.value.filter(w => w.status === 'CLOSED'))

// 报修相关
const reportModalVisible = ref(false)
const reportLoading = ref(false)
const reportFormRef = ref()
const reportForm = reactive({
  equipment_id: null as any,
  title: '',
  urgency: 'NORMAL',
  phenomenon: ''
})
const reportRules = {
  equipment_id: [{ required: true, message: '请选择故障设备', trigger: 'blur' }],
  title: [{ required: true, message: '请输入故障简述', trigger: 'blur' }]
}
const recommendedCases = ref<any[]>([])
let debounceTimer: any = null

// 修改工单
const editModalVisible = ref(false)
const editLoading = ref(false)
const editTargetId = ref<number | null>(null)
const editForm = reactive<any>({
  title: '',
  urgency: 'NORMAL',
  phenomenon: '',
  root_cause: '',
  solution_steps: '',
  spare_parts: ''
})

function openEditModal(wo: any) {
  editTargetId.value = wo.id
  editForm.title = wo.title
  editForm.urgency = wo.urgency
  editForm.phenomenon = wo.phenomenon || ''
  editForm.root_cause = wo.root_cause || ''
  editForm.solution_steps = wo.solution_steps || ''
  editForm.spare_parts = wo.spare_parts || ''
  editModalVisible.value = true
}

async function submitEditWorkOrder() {
  if (!editForm.title || editForm.title.trim().length === 0) {
    ElMessage.warning('请输入故障标题')
    return
  }
  editLoading.value = true
  try {
    await apiClient.put(`/work-orders/${editTargetId.value}`, editForm)
    ElMessage.success('工单信息修改成功！')
    editModalVisible.value = false
    fetchWorkOrders()
  } catch (e) {
  } finally {
    editLoading.value = false
  }
}

// 详细信息弹窗 (完工待验收等点击打开)
const detailModalVisible = ref(false)
const selectedWo = ref<any>(null)

function openDetailModal(wo: any) {
  selectedWo.value = wo
  detailModalVisible.value = true
}

function getPhotoList(str: string) {
  if (!str) return []
  return str.split(',').map(s => s.trim()).filter(Boolean)
}

function getStatusTagType(status: string) {
  if (status === 'PENDING') return 'danger'
  if (status === 'IN_PROGRESS') return 'primary'
  if (status === 'PENDING_CONFIRM') return 'warning'
  return 'success'
}

function getStatusText(status: string) {
  if (status === 'PENDING') return '待派单/待抢单'
  if (status === 'IN_PROGRESS') return '排故抢修中'
  if (status === 'PENDING_CONFIRM') return '完工待验收'
  return '已闭环结案'
}

// 完工复盘相关
const resolveModalVisible = ref(false)
const resolveLoading = ref(false)
const selectedWoId = ref<number | null>(null)
const resolveForm = reactive({
  root_cause: '',
  solution_steps: '',
  spare_parts: '',
  repair_duration_minutes: 30,
  repair_photos: ''
})

async function fetchWorkOrders() {
  loading.value = true
  try {
    const res = await apiClient.get('/work-orders')
    workOrders.value = res.data
  } catch (e) {
  } finally {
    loading.value = false
  }
}

async function fetchEquipments() {
  try {
    const res = await apiClient.get('/equipments')
    equipments.value = res.data
  } catch (e) {
  }
}

function openReportModal(prefillEqId?: number) {
  const targetId = prefillEqId || (route.query.equipment_id ? Number(route.query.equipment_id) : null)
  if (targetId) {
    reportForm.equipment_id = targetId
  } else if (equipments.value.length > 0) {
    reportForm.equipment_id = equipments.value[0].id
  }
  reportForm.title = ''
  reportForm.phenomenon = ''
  reportForm.urgency = 'NORMAL'
  recommendedCases.value = []
  reportModalVisible.value = true
}

function handleFaultTitleInput() {
  clearTimeout(debounceTimer)
  if (!reportForm.title || reportForm.title.trim().length < 2) {
    recommendedCases.value = []
    return
  }
  debounceTimer = setTimeout(async () => {
    try {
      const res = await apiClient.get('/knowledge/recommend', {
        params: { query: reportForm.title.trim() }
      })
      recommendedCases.value = res.data
    } catch (e) {
    }
  }, 300)
}

async function submitReport() {
  if (!reportFormRef.value) return
  await reportFormRef.value.validate(async (valid: boolean) => {
    if (!valid) return
    reportLoading.value = true
    try {
      await apiClient.post('/work-orders', reportForm)
      ElMessage.success('报修成功！已通知车间技术人员')
      reportModalVisible.value = false
      fetchWorkOrders()
    } catch (e) {
    } finally {
      reportLoading.value = false
    }
  })
}

async function handleClaim(wo: any) {
  try {
    await apiClient.put(`/work-orders/${wo.id}/dispatch`, {})
    ElMessage.success('接单成功！已进入排故抢修中')
    fetchWorkOrders()
  } catch (e) {
  }
}

function openResolveModal(wo: any) {
  selectedWoId.value = wo.id
  resolveForm.root_cause = ''
  resolveForm.solution_steps = ''
  resolveForm.spare_parts = ''
  resolveForm.repair_duration_minutes = 30
  resolveForm.repair_photos = ''
  resolveModalVisible.value = true
}

async function submitResolve() {
  if (!resolveForm.root_cause || resolveForm.root_cause.trim().length < 2) {
    ElMessage.warning('必须如实填写故障根本原因 (至少2字)')
    return
  }
  if (!resolveForm.solution_steps || resolveForm.solution_steps.trim().length < 2) {
    ElMessage.warning('必须填写详细排除步骤 (至少2字)')
    return
  }
  resolveLoading.value = true
  try {
    await apiClient.put(`/work-orders/${selectedWoId.value}/resolve`, resolveForm)
    ElMessage.success('复盘提交成功！已流转至待主管工程师试车验收')
    resolveModalVisible.value = false
    fetchWorkOrders()
  } catch (e) {
  } finally {
    resolveLoading.value = false
  }
}

function handleConfirmClose(wo: any) {
  ElMessageBox.confirm(`主管工程师试车确认：设备 [${wo.equipment_name}] 试运行平稳、无异响，确认验收结案吗？`, '复核验收', {
    type: 'success'
  }).then(async () => {
    await apiClient.put(`/work-orders/${wo.id}/confirm`)
    ElMessage.success('工单已闭环结案！设备状态已自动恢复正常运行')
    if (detailModalVisible.value && selectedWo.value?.id === wo.id) {
      detailModalVisible.value = false
    }
    fetchWorkOrders()
  }).catch(() => {})
}

async function extractKnowledge(wo: any) {
  try {
    const res = await apiClient.post(`/work-orders/${wo.id}/to-knowledge`)
    ElMessage.success(res.data.message)
    if (selectedWo.value && selectedWo.value.id === wo.id) {
      selectedWo.value.is_featured_case = true
    }
    fetchWorkOrders()
  } catch (e) {
  }
}

function getUrgencyTag(urgency: string) {
  if (urgency === 'CRITICAL') return 'danger'
  if (urgency === 'MAJOR') return 'warning'
  return 'info'
}

onMounted(async () => {
  await fetchEquipments()
  await fetchWorkOrders()
  if (route.query.equipment_id) {
    openReportModal(Number(route.query.equipment_id))
  }
})
</script>

<style scoped>
.kanban-top {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}
.main-title {
  font-size: 18px;
  font-weight: bold;
  color: #0f172a;
  display: block;
}
.sub-txt {
  font-size: 13px;
  color: #64748b;
  margin-top: 4px;
}
.kanban-board {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
  min-height: 600px;
}
.kanban-col {
  background-color: #f1f5f9;
  border-radius: 8px;
  display: flex;
  flex-direction: column;
  border-top: 4px solid #cbd5e1;
}
.kanban-col.pending-col { border-top-color: #ef4444; }
.kanban-col.inprogress-col { border-top-color: #3b82f6; }
.kanban-col.confirm-col { border-top-color: #f59e0b; }
.kanban-col.closed-col { border-top-color: #10b981; }

.col-header {
  padding: 14px 16px;
  font-weight: bold;
  font-size: 14px;
  color: #1e293b;
  border-bottom: 1px solid #e2e8f0;
}
.col-body {
  padding: 12px;
  flex: 1;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.wo-card {
  border-radius: 8px;
}
.wo-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}
.wo-no {
  font-family: monospace;
  font-size: 12px;
  color: #64748b;
}
.wo-title {
  font-weight: bold;
  font-size: 15px;
  color: #0f172a;
  margin-bottom: 6px;
  cursor: pointer;
}
.wo-title:hover {
  color: #0284c7;
}
.wo-eq {
  font-size: 13px;
  color: #334155;
  margin-bottom: 6px;
}
.wo-meta, .wo-assignee {
  font-size: 12px;
  color: #64748b;
  margin-bottom: 10px;
}
.wo-cause-preview {
  background-color: #fef2f2;
  font-size: 12px;
  color: #991b1b;
  padding: 8px;
  border-radius: 4px;
  margin-bottom: 10px;
}
.wo-actions {
  text-align: right;
  display: flex;
  justify-content: flex-end;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
}
.rec-box {
  background-color: #f0fdf4;
  border: 1px solid #bbf7d0;
  padding: 12px;
  border-radius: 6px;
  margin-top: 15px;
}
.rec-title {
  font-size: 13px;
  font-weight: bold;
  color: #166534;
  margin-bottom: 8px;
}
.rec-item {
  background: #ffffff;
  padding: 8px;
  border-radius: 4px;
  margin-bottom: 6px;
  font-size: 12px;
}
.rec-item-title {
  font-weight: bold;
  color: #1e293b;
}
.rec-item-cause {
  color: #b91c1c;
  margin-top: 2px;
}
.rec-item-step {
  color: #15803d;
  margin-top: 2px;
}
.resolve-tip {
  background-color: #eff6ff;
  border: 1px solid #bfdbfe;
  padding: 10px;
  border-radius: 6px;
  font-size: 12px;
  color: #1e40af;
}

/* Detail dialog */
.detail-container {
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.detail-header-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-bottom: 1px solid #e2e8f0;
  padding-bottom: 10px;
}
.detail-no {
  font-family: monospace;
  font-size: 16px;
  font-weight: bold;
  color: #0f172a;
}
.detail-time {
  font-size: 12px;
  color: #64748b;
}
.detail-section {
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  padding: 14px;
}
.d-title {
  font-weight: bold;
  font-size: 14px;
  color: #1e293b;
  margin-bottom: 10px;
  border-left: 3px solid #3b82f6;
  padding-left: 6px;
}
.d-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 8px;
  font-size: 13px;
  color: #334155;
}
.cause-box {
  background: #fef2f2;
  border: 1px solid #fecaca;
  padding: 10px;
  border-radius: 6px;
  margin-top: 10px;
  font-size: 13px;
  color: #991b1b;
}
.steps-box {
  background: #f0fdf4;
  border: 1px solid #bbf7d0;
  padding: 10px;
  border-radius: 6px;
  margin-top: 10px;
  font-size: 13px;
  color: #166534;
}
.steps-pre {
  white-space: pre-wrap;
  font-family: inherit;
  margin-top: 6px;
  line-height: 1.5;
}
</style>
