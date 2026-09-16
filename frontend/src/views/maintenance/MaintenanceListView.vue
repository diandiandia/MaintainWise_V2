<template>
  <div class="maintenance-page">
    <el-card shadow="hover">
      <div class="toolbar">
        <div class="filters">
          <el-select v-model="filterStatus" placeholder="单据状态" clearable style="width: 170px;" @change="fetchRecords">
            <el-option label="技术员已上传锁定" value="SUBMITTED" />
            <el-option label="工程师已审核修正" value="REVISED_BY_ENGINEER" />
          </el-select>
          <el-select v-model="filterNormal" placeholder="检查结论" clearable style="width: 140px; margin-left: 10px;" @change="fetchRecords">
            <el-option label="全项正常" :value="true" />
            <el-option label="发现异常" :value="false" />
          </el-select>
        </div>
        <div>
          <el-button type="success" @click="openSubmitDrawer">+ 现场设备维护打卡</el-button>
        </div>
      </div>

      <el-table :data="records" v-loading="loading" style="width: 100%; margin-top: 15px;" stripe>
        <el-table-column prop="record_no" label="维护单号" width="200">
          <template #default="{ row }">
            <span class="mono-code">{{ row.record_no }}</span>
            <el-tag size="small" type="warning" effect="dark" style="margin-left: 6px;">🔒 锁定</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="equipment_name" label="目标设备" min-width="160">
          <template #default="{ row }">
            <strong>{{ row.equipment_name }}</strong>
          </template>
        </el-table-column>
        <el-table-column prop="technician_name" label="打卡技术员" width="130" />
        <el-table-column prop="submitted_at" label="提交时间" width="170" />
        <el-table-column label="结论" width="120" align="center">
          <template #default="{ row }">
            <el-tag :type="row.is_normal ? 'success' : 'danger'">
              {{ row.is_normal ? '全项合格' : '⚠️ 发现异常' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="160" align="center">
          <template #default="{ row }">
            <el-tag v-if="row.status === 'REVISED_BY_ENGINEER'" type="primary">
              已修正: {{ row.revised_by_name }}
            </el-tag>
            <el-tag v-else type="info">技术员已提交</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="180" align="center" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" size="small" @click="viewDetail(row)">查看明细</el-button>
            <el-button v-if="userStore.isEngineer" link type="warning" size="small" @click="openReviseDialog(row)">
              ✏️ 审核修正
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 现场维保打卡抽屉 (4级级联筛选 + 动态 SOP 项目创建) -->
    <el-drawer v-model="submitDrawerVisible" title="现场设备维护巡检打卡" size="560px">
      <el-form :model="submitForm" label-width="100px">
        <div class="section-title">📍 巡检设备精准定位 (厂-车间-系统-设备)：</div>
        
        <el-form-item label="所属工厂" required>
          <el-select v-model="submitForm.factory" placeholder="选择工厂" style="width: 100%;" @change="onFactoryChange">
            <el-option v-for="f in factoryOptions" :key="f" :label="f" :value="f" />
          </el-select>
        </el-form-item>

        <el-form-item label="所属车间" required>
          <el-select v-model="submitForm.department" placeholder="选择车间部门" style="width: 100%;" @change="onDepartmentChange">
            <el-option v-for="d in departmentOptions" :key="d" :label="d" :value="d" />
          </el-select>
        </el-form-item>

        <el-form-item label="所属系统" required>
          <el-select v-model="submitForm.system_name" placeholder="选择系统工段" style="width: 100%;" @change="onSystemChange">
            <el-option v-for="s in systemOptions" :key="s" :label="s" :value="s" />
          </el-select>
        </el-form-item>

        <el-form-item label="巡检设备" required>
          <el-select v-model="submitForm.equipment_id" placeholder="选择要打卡的具体设备" style="width: 100%;" @change="onEquipmentChange">
            <el-option v-for="eq in filteredEquipments" :key="eq.id" :label="`${eq.equipment_name} (${eq.equipment_code})`" :value="eq.id" />
          </el-select>
        </el-form-item>
        
        <div class="checklist-header">
          <span class="checklist-title">📋 检查项目标准核验 (SOP)：</span>
          <el-button type="primary" size="small" plain @click="addChecklistItem">+ 添加检查项目</el-button>
        </div>

        <div v-for="(item, idx) in submitForm.checklist_results" :key="idx" class="check-item-row">
          <div class="check-item-top">
            <div class="item-title-box">
              <span class="item-idx">{{ idx + 1 }}.</span>
              <el-input v-model="item.item" placeholder="检查项目名称" size="small" style="flex: 1;" />
            </div>
            <div class="item-ops">
              <el-radio-group v-model="item.status" size="small" @change="recalcNormal">
                <el-radio-button label="NORMAL">合格</el-radio-button>
                <el-radio-button label="ABNORMAL">异常</el-radio-button>
              </el-radio-group>
              <el-button v-if="submitForm.checklist_results.length > 1" link type="danger" size="small" @click="removeChecklistItem(idx)">✕</el-button>
            </div>
          </div>
          <div class="check-item-sub">
            <el-input v-model="item.standard" placeholder="核验标准要求 (如：脂量充足无积碳、温度<=70℃等)" size="small" />
          </div>
          <el-input v-if="item.status === 'ABNORMAL'" v-model="item.remark" placeholder="⚠️ 必填：请说明现场异常具体部位及特征" size="small" style="margin-top: 6px;" />
        </div>

        <el-form-item label="⏱️ 顺手记工时" style="margin-top: 18px;">
          <div style="display: flex; align-items: center; gap: 8px; width: 100%;">
            <el-input-number v-model="submitForm.log_runtime_hours" :min="0" :max="24" :precision="1" :step="0.5" style="width: 150px;" />
            <span style="font-size: 13px; color: #64748b;">小时 (选填：间歇开机设备可顺手填报今日开机时长)</span>
          </div>
        </el-form-item>

        <el-form-item label="全项结论" style="margin-top: 10px;">
          <el-tag :type="submitForm.is_normal ? 'success' : 'danger'" effect="dark">
            {{ submitForm.is_normal ? '🟢 全部检查合格' : '🔴 发现异常隐患 (提交将自动派发抢修工单并邮件告警)' }}
          </el-tag>
        </el-form-item>

        <el-form-item v-if="!submitForm.is_normal" label="异常总体描述">
          <el-input v-model="submitForm.anomaly_desc" type="textarea" :rows="2" placeholder="详细描述现场隐患情况，便于主管工程师研判派单" />
        </el-form-item>

        <div class="lock-tip">
          ℹ️ <strong>第一性原理防篡改提示</strong>：点击【上传提交并锁定】后，系统将立即将该打卡记录固化为只读，技术员无法自行篡改。若发现异常，系统将自动联锁生成现场维修单！
        </div>

        <div style="text-align: right; margin-top: 20px;">
          <el-button @click="submitDrawerVisible = false">取消</el-button>
          <el-button type="success" :loading="submitLoading" @click="handleSubmitRecord">上传提交并锁定</el-button>
        </div>
      </el-form>
    </el-drawer>

    <!-- 维保打卡明细弹窗 -->
    <el-dialog v-model="detailVisible" title="📋 现场维护单打卡详情" width="600px">
      <div v-if="selectedRecord" class="detail-content">
        <div class="detail-row">
          <span>维护单号：<code>{{ selectedRecord.record_no }}</code></span>
          <el-tag :type="selectedRecord.is_normal ? 'success' : 'danger'">
            {{ selectedRecord.is_normal ? '全项正常' : '发现异常' }}
          </el-tag>
        </div>
        <div class="detail-row">
          <span>目标设备：<strong>{{ selectedRecord.equipment_name }}</strong></span>
          <span>打卡技术员：{{ selectedRecord.technician_name }}</span>
        </div>
        <div class="detail-row">
          <span>打卡时间：{{ selectedRecord.submitted_at }}</span>
          <span v-if="selectedRecord.revised_by_name" style="color: #0284c7;">
            审核工程师：{{ selectedRecord.revised_by_name }} ({{ selectedRecord.revised_at }})
          </span>
        </div>
        <div v-if="selectedRecord.revision_reason" class="revision-box">
          <strong>工程师复核批注：</strong>{{ selectedRecord.revision_reason }}
        </div>
        <div v-if="selectedRecord.anomaly_desc" class="anomaly-box">
          <strong>异常情况说明：</strong>{{ selectedRecord.anomaly_desc }}
        </div>

        <div class="detail-checklist-title">检查项目核验清单 (SOP)：</div>
        <div v-for="(item, idx) in parsedChecklist" :key="idx" class="detail-check-item">
          <div style="display: flex; justify-content: space-between; align-items: center;">
            <span style="font-weight: bold;">{{ idx + 1 }}. {{ item.item }}</span>
            <el-tag size="small" :type="item.status === 'NORMAL' ? 'success' : 'danger'">
              {{ item.status === 'NORMAL' ? '合格' : '异常' }}
            </el-tag>
          </div>
          <div v-if="item.standard" style="color: #64748b; font-size: 12px; margin-top: 4px;">
            标准：{{ item.standard }}
          </div>
          <div v-if="item.remark" style="color: #dc2626; font-size: 12px; margin-top: 4px;">
            说明：{{ item.remark }}
          </div>
        </div>
      </div>
      <template #footer>
        <el-button @click="detailVisible = false">关闭</el-button>
      </template>
    </el-dialog>

    <!-- 工程师独占审核修正弹窗 -->
    <el-dialog v-model="reviseVisible" title="主管工程师审核修正 (强制留痕)" width="520px">
      <div class="revise-alert">
        ⚠️ 工程师独占权限：修正现场打卡记录必须如实填写修改原因与复核批注，供日后质量审计。
      </div>
      <el-form :model="reviseForm" label-width="110px" style="margin-top: 15px;">
        <el-form-item label="修改结论">
          <el-radio-group v-model="reviseForm.is_normal">
            <el-radio :label="true">合格正常</el-radio>
            <el-radio :label="false">仍有异常</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="复核批注" required>
          <el-input v-model="reviseForm.revision_reason" type="textarea" :rows="3" placeholder="必须填写修改原因 (如：现场抽检复测振动在合格范围内)" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="reviseVisible = false">取消</el-button>
        <el-button type="primary" :loading="reviseLoading" @click="submitRevise">提交审核修正</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, computed } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import apiClient from '../../api/client'
import { useUserStore } from '../../stores/user'

const route = useRoute()
const userStore = useUserStore()
const loading = ref(false)
const filterStatus = ref('')
const filterNormal = ref<boolean | ''>('')
const records = ref<any[]>([])
const equipments = ref<any[]>([])

// 4级级联数据源
const factoryOptions = computed(() => Array.from(new Set(equipments.value.map(e => e.factory))))
const departmentOptions = computed(() => {
  const list = equipments.value.filter(e => !submitForm.factory || e.factory === submitForm.factory)
  return Array.from(new Set(list.map(e => e.department)))
})
const systemOptions = computed(() => {
  const list = equipments.value.filter(e => 
    (!submitForm.factory || e.factory === submitForm.factory) &&
    (!submitForm.department || e.department === submitForm.department)
  )
  return Array.from(new Set(list.map(e => e.system_name)))
})
const filteredEquipments = computed(() => {
  return equipments.value.filter(e =>
    (!submitForm.factory || e.factory === submitForm.factory) &&
    (!submitForm.department || e.department === submitForm.department) &&
    (!submitForm.system_name || e.system_name === submitForm.system_name)
  )
})

function onFactoryChange() {
  submitForm.department = ''
  submitForm.system_name = ''
  submitForm.equipment_id = null
}
function onDepartmentChange() {
  submitForm.system_name = ''
  submitForm.equipment_id = null
}
function onSystemChange() {
  submitForm.equipment_id = null
}
function onEquipmentChange(eqId: number) {
  const dev = equipments.value.find(e => e.id === eqId)
  if (dev) {
    submitForm.factory = dev.factory
    submitForm.department = dev.department
    submitForm.system_name = dev.system_name
  }
}

// 打卡相关
const submitDrawerVisible = ref(false)
const submitLoading = ref(false)
const submitForm = reactive({
  factory: '',
  department: '',
  system_name: '',
  equipment_id: null as any,
  checklist_results: [
    { item: '主轴与轴承润滑情况', standard: '脂量充足无积碳变黑', status: 'NORMAL', remark: '' },
    { item: '传动机构皮带与螺栓紧固度', standard: '下陷量10-15mm无龟裂松动', status: 'NORMAL', remark: '' },
    { item: '运行噪音与表面温升', standard: '温度<=70℃，无金属刮擦异响', status: 'NORMAL', remark: '' },
    { item: '电气控制柜接线与指示灯', standard: '线排牢固无过热焦痕', status: 'NORMAL', remark: '' }
  ],
  is_normal: true,
  anomaly_desc: '',
  log_runtime_hours: 0
})

function addChecklistItem() {
  submitForm.checklist_results.push({
    item: `自定义检查项 ${submitForm.checklist_results.length + 1}`,
    standard: '符合原厂技术规程要求',
    status: 'NORMAL',
    remark: ''
  })
}

function removeChecklistItem(idx: number) {
  submitForm.checklist_results.splice(idx, 1)
  recalcNormal()
}

// 修正相关
const reviseVisible = ref(false)
const reviseLoading = ref(false)
const selectedRecordId = ref<number | null>(null)
const reviseForm = reactive({
  is_normal: true,
  revision_reason: ''
})

// 明细相关
const detailVisible = ref(false)
const selectedRecord = ref<any>(null)
const parsedChecklist = computed(() => {
  if (!selectedRecord.value?.checklist_result_json) return []
  try {
    return JSON.parse(selectedRecord.value.checklist_result_json)
  } catch (e) {
    return []
  }
})

async function fetchRecords() {
  loading.value = true
  try {
    const params: any = {}
    if (filterStatus.value) params.status = filterStatus.value
    if (filterNormal.value !== '') params.is_normal = filterNormal.value
    const res = await apiClient.get('/maintenance/records', { params })
    records.value = res.data
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

function openSubmitDrawer(prefillEqId?: number) {
  const targetId = prefillEqId || (route.query.equipment_id ? Number(route.query.equipment_id) : null)
  if (targetId) {
    const found = equipments.value.find(e => e.id === targetId)
    if (found) {
      submitForm.factory = found.factory
      submitForm.department = found.department
      submitForm.system_name = found.system_name
      submitForm.equipment_id = found.id
    }
  } else if (equipments.value.length > 0) {
    submitForm.factory = equipments.value[0].factory
    submitForm.department = equipments.value[0].department
    submitForm.system_name = equipments.value[0].system_name
    submitForm.equipment_id = equipments.value[0].id
  }
  submitForm.is_normal = true
  submitForm.anomaly_desc = ''
  submitDrawerVisible.value = true
}

function recalcNormal() {
  submitForm.is_normal = submitForm.checklist_results.every(i => i.status === 'NORMAL')
}

async function handleSubmitRecord() {
  if (!submitForm.equipment_id) {
    ElMessage.warning('请选择巡检设备')
    return
  }
  for (const item of submitForm.checklist_results) {
    if (!item.item || item.item.trim().length === 0) {
      ElMessage.warning('检查项目名称不能为空')
      return
    }
    if (item.status === 'ABNORMAL' && (!item.remark || item.remark.trim().length === 0)) {
      ElMessage.warning(`请填写【${item.item}】的异常具体说明`)
      return
    }
  }
  if (!submitForm.is_normal && (!submitForm.anomaly_desc || submitForm.anomaly_desc.trim().length === 0)) {
    ElMessage.warning('发现异常时必须填写异常总体描述')
    return
  }

  submitLoading.value = true
  try {
    await apiClient.post('/maintenance/records/submit', {
      equipment_id: submitForm.equipment_id,
      checklist_results: submitForm.checklist_results,
      is_normal: submitForm.is_normal,
      anomaly_desc: submitForm.anomaly_desc,
      log_runtime_hours: submitForm.log_runtime_hours || 0
    })
    ElMessage.success('打卡成功！记录已上传锁定防篡改，设备维保周期已自动复位')
    submitDrawerVisible.value = false
    fetchRecords()
  } catch (e) {
  } finally {
    submitLoading.value = false
  }
}

function openReviseDialog(row: any) {
  selectedRecordId.value = row.id
  reviseForm.is_normal = row.is_normal
  reviseForm.revision_reason = ''
  reviseVisible.value = true
}

async function submitRevise() {
  if (!reviseForm.revision_reason || reviseForm.revision_reason.trim().length < 2) {
    ElMessage.warning('必须如实填写修改原因与复核批注 (至少2字)')
    return
  }
  reviseLoading.value = true
  try {
    await apiClient.put(`/maintenance/records/${selectedRecordId.value}/revise`, reviseForm)
    ElMessage.success('审核修正留痕成功！')
    reviseVisible.value = false
    fetchRecords()
  } catch (e) {
  } finally {
    reviseLoading.value = false
  }
}

function viewDetail(row: any) {
  selectedRecord.value = row
  detailVisible.value = true
}

onMounted(async () => {
  await fetchEquipments()
  await fetchRecords()
  if (route.query.equipment_id) {
    openSubmitDrawer(Number(route.query.equipment_id))
  }
})
</script>

<style scoped>
.toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.mono-code {
  font-family: monospace;
  font-weight: 600;
  color: #0f172a;
}
.section-title {
  font-size: 14px;
  font-weight: bold;
  color: #1e293b;
  margin-bottom: 14px;
  border-left: 3px solid #3b82f6;
  padding-left: 8px;
}
.checklist-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin: 18px 0 10px 0;
  border-left: 3px solid #10b981;
  padding-left: 8px;
}
.checklist-title {
  font-weight: bold;
  font-size: 14px;
  color: #1e293b;
}
.check-item-row {
  background-color: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 6px;
  padding: 10px 12px;
  margin-bottom: 10px;
}
.check-item-top {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 10px;
}
.item-title-box {
  display: flex;
  align-items: center;
  gap: 6px;
  flex: 1;
}
.item-idx {
  font-weight: bold;
  color: #64748b;
  font-size: 13px;
}
.item-ops {
  display: flex;
  align-items: center;
  gap: 8px;
}
.check-item-sub {
  margin-top: 6px;
}
.lock-tip {
  background-color: #eff6ff;
  border: 1px solid #bfdbfe;
  padding: 10px;
  border-radius: 6px;
  font-size: 12px;
  color: #1e40af;
  margin-top: 15px;
  line-height: 1.6;
}
.revise-alert {
  background-color: #fff7ed;
  border: 1px solid #fed7aa;
  padding: 10px;
  border-radius: 6px;
  font-size: 12px;
  color: #9a3412;
}
.detail-content {
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.detail-row {
  display: flex;
  justify-content: space-between;
  font-size: 13px;
  color: #334155;
}
.revision-box {
  background: #f0f9ff;
  border: 1px solid #bae6fd;
  padding: 8px 12px;
  border-radius: 6px;
  font-size: 12px;
  color: #0369a1;
}
.anomaly-box {
  background: #fef2f2;
  border: 1px solid #fecaca;
  padding: 8px 12px;
  border-radius: 6px;
  font-size: 12px;
  color: #991b1b;
}
.detail-checklist-title {
  font-weight: bold;
  font-size: 13px;
  color: #0f172a;
  margin-top: 10px;
}
.detail-check-item {
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 6px;
  padding: 8px 10px;
}
</style>
