<template>
  <div class="equipments-page">
    <el-row :gutter="16">
      <!-- 左侧三级层级树 -->
      <el-col :span="6">
        <el-card shadow="hover" class="tree-card">
          <template #header>
            <div class="tree-header">
              <span>🏭 工厂-部门-系统架构</span>
              <el-button link type="primary" size="small" @click="fetchHierarchyTree">刷新</el-button>
            </div>
          </template>
          <div class="tree-tips">点击节点钻取设备，悬停可修改更名</div>
          <el-tree
            :data="hierarchyTree"
            node-key="name"
            default-expand-all
            :expand-on-click-node="false"
            @node-click="handleNodeClick"
          >
            <template #default="{ node, data }">
              <div class="tree-node">
                <span class="node-label">{{ data.label }}</span>
                <span class="node-actions" v-if="userStore.isEngineer">
                  <el-button link type="primary" size="small" @click.stop="openRenameDialog(data)">✏️</el-button>
                  <el-button link type="danger" size="small" @click.stop="openDeleteHierarchy(data)">🗑️</el-button>
                </span>
              </div>
            </template>
          </el-tree>
        </el-card>
      </el-col>

      <!-- 右侧设备列表与操作区 -->
      <el-col :span="18">
        <el-card shadow="hover">
          <!-- 检索与工具栏 -->
          <div class="toolbar">
            <div class="search-box">
              <el-input
                v-model="searchQuery"
                placeholder="搜索设备名称、规格型号或设备编号..."
                clearable
                style="width: 320px;"
                @keyup.enter="fetchEquipments"
                @clear="fetchEquipments"
              >
                <template #append>
                  <el-button @click="fetchEquipments">搜索</el-button>
                </template>
              </el-input>
              <el-tag v-if="activeFilter" closable @close="clearFilter" style="margin-left: 10px;">
                筛选: {{ activeFilter }}
              </el-tag>
            </div>

            <div class="btn-group">
              <el-radio-group v-model="viewMode" size="small" style="margin-right: 12px;">
                <el-radio-button label="table">表格视图</el-radio-button>
                <el-radio-button label="card">看板大卡片</el-radio-button>
              </el-radio-group>
              <el-button v-if="userStore.isEngineer" type="primary" @click="openCreateDialog">
                + 录入新设备
              </el-button>
            </div>
          </div>

          <!-- 列表模式 -->
          <el-table v-if="viewMode === 'table'" :data="equipments" v-loading="loading" style="width: 100%; margin-top: 15px;" stripe>
            <el-table-column prop="equipment_code" label="设备编号" min-width="140">
              <template #default="{ row }">
                <el-tag size="small" effect="plain" type="info">{{ row.equipment_code }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="equipment_name" label="设备名称" min-width="150">
              <template #default="{ row }">
                <span class="highlight-name">{{ row.equipment_name }}</span>
              </template>
            </el-table-column>
            <el-table-column prop="model_spec" label="规格型号" min-width="120" />
            <el-table-column label="归属层级" min-width="170">
              <template #default="{ row }">
                <span style="font-size: 13px; color: #475569;">{{ row.factory }} / {{ row.department }} / {{ row.system_name }}</span>
              </template>
            </el-table-column>
            <el-table-column label="工时与维护倒计时" min-width="230">
              <template #default="{ row }">
                <div class="countdown-cell">
                  <div style="display: flex; align-items: center; justify-content: space-between;">
                    <div>
                      <el-tag size="small" :type="row.running_mode === 'INTERMITTENT' ? 'warning' : 'info'" effect="plain">
                        {{ row.running_mode === 'INTERMITTENT' ? '间歇作业' : '24h常开' }}
                      </el-tag>
                      <span style="font-size: 13px; font-weight: bold; margin-left: 6px;">{{ row.total_running_hours }} h</span>
                    </div>
                    <el-button link type="primary" size="small" @click="openLogHours(row)">[⏱️ 记工时/抄表]</el-button>
                  </div>
                  <div style="margin-top: 5px; display: flex; align-items: center; gap: 6px; flex-wrap: wrap;">
                    <el-tag size="small" :type="getCountdownTagType(row.countdown_status)">
                      {{ getCountdownLabel(row) }}
                    </el-tag>
                    <span v-if="row.estimated_days_left !== null && row.countdown_status !== 'OVERDUE'" style="font-size: 12px; color: #d97706; font-weight: 500;">
                      (约剩 {{ row.estimated_days_left }} 天)
                    </span>
                    <span style="font-size: 12px; color: #94a3b8;">周期: {{ row.maintenance_interval_hours }}h</span>
                  </div>
                </div>
              </template>
            </el-table-column>
            <el-table-column prop="status" label="状态" width="100" align="center">
              <template #default="{ row }">
                <el-tag :type="getStatusTag(row.status)">{{ getStatusText(row.status) }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column label="快捷操作与病历" width="310" align="center" fixed="right">
              <template #default="{ row }">
                <el-button size="small" type="success" plain @click="quickMaintenance(row)">+ 快速维保</el-button>
                <el-button size="small" type="danger" plain @click="quickRepair(row)">+ 快速报修</el-button>
                <el-button link type="primary" size="small" @click="openTimeline(row)">📋 病历</el-button>
                <el-button link type="info" size="small" @click="showQrCode(row)">码</el-button>
                <el-button v-if="userStore.isEngineer" link type="danger" size="small" @click="handleDelete(row)">删</el-button>
              </template>
            </el-table-column>
          </el-table>

          <!-- 看板大卡片模式 (现场工业触控屏友好) -->
          <div v-else class="cards-grid" v-loading="loading">
            <el-card v-for="eq in equipments" :key="eq.id" shadow="hover" class="eq-card">
              <div class="eq-card-header">
                <div>
                  <span class="eq-title">{{ eq.equipment_name }}</span>
                  <el-tag size="small" effect="plain" type="info" style="margin-left: 6px;">{{ eq.equipment_code }}</el-tag>
                </div>
                <el-tag size="small" :type="getStatusTag(eq.status)">{{ getStatusText(eq.status) }}</el-tag>
              </div>
              <div class="eq-spec">规格: {{ eq.model_spec }} | 数量: {{ eq.quantity }}</div>
              <div class="eq-hierarchy">{{ eq.factory }} - {{ eq.department }} - {{ eq.system_name }}</div>
              <div class="eq-countdown-block">
                <div class="countdown-row">
                  <div>
                    <el-tag size="small" :type="eq.running_mode === 'INTERMITTENT' ? 'warning' : 'info'" effect="plain" style="margin-right: 4px;">
                      {{ eq.running_mode === 'INTERMITTENT' ? '间歇作业' : '24h常开' }}
                    </el-tag>
                    <span>累计运行: <strong>{{ eq.total_running_hours }}</strong> h</span>
                  </div>
                  <el-tag size="small" :type="getCountdownTagType(eq.countdown_status)">{{ getCountdownLabel(eq) }}</el-tag>
                </div>
                <div style="font-size: 12px; color: #94a3b8; margin-top: 4px; display: flex; justify-content: space-between;">
                  <span>维护周期: {{ eq.maintenance_interval_hours }} 小时</span>
                  <span v-if="eq.estimated_days_left !== null && eq.countdown_status !== 'OVERDUE'" style="color: #d97706; font-weight: 500;">
                    预计约剩 {{ eq.estimated_days_left }} 天
                  </span>
                </div>
              </div>
              <div class="eq-footer">
                <el-button size="small" type="success" plain @click="quickMaintenance(eq)">+ 快速维保</el-button>
                <el-button size="small" type="danger" plain @click="quickRepair(eq)">+ 快速报修</el-button>
                <el-button size="small" type="primary" plain @click="openLogHours(eq)">⏱️ 记工时</el-button>
                <el-button size="small" type="primary" @click="openTimeline(eq)">病历档案</el-button>
                <el-button size="small" @click="showQrCode(eq)">二维码</el-button>
              </div>
            </el-card>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 录入设备抽屉/模态框 -->
    <el-dialog v-model="createDialogVisible" title="录入新设备 (零前置建树)" width="640px">
      <el-alert
        title="💡 零前置建树模式：无需预先创建架构树。直接在下方选择已有或手打新建工厂/部门/系统，系统将自动挂载生成架构树。"
        type="info"
        :closable="false"
        show-icon
        style="margin-bottom: 16px;"
      />
      <el-form :model="createForm" :rules="createRules" ref="createFormRef" label-width="120px">
        <el-form-item label="所属工厂" prop="factory">
          <el-select v-model="createForm.factory" filterable allow-create placeholder="选择已有或手打新建" style="width: 100%;">
            <el-option v-for="f in existingFactories" :key="f" :label="f" :value="f" />
          </el-select>
        </el-form-item>
        <el-form-item label="所属部门" prop="department">
          <el-select v-model="createForm.department" filterable allow-create placeholder="选择已有或手打新建" style="width: 100%;">
            <el-option v-for="d in existingDepartments" :key="d" :label="d" :value="d" />
          </el-select>
        </el-form-item>
        <el-form-item label="所属系统" prop="system_name">
          <el-select v-model="createForm.system_name" filterable allow-create placeholder="选择已有或手打新建" style="width: 100%;">
            <el-option v-for="s in existingSystems" :key="s" :label="s" :value="s" />
          </el-select>
        </el-form-item>
        <el-form-item label="设备名称" prop="equipment_name">
          <el-input v-model="createForm.equipment_name" placeholder="如: 1# 离心排风机 (强制必填)" />
        </el-form-item>
        <el-form-item label="规格型号" prop="model_spec">
          <el-input v-model="createForm.model_spec" placeholder="如: F-4-72-8C (强制必填)" />
        </el-form-item>
        <el-form-item label="设备编号" prop="equipment_code">
          <div style="display: flex; gap: 8px; width: 100%;">
            <el-input v-model="createForm.equipment_code" placeholder="如: DEV-2026-001，可点击右侧自动生成" />
            <el-button type="primary" plain @click="generateQuickCode">⚡ 自动生成</el-button>
          </div>
        </el-form-item>

        <el-form-item label="作业运行模式" prop="running_mode">
          <el-radio-group v-model="createForm.running_mode">
            <el-radio value="CONTINUOUS">🟢 24h 连续常开型 (风机/泵等，系统按自然时间推进)</el-radio>
            <el-radio value="INTERMITTENT">🔵 间歇/按需开机型 (加工中心/试验机，每天开2-8h不等)</el-radio>
          </el-radio-group>
        </el-form-item>

        <el-form-item label="维护倒计时周期" prop="maintenance_interval_hours">
          <div style="width: 100%;">
            <div style="display: flex; align-items: center; gap: 8px;">
              <el-input-number v-model="createForm.maintenance_interval_hours" :min="1" :step="50" style="width: 180px;" />
              <span style="color: #64748b; font-size: 13px;">小时 (h)</span>
            </div>
            <div style="margin-top: 8px; display: flex; align-items: center; gap: 6px; flex-wrap: wrap;">
              <span style="font-size: 12px; color: #94a3b8;">快捷预设:</span>
              <el-button size="small" text bg @click="createForm.maintenance_interval_hours = 100">100h(间歇设备推荐)</el-button>
              <el-button size="small" text bg @click="createForm.maintenance_interval_hours = 240">240h(约1月)</el-button>
              <el-button size="small" text bg @click="createForm.maintenance_interval_hours = 500">500h(季)</el-button>
              <el-button size="small" text bg @click="createForm.maintenance_interval_hours = 1000">1000h(半年)</el-button>
              <el-button size="small" text bg @click="createForm.maintenance_interval_hours = 2000">2000h(年)</el-button>
            </div>
          </div>
        </el-form-item>

        <el-form-item label="提前预警阈值" prop="advance_warning_hours">
          <div style="display: flex; align-items: center; gap: 8px;">
            <el-input-number v-model="createForm.advance_warning_hours" :min="1" :step="5" style="width: 150px;" />
            <span style="color: #64748b; font-size: 13px;">小时 (剩余少于此工时触发临期预警与邮件，如 15h)</span>
          </div>
        </el-form-item>

        <el-form-item label="初始运行工时">
          <div style="display: flex; align-items: center; gap: 8px;">
            <el-input-number v-model="createForm.initial_running_hours" :min="0" :precision="1" :step="10" style="width: 180px;" />
            <span style="color: #64748b; font-size: 13px;">小时 (新机填 0，已有旧机可录入当前表盘读数)</span>
          </div>
        </el-form-item>
        <el-form-item label="数量 (台/套)">
          <el-input-number v-model="createForm.quantity" :min="1" />
        </el-form-item>
        <el-form-item label="工况参数">
          <el-input v-model="createForm.parameters" type="textarea" :rows="2" placeholder="选填：额定功率/电压/扬程/风量等" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="createDialogVisible = false">取消</el-button>
        <el-button type="success" :loading="createLoading" @click="submitCreate(true)">保存并继续录入下一台</el-button>
        <el-button type="primary" :loading="createLoading" @click="submitCreate(false)">保 存</el-button>
      </template>
    </el-dialog>

    <!-- 现场抄表 / 记工时对话框 -->
    <el-dialog v-model="logHoursVisible" title="现场填报开机工时 / 抄表" width="500px">
      <div v-if="selectedEq" style="margin-bottom: 15px; padding: 12px; background: #f8fafc; border-radius: 6px; border: 1px solid #e2e8f0;">
        <div style="display: flex; justify-content: space-between; align-items: center;">
          <span style="font-weight: bold; font-size: 14px;">{{ selectedEq.equipment_name }}</span>
          <el-tag size="small" :type="selectedEq.running_mode === 'INTERMITTENT' ? 'warning' : 'info'">
            {{ selectedEq.running_mode === 'INTERMITTENT' ? '间歇作业型 (每天开2-8h)' : '24h连续常开型' }}
          </el-tag>
        </div>
        <div style="display: flex; justify-content: space-between; margin-top: 8px; font-size: 13px; color: #64748b;">
          <span>设备编号：<code>{{ selectedEq.equipment_code }}</code></span>
          <span>维护周期：<strong>{{ selectedEq.maintenance_interval_hours }}</strong> h</span>
        </div>
        <div style="display: flex; justify-content: space-between; margin-top: 4px; font-size: 13px; color: #64748b;">
          <span>当前累计工时：<strong>{{ selectedEq.total_running_hours }}</strong> h</span>
          <span>当前剩余工时：<strong :style="{ color: selectedEq.countdown_hours <= (selectedEq.advance_warning_hours || 20) ? '#dc2626' : '#16a34a' }">{{ selectedEq.countdown_hours }}</strong> h</span>
        </div>
      </div>

      <el-radio-group v-model="hoursForm.mode" style="margin-bottom: 16px; width: 100%; display: flex;" size="default">
        <el-radio-button value="DELTA" style="flex: 1;">⏱️ 今日实际开机时长 (增量累加)</el-radio-button>
        <el-radio-button value="READING" style="flex: 1;">🔢 表盘当前总读数 (抄表推算)</el-radio-button>
      </el-radio-group>

      <el-form :model="hoursForm" label-width="110px">
        <el-form-item v-if="hoursForm.mode === 'DELTA'" label="今日开机时长">
          <div style="width: 100%;">
            <div style="display: flex; align-items: center; gap: 8px;">
              <el-input-number v-model="hoursForm.delta_hours" :min="0.1" :max="24" :precision="1" :step="0.5" style="width: 160px;" />
              <span style="color: #64748b; font-size: 13px;">小时 (今天开了多久)</span>
            </div>
            <div style="margin-top: 6px; display: flex; gap: 6px;">
              <el-button size="small" text bg @click="hoursForm.delta_hours = 2">2h</el-button>
              <el-button size="small" text bg @click="hoursForm.delta_hours = 4">4h(半天)</el-button>
              <el-button size="small" text bg @click="hoursForm.delta_hours = 6">6h</el-button>
              <el-button size="small" text bg @click="hoursForm.delta_hours = 8">8h(整班)</el-button>
            </div>
          </div>
        </el-form-item>

        <el-form-item v-else label="表盘当前读数">
          <div style="display: flex; align-items: center; gap: 8px; width: 100%;">
            <el-input-number v-model="hoursForm.reading_hours" :min="0" :precision="1" :step="1" style="width: 200px;" />
            <span style="color: #64748b; font-size: 13px;">小时 (机床/仪表显示值)</span>
          </div>
        </el-form-item>

        <el-form-item label="填报工况备注">
          <el-input v-model="hoursForm.remark" placeholder="如：白班加工批次开机4小时 / 正常运行" />
        </el-form-item>

        <!-- 动态推算卡片 -->
        <div style="background: #eff6ff; border: 1px dashed #93c5fd; padding: 10px 14px; border-radius: 6px; margin-top: 5px; font-size: 13px; color: #1e40af;">
          <div>📊 <strong>录入后状态预估</strong>：</div>
          <div style="margin-top: 4px;">
            更新后累计开机：<strong>{{ predictedNewTotal }}</strong> h 
            (较此前 +{{ hoursForm.mode === 'DELTA' ? hoursForm.delta_hours : Math.max(0, (hoursForm.reading_hours - (selectedEq?.total_running_hours || 0))).toFixed(1) }} h)
          </div>
          <div style="margin-top: 2px;">
            距离保养周期还剩：<strong :style="{ color: predictedRemaining <= (selectedEq?.advance_warning_hours || 20) ? '#dc2626' : '#2563eb' }">{{ predictedRemaining }}</strong> h
            <span v-if="predictedDaysLeft !== null && predictedRemaining > 0">
              （按日均开机推算，<strong>预计约 {{ predictedDaysLeft }} 天后到期</strong>）
            </span>
            <span v-else-if="predictedRemaining <= 0" style="color: #dc2626; font-weight: bold;">
              （🚨 达到或超出周期阈值，将触发维保告警与邮件推送）
            </span>
          </div>
        </div>
      </el-form>
      <template #footer>
        <el-button @click="logHoursVisible = false">取消</el-button>
        <el-button type="primary" :loading="hoursLoading" @click="submitLogHours">确定录入并更新倒计时</el-button>
      </template>
    </el-dialog>

    <!-- 层级重命名对话框 -->
    <el-dialog v-model="renameDialogVisible" title="层级多次任意更名 (单事务原子同步)" width="480px">
      <el-form :model="renameForm" label-width="110px">
        <el-form-item label="更名层级">
          <el-tag>{{ renameForm.level }}</el-tag>
        </el-form-item>
        <el-form-item label="原名称">
          <el-input v-model="renameForm.old_name" disabled />
        </el-form-item>
        <el-form-item label="新名称">
          <el-input v-model="renameForm.new_name" placeholder="输入新的层级名称" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="renameDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="submitRename">确认批量同步修改</el-button>
      </template>
    </el-dialog>

    <!-- 二维码展示弹窗 -->
    <el-dialog v-model="qrVisible" title="一机一码工业标签" width="380px" align-center>
      <div style="text-align: center;" v-if="currentQrUrl">
        <img :src="currentQrUrl" style="width: 200px; height: 200px; border: 1px solid #e2e8f0; padding: 10px; border-radius: 8px;" />
        <p style="margin-top: 10px; color: #64748b; font-size: 13px;">扫码秒达该设备终身病历档案</p>
      </div>
    </el-dialog>

    <!-- 快速极速报修弹窗 -->
    <el-dialog v-model="quickRepairVisible" title="🚨 现场设备快速报修" width="560px">
      <div v-if="quickRepairTarget" style="margin-bottom: 12px; font-size: 13px; color: #475569;">
        目标设备：<strong>{{ quickRepairTarget.equipment_name }}</strong> ({{ quickRepairTarget.equipment_code }})
      </div>
      <el-form :model="quickRepairForm" label-width="90px">
        <el-form-item label="故障简述" required>
          <el-input v-model="quickRepairForm.title" placeholder="如：主轴承异响发烫" />
        </el-form-item>
        <el-form-item label="紧急度">
          <el-radio-group v-model="quickRepairForm.urgency">
            <el-radio label="NORMAL">普通</el-radio>
            <el-radio label="MAJOR">严重</el-radio>
            <el-radio label="CRITICAL">紧急</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="故障现象">
          <el-input v-model="quickRepairForm.phenomenon" type="textarea" :rows="2" placeholder="现场异响/烟雾/泄漏等详述" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="quickRepairVisible = false">取消</el-button>
        <el-button type="danger" :loading="quickRepairLoading" @click="submitQuickRepair">立即提交报修工单</el-button>
      </template>
    </el-dialog>

    <!-- 层级安全级联删除确认对话框 -->
    <el-dialog v-model="deleteHierarchyVisible" title="⚠️ 层级安全级联删除确认" width="540px">
      <div v-if="deleteHierarchyPreview" class="delete-preview-content">
        <el-alert
          :title="deleteHierarchyPreview.warning_message"
          type="warning"
          :closable="false"
          show-icon
        />
        <div style="margin-top: 16px; font-size: 13px; line-height: 1.8; color: #334155;">
          <div>🏭 目标层级：<strong>{{ deleteHierarchyPreview.level }} · {{ deleteHierarchyPreview.name }}</strong></div>
          <div>⚠️ 受影响停用设备：<span style="color: #ef4444; font-weight: bold;">{{ deleteHierarchyPreview.affected_equipments }} 台</span></div>
          <div>🔒 <strong>安全核心保障</strong>：系统检测到已有 <span style="color: #0284c7; font-weight: bold;">{{ deleteHierarchyPreview.retained_work_orders }} 张历史工单</span> 及 <span style="color: #10b981; font-weight: bold;">{{ deleteHierarchyPreview.retained_maintenance_records }} 条维保记录</span>，均将作为法定履历永久保留，绝不丢失！</div>
        </div>
      </div>
      <template #footer>
        <el-button @click="deleteHierarchyVisible = false">取消</el-button>
        <el-button type="danger" :loading="deleteHierarchyLoading" @click="submitDeleteHierarchy">确认执行停用删除</el-button>
      </template>
    </el-dialog>

    <!-- 后来人终身维修病历抽屉 -->
    <EquipmentTimelineDrawer ref="timelineDrawerRef" />
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import apiClient from '../../api/client'
import { useUserStore } from '../../stores/user'
import EquipmentTimelineDrawer from '../../components/EquipmentTimelineDrawer.vue'

const router = useRouter()

const userStore = useUserStore()
const loading = ref(false)
const viewMode = ref('table')
const searchQuery = ref('')
const activeFilter = ref('')

const equipments = ref<any[]>([])
const hierarchyTree = ref<any[]>([])
const timelineDrawerRef = ref()

// 录入相关
const createDialogVisible = ref(false)
const createLoading = ref(false)
const createFormRef = ref()
const createForm = reactive({
  factory: '总厂',
  department: '动力车间',
  system_name: '通用系统',
  equipment_name: '',
  model_spec: '',
  quantity: 1,
  equipment_code: '',
  running_mode: 'CONTINUOUS',
  maintenance_interval_hours: 500,
  advance_warning_hours: 20,
  initial_running_hours: 0,
  parameters: ''
})
const createRules = {
  factory: [{ required: true, message: '请选择或输入工厂', trigger: 'blur' }],
  department: [{ required: true, message: '请选择或输入部门', trigger: 'blur' }],
  system_name: [{ required: true, message: '请选择或输入系统', trigger: 'blur' }],
  equipment_name: [{ required: true, message: '设备名称为强制必填项', trigger: 'blur' }],
  model_spec: [{ required: true, message: '规格型号为强制必填项', trigger: 'blur' }]
}

// 快速生成设备编号
function generateQuickCode() {
  const year = new Date().getFullYear()
  const rand = Math.floor(1000 + Math.random() * 9000)
  createForm.equipment_code = `DEV-${year}-${rand}`
}

function getCountdownTagType(status: string) {
  if (status === 'OVERDUE') return 'danger'
  if (status === 'WARNING') return 'warning'
  return 'success'
}

function getCountdownLabel(row: any) {
  const cd = row.countdown_hours ?? 500
  if (cd <= 0) {
    return `🚨 已超期 ${Math.abs(cd)} h`
  } else if (cd <= (row.advance_warning_hours || 20)) {
    return `⏰ 临期剩 ${cd} h`
  } else {
    return `🟢 剩余 ${cd} h`
  }
}

// 抄表 / 记工时相关
const logHoursVisible = ref(false)
const hoursLoading = ref(false)
const selectedEq = ref<any>(null)
const hoursForm = reactive({
  mode: 'DELTA', // 'DELTA' (今日开机小时) 或 'READING' (表盘读数)
  delta_hours: 4.0,
  reading_hours: 0,
  remark: ''
})

const predictedNewTotal = computed(() => {
  if (!selectedEq.value) return 0
  const cur = Number(selectedEq.value.total_running_hours || 0)
  if (hoursForm.mode === 'DELTA') {
    return Number((cur + Number(hoursForm.delta_hours || 0)).toFixed(1))
  } else {
    return Number((hoursForm.reading_hours || 0).toFixed(1))
  }
})

const predictedRemaining = computed(() => {
  if (!selectedEq.value) return 0
  const interval = Number(selectedEq.value.maintenance_interval_hours || 500)
  const lastMaint = Number(selectedEq.value.last_maintenance_hours || 0)
  return Number((interval - (predictedNewTotal.value - lastMaint)).toFixed(1))
})

const predictedDaysLeft = computed(() => {
  if (!selectedEq.value) return null
  const rem = Math.max(0, predictedRemaining.value)
  const avg = Number(selectedEq.value.avg_daily_hours || (selectedEq.value.running_mode === 'INTERMITTENT' ? 4 : 24))
  if (avg <= 0) return null
  return Number((rem / avg).toFixed(1))
})

// 重命名相关
const renameDialogVisible = ref(false)
const renameForm = reactive({
  level: '',
  old_name: '',
  new_name: ''
})

// 二维码相关
const qrVisible = ref(false)
const currentQrUrl = ref('')

// 计算已存在的层级供下拉参考
const existingFactories = computed(() => hierarchyTree.value.map(n => n.name))
const existingDepartments = computed(() => {
  const depts = new Set<string>()
  hierarchyTree.value.forEach(f => {
    f.children?.forEach((d: any) => depts.add(d.name))
  })
  return Array.from(depts)
})
const existingSystems = computed(() => {
  const sys = new Set<string>()
  hierarchyTree.value.forEach(f => {
    f.children?.forEach((d: any) => {
      d.children?.forEach((s: any) => sys.add(s.name))
    })
  })
  return Array.from(sys)
})

async function fetchEquipments(extraParams = {}) {
  loading.value = true
  try {
    const params: any = { ...extraParams }
    if (searchQuery.value) {
      params.search = searchQuery.value
    }
    const res = await apiClient.get('/equipments', { params })
    equipments.value = res.data
  } catch (e) {
  } finally {
    loading.value = false
  }
}

async function fetchHierarchyTree() {
  try {
    const res = await apiClient.get('/equipments/hierarchy-tree')
    hierarchyTree.value = res.data
  } catch (e) {
  }
}

function handleNodeClick(data: any) {
  activeFilter.value = `${data.level}: ${data.name}`
  const params: any = {}
  if (data.level === 'factory') params.factory = data.name
  if (data.level === 'department') {
    params.factory = data.factory
    params.department = data.name
  }
  if (data.level === 'system_name') {
    params.factory = data.factory
    params.department = data.department
    params.system_name = data.name
  }
  fetchEquipments(params)
}

function clearFilter() {
  activeFilter.value = ''
  fetchEquipments()
}

function openCreateDialog() {
  createDialogVisible.value = true
}

async function submitCreate(continueNext = false) {
  if (!createFormRef.value) return
  await createFormRef.value.validate(async (valid: boolean) => {
    if (!valid) return
    createLoading.value = true
    try {
      await apiClient.post('/equipments', createForm)
      ElMessage.success('新设备建档成功！已自动生成专属二维码与维护倒计时')
      fetchEquipments()
      fetchHierarchyTree()
      if (continueNext) {
        // 清空名称和型号，保留层级，方便快速录入下一台
        createForm.equipment_name = ''
        createForm.model_spec = ''
        createForm.equipment_code = ''
        createForm.initial_running_hours = 0
        createForm.parameters = ''
      } else {
        createDialogVisible.value = false
      }
    } catch (e) {
    } finally {
      createLoading.value = false
    }
  })
}

function openLogHours(row: any) {
  selectedEq.value = row
  hoursForm.mode = row.running_mode === 'INTERMITTENT' ? 'DELTA' : 'READING'
  hoursForm.delta_hours = 4.0
  hoursForm.reading_hours = row.total_running_hours
  hoursForm.remark = ''
  logHoursVisible.value = true
}

async function submitLogHours() {
  if (!selectedEq.value) return
  hoursLoading.value = true
  try {
    const payload: any = {
      mode: hoursForm.mode,
      remark: hoursForm.remark
    }
    if (hoursForm.mode === 'DELTA') {
      payload.delta_hours = hoursForm.delta_hours
    } else {
      payload.reading_hours = hoursForm.reading_hours
    }
    const res = await apiClient.post(`/equipments/${selectedEq.value.id}/runtime-logs`, payload)
    ElMessage.success(`工时填报成功！本次开机运行 +${res.data.delta_hours} 小时，维护倒计时已自动更新`)
    logHoursVisible.value = false
    fetchEquipments()
  } catch (e) {
  } finally {
    hoursLoading.value = false
  }
}

function openRenameDialog(data: any) {
  renameForm.level = data.level
  renameForm.old_name = data.name
  renameForm.new_name = ''
  renameDialogVisible.value = true
}

async function submitRename() {
  if (!renameForm.new_name || renameForm.new_name.trim() === '') {
    ElMessage.warning('请输入新名称')
    return
  }
  try {
    const res = await apiClient.post('/equipments/rename-hierarchy', renameForm)
    ElMessage.success(res.data.message)
    renameDialogVisible.value = false
    fetchEquipments()
    fetchHierarchyTree()
  } catch (e) {
  }
}

function openTimeline(row: any) {
  if (timelineDrawerRef.value) {
    timelineDrawerRef.value.open(row.id, row.equipment_name)
  }
}

function showQrCode(row: any) {
  currentQrUrl.value = row.qr_code_url || ''
  qrVisible.value = true
}

function handleDelete(row: any) {
  ElMessageBox.confirm(`确定要移除设备 [${row.equipment_name}] 吗？历史病历将完整保留`, '提示', {
    type: 'warning'
  }).then(async () => {
    await apiClient.delete(`/equipments/${row.id}`)
    ElMessage.success('设备已移除')
    fetchEquipments()
    fetchHierarchyTree()
  }).catch(() => {})
}

function getStatusTag(status: string) {
  if (status === 'RUNNING') return 'success'
  if (status === 'REPAIRING') return 'danger'
  if (status === 'MAINTAINING') return 'warning'
  return 'info'
}

function getStatusText(status: string) {
  if (status === 'RUNNING') return '正常运行'
  if (status === 'REPAIRING') return '故障检修'
  if (status === 'MAINTAINING') return '维保中'
  return '停机'
}

// 快速维保跳转
function quickMaintenance(row: any) {
  router.push({ path: '/maintenance', query: { equipment_id: row.id } })
}

// 快速极速报修
const quickRepairVisible = ref(false)
const quickRepairLoading = ref(false)
const quickRepairTarget = ref<any>(null)
const quickRepairForm = reactive({
  title: '',
  urgency: 'NORMAL',
  phenomenon: ''
})

function quickRepair(row: any) {
  quickRepairTarget.value = row
  quickRepairForm.title = ''
  quickRepairForm.urgency = 'NORMAL'
  quickRepairForm.phenomenon = ''
  quickRepairVisible.value = true
}

async function submitQuickRepair() {
  if (!quickRepairForm.title || quickRepairForm.title.trim().length < 2) {
    ElMessage.warning('请输入故障简述')
    return
  }
  quickRepairLoading.value = true
  try {
    await apiClient.post('/work-orders', {
      equipment_id: quickRepairTarget.value.id,
      title: quickRepairForm.title.trim(),
      urgency: quickRepairForm.urgency,
      phenomenon: quickRepairForm.phenomenon
    })
    ElMessage.success('报修成功！已生成现场维护单并通知主管')
    quickRepairVisible.value = false
    fetchEquipments()
  } catch (e) {
  } finally {
    quickRepairLoading.value = false
  }
}

// 层级安全级联删除
const deleteHierarchyVisible = ref(false)
const deleteHierarchyLoading = ref(false)
const deleteHierarchyTarget = ref<any>(null)
const deleteHierarchyPreview = ref<any>(null)

async function openDeleteHierarchy(data: any) {
  deleteHierarchyTarget.value = data
  try {
    const res = await apiClient.post('/equipments/delete-hierarchy-preview', {
      level: data.level,
      name: data.name,
      factory: data.factory,
      department: data.department
    })
    deleteHierarchyPreview.value = res.data
    deleteHierarchyVisible.value = true
  } catch (e) {
  }
}

async function submitDeleteHierarchy() {
  if (!deleteHierarchyTarget.value) return
  deleteHierarchyLoading.value = true
  try {
    const res = await apiClient.post('/equipments/delete-hierarchy', {
      level: deleteHierarchyTarget.value.level,
      name: deleteHierarchyTarget.value.name,
      factory: deleteHierarchyTarget.value.factory,
      department: deleteHierarchyTarget.value.department
    })
    ElMessage.success(res.data.message)
    deleteHierarchyVisible.value = false
    fetchEquipments()
    fetchHierarchyTree()
  } catch (e) {
  } finally {
    deleteHierarchyLoading.value = false
  }
}

onMounted(() => {
  fetchEquipments()
  fetchHierarchyTree()
})
</script>

<style scoped>
.tree-card {
  height: calc(100vh - 130px);
  overflow-y: auto;
}
.tree-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-weight: bold;
}
.tree-tips {
  font-size: 12px;
  color: #94a3b8;
  margin-bottom: 12px;
}
.tree-node {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: 14px;
  padding-right: 8px;
}
.toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.highlight-name {
  font-weight: bold;
  color: #1e293b;
}
.countdown-cell {
  line-height: 1.4;
}
.cards-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 16px;
  margin-top: 15px;
}
.eq-card {
  border-radius: 8px;
  transition: all 0.2s;
}
.eq-card:hover {
  transform: translateY(-2px);
}
.eq-card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-weight: bold;
  margin-bottom: 8px;
}
.eq-title {
  font-size: 15px;
  color: #0f172a;
}
.eq-spec {
  font-size: 13px;
  color: #64748b;
  margin-bottom: 4px;
}
.eq-hierarchy {
  font-size: 12px;
  color: #94a3b8;
  margin-bottom: 8px;
}
.eq-countdown-block {
  background-color: #f8fafc;
  padding: 8px 10px;
  border-radius: 6px;
  margin-bottom: 12px;
}
.countdown-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 13px;
}
.eq-footer {
  display: flex;
  justify-content: flex-end;
  gap: 6px;
  border-top: 1px solid #f1f5f9;
  padding-top: 8px;
}
</style>
