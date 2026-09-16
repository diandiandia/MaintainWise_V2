<template>
  <div class="dashboard-page">
    <!-- 顶部驾驶舱态势条 -->
    <div class="welcome-banner">
      <div class="banner-content">
        <div class="banner-title">
          <span>🏭 MaintainWise 2.0 数据平台 · 智能车间数字驾驶舱</span>
          <span class="role-desc">当前席位：{{ roleText }} ({{ userStore.user?.full_name }})</span>
        </div>
        <p class="banner-sub">设备态势实时推演、故障风险智能溯源、预防性维护倒计时闭环监控。</p>
      </div>
      <div class="banner-kpis">
        <div class="kpi-mini">
          <span class="kpi-val text-success">{{ availabilityRate }}%</span>
          <span class="kpi-lbl">设备综合完好率</span>
        </div>
        <div class="kpi-mini">
          <span class="kpi-val text-warning">{{ mttrMinutes }} min</span>
          <span class="kpi-lbl">平均修复时长 (MTTR)</span>
        </div>
        <div class="kpi-mini">
          <span class="kpi-val text-primary">{{ inspectionPassRate }}%</span>
          <span class="kpi-lbl">巡检合格率</span>
        </div>
      </div>
    </div>

    <!-- 突发紧急安灯警报条 (如有停机或超期) -->
    <el-alert
      v-if="hasCriticalIssues"
      :title="criticalAlertTitle"
      type="error"
      show-icon
      :closable="false"
      class="andon-alert"
    >
      <template #default>
        <div class="alert-action-row">
          <span>{{ criticalAlertDesc }}</span>
          <el-button size="small" type="danger" plain @click="$router.push('/workorders')">立即查看处置 &gt;</el-button>
        </div>
      </template>
    </el-alert>

    <!-- 核心四态关键指标卡片 -->
    <el-row :gutter="16" class="stats-row">
      <el-col :span="6">
        <el-card shadow="hover" class="stat-card running-card">
          <div class="stat-icon-bg"><span class="badge-dot dot-success"></span></div>
          <div class="stat-num text-success">{{ dashboardData.equipment_stats.RUNNING || 0 }}</div>
          <div class="stat-label">正常平稳运行 (台)</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover" class="stat-card repairing-card">
          <div class="stat-icon-bg"><span class="badge-dot dot-danger"></span></div>
          <div class="stat-num text-danger">{{ dashboardData.equipment_stats.REPAIRING || 0 }}</div>
          <div class="stat-label">故障停机检修 (台)</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover" class="stat-card maintaining-card">
          <div class="stat-icon-bg"><span class="badge-dot dot-warning"></span></div>
          <div class="stat-num text-warning">{{ dashboardData.equipment_stats.MAINTAINING || 0 }}</div>
          <div class="stat-label">现场维护打卡中 (台)</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover" class="stat-card total-card">
          <div class="stat-icon-bg"><span class="badge-dot dot-primary"></span></div>
          <div class="stat-num text-primary">{{ dashboardData.total_equipments || 0 }}</div>
          <div class="stat-label">全厂在线资产总数 (台)</div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 领导层核心图表区：双列可视化仪表盘 (回答用户问题：问题展示方式) -->
    <el-row :gutter="16" style="margin-top: 16px;">
      <!-- 左列：全厂设备四态健康环形图 -->
      <el-col :span="10">
        <el-card shadow="hover" class="chart-card">
          <template #header>
            <div class="card-header">
              <span class="header-title">📊 全厂设备健康态势分布环形图</span>
              <el-tag size="small" type="info">实时采集</el-tag>
            </div>
          </template>
          <div class="donut-chart-wrapper">
            <div class="donut-svg-container">
              <svg viewBox="0 0 160 160" class="donut-svg">
                <!-- 背景底环 -->
                <circle cx="80" cy="80" r="60" fill="none" stroke="#f1f5f9" stroke-width="16" />
                <!-- 正常运行环段 (绿) -->
                <circle
                  cx="80" cy="80" r="60" fill="none"
                  stroke="#10b981" stroke-width="16"
                  :stroke-dasharray="`${runningStroke} 377`"
                  stroke-dashoffset="0"
                  class="donut-segment"
                />
                <!-- 停机检修环段 (红) -->
                <circle
                  cx="80" cy="80" r="60" fill="none"
                  stroke="#ef4444" stroke-width="16"
                  :stroke-dasharray="`${repairingStroke} 377`"
                  :stroke-dashoffset="`-${runningStroke}`"
                  class="donut-segment"
                />
                <!-- 维保中环段 (黄) -->
                <circle
                  cx="80" cy="80" r="60" fill="none"
                  stroke="#f59e0b" stroke-width="16"
                  :stroke-dasharray="`${maintainingStroke} 377`"
                  :stroke-dashoffset="`-${runningStroke + repairingStroke}`"
                  class="donut-segment"
                />
                <!-- 中心统计文字 -->
                <text x="80" y="74" text-anchor="middle" font-size="22" font-weight="bold" fill="#0f172a">{{ dashboardData.total_equipments }}</text>
                <text x="80" y="94" text-anchor="middle" font-size="12" fill="#64748b">在线设备</text>
              </svg>
            </div>

            <!-- 右侧图例与百分比 -->
            <div class="donut-legend">
              <div class="legend-item">
                <span class="legend-badge bg-success"></span>
                <span class="legend-name">正常运行</span>
                <span class="legend-cnt">{{ dashboardData.equipment_stats.RUNNING || 0 }} 台</span>
                <span class="legend-pct text-success">{{ runningPct }}%</span>
              </div>
              <div class="legend-item">
                <span class="legend-badge bg-danger"></span>
                <span class="legend-name">停机抢修</span>
                <span class="legend-cnt">{{ dashboardData.equipment_stats.REPAIRING || 0 }} 台</span>
                <span class="legend-pct text-danger">{{ repairingPct }}%</span>
              </div>
              <div class="legend-item">
                <span class="legend-badge bg-warning"></span>
                <span class="legend-name">巡检保养</span>
                <span class="legend-cnt">{{ dashboardData.equipment_stats.MAINTAINING || 0 }} 台</span>
                <span class="legend-pct text-warning">{{ maintainingPct }}%</span>
              </div>
            </div>
          </div>
        </el-card>
      </el-col>

      <!-- 右列：各车间部门设备完好与异常对比排行条 -->
      <el-col :span="14">
        <el-card shadow="hover" class="chart-card">
          <template #header>
            <div class="card-header">
              <span class="header-title">🏭 各车间部门设备完好度与异常问题排行</span>
              <el-tag size="small" type="success">按部门透视</el-tag>
            </div>
          </template>
          <div class="dept-bars-wrapper">
            <div v-if="!deptList.length" class="empty-todo">暂无车间数据</div>
            <div v-for="d in deptList" :key="d.department" class="dept-bar-row">
              <div class="dept-bar-label">
                <span class="dept-name">{{ d.department }}</span>
                <span class="dept-counts">
                  <span class="c-run">{{ d.running_devs || 0 }} 正常</span> /
                  <span class="c-rep" :class="{ 'has-rep': d.repairing_devs > 0 }">{{ d.repairing_devs || 0 }} 报修</span>
                  <span class="c-total">（共 {{ d.total_devs }} 台）</span>
                </span>
              </div>
              <div class="dept-bar-track">
                <div
                  class="dept-bar-fill-running"
                  :style="{ width: `${getDeptRunPct(d)}%` }"
                  title="正常运行比例"
                ></div>
                <div
                  v-if="d.repairing_devs > 0"
                  class="dept-bar-fill-repairing"
                  :style="{ width: `${getDeptRepPct(d)}%` }"
                  title="故障检修比例"
                ></div>
              </div>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 维护倒计时周期预警专区 (问题展示方式阶梯雷达) -->
    <el-card shadow="hover" class="countdown-card" style="margin-top: 16px;">
      <template #header>
        <div class="card-header">
          <div class="header-left">
            <span class="header-title">⏰ 设备维护工时倒计时阶梯预警 (预防性保养核心)</span>
            <span class="header-tip">按设备维护周期与累计工时动态推算，拒绝突发故障</span>
          </div>
          <el-button type="primary" link @click="$router.push('/equipments')">前往设备信息台账 &gt;</el-button>
        </div>
      </template>
      
      <el-row :gutter="16">
        <el-col :span="6">
          <div class="cd-summary-box">
            <div class="cd-metric overdue">
              <span class="cnt">{{ dashboardData.countdown_stats?.overdue_count || 0 }}</span>
              <span class="lbl">🚨 超期未维保</span>
            </div>
            <div class="cd-metric warning">
              <span class="cnt">{{ dashboardData.countdown_stats?.warning_count || 0 }}</span>
              <span class="lbl">⚠️ 周期临期预警</span>
            </div>
            <div class="cd-metric healthy">
              <span class="cnt">{{ dashboardData.countdown_stats?.healthy_count || 0 }}</span>
              <span class="lbl">🟢 周期充裕正常</span>
            </div>
          </div>
        </el-col>
        <el-col :span="18">
          <div v-if="!dashboardData.countdown_stats?.urgent_items?.length" class="empty-todo">
            🎉 全厂设备维护周期运转良好，暂无临期或超期设备！
          </div>
          <div v-else class="urgent-grid">
            <div
              v-for="item in dashboardData.countdown_stats.urgent_items"
              :key="item.id"
              class="urgent-item-card"
              :class="{ 'is-overdue': item.status === 'OVERDUE', 'is-warning': item.status === 'WARNING' }"
            >
              <div class="item-head">
                <div style="display: flex; gap: 4px; align-items: center;">
                  <el-tag size="small" :type="item.running_mode === 'INTERMITTENT' ? 'warning' : 'info'" effect="plain">
                    {{ item.running_mode === 'INTERMITTENT' ? '间歇' : '常开' }}
                  </el-tag>
                  <el-tag size="small" effect="plain" type="info">{{ item.equipment_code }}</el-tag>
                </div>
                <el-tag size="small" :type="item.status === 'OVERDUE' ? 'danger' : (item.status === 'WARNING' ? 'warning' : 'success')">
                  {{ item.status === 'OVERDUE' ? `已超期 ${Math.abs(item.countdown_hours)}h` : `剩 ${item.countdown_hours}h` }}
                </el-tag>
              </div>
              <div class="item-name">{{ item.equipment_name }}</div>
              <div class="item-loc">{{ item.location }}</div>
              <div v-if="item.estimated_days_left !== null && item.status !== 'OVERDUE'" style="font-size: 11px; color: #d97706; margin-top: 3px;">
                ⏳ 预计约剩 <strong>{{ item.estimated_days_left }}</strong> 天 (日均 {{ item.avg_daily_hours }}h)
              </div>
              <div class="item-foot" style="margin-top: 5px;">
                <span style="font-size: 11px; color: #94a3b8;">周期: {{ item.interval_hours }}h (已运转 {{ item.used_hours || item.total_running_hours }}h)</span>
                <el-button size="small" link type="primary" @click="$router.push(`/maintenance?equipment_id=${item.id}`)">快速维保</el-button>
              </div>
            </div>
          </div>
        </el-col>
      </el-row>
    </el-card>

    <!-- 下部双列：我的专属待办 与 现场维护单四态状态大盘 -->
    <el-row :gutter="16" style="margin-top: 16px;">
      <el-col :span="12">
        <el-card shadow="hover" style="height: 100%;">
          <template #header>
            <div class="card-header">
              <span class="header-title">📋 我的专属待办事项</span>
              <el-tag size="small" type="info">角色智能调度</el-tag>
            </div>
          </template>
          <div v-if="dashboardData.role_todos.length === 0" class="empty-todo">
            🎉 当前暂无待处理紧急任务，车间运转平稳！
          </div>
          <el-timeline v-else style="padding-left: 10px;">
            <el-timeline-item
              v-for="(todo, idx) in dashboardData.role_todos"
              :key="idx"
              :type="todo.urgency === 'CRITICAL' ? 'danger' : (todo.urgency === 'MAJOR' ? 'warning' : 'primary')"
            >
              <div class="todo-item">
                <span class="todo-text">{{ todo.title }}</span>
                <el-button size="small" type="primary" link @click="$router.push(todo.target_url)">立即处理 &gt;</el-button>
              </div>
            </el-timeline-item>
          </el-timeline>
        </el-card>
      </el-col>

      <el-col :span="12">
        <el-card shadow="hover" style="height: 100%;">
          <template #header>
            <div class="card-header">
              <span class="header-title">⚡ 现场维护单流转矩阵</span>
              <el-button type="primary" link @click="$router.push('/workorders')">打开全屏看板 &gt;</el-button>
            </div>
          </template>
          <div class="wo-kanban-mini">
            <div class="mini-col red-col">
              <div class="m-title">待派/待抢</div>
              <div class="m-cnt">{{ dashboardData.work_order_stats.PENDING || 0 }}</div>
            </div>
            <div class="mini-col blue-col">
              <div class="m-title">抢修排故中</div>
              <div class="m-cnt">{{ dashboardData.work_order_stats.IN_PROGRESS || 0 }}</div>
            </div>
            <div class="mini-col orange-col">
              <div class="m-title">完工待验收</div>
              <div class="m-cnt">{{ dashboardData.work_order_stats.PENDING_CONFIRM || 0 }}</div>
            </div>
            <div class="mini-col green-col">
              <div class="m-title">已闭环归档</div>
              <div class="m-cnt">{{ dashboardData.work_order_stats.CLOSED || 0 }}</div>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import apiClient from '../../api/client'
import { useUserStore } from '../../stores/user'

const userStore = useUserStore()

const dashboardData = ref<any>({
  equipment_stats: { RUNNING: 0, REPAIRING: 0, MAINTAINING: 0, STOPPED: 0 },
  work_order_stats: { PENDING: 0, IN_PROGRESS: 0, PENDING_CONFIRM: 0, CLOSED: 0 },
  role_todos: [],
  total_equipments: 0,
  countdown_stats: { overdue_count: 0, warning_count: 0, healthy_count: 0, urgent_items: [] },
  executive_kpis: { availability_rate: 100, avg_mttr_minutes: 30, inspection_pass_rate: 100 },
  department_issue_stats: []
})

const roleText = computed(() => {
  if (userStore.user?.role === 'ADMIN') return '系统管理员'
  if (userStore.user?.role === 'ENGINEER') return '主管工程师'
  return '维保技术员'
})

const availabilityRate = computed(() => {
  return dashboardData.value.executive_kpis?.availability_rate ?? 100
})

const mttrMinutes = computed(() => {
  return dashboardData.value.executive_kpis?.avg_mttr_minutes ?? 30
})

const inspectionPassRate = computed(() => {
  return dashboardData.value.executive_kpis?.inspection_pass_rate ?? 100
})

// 环形图计算 (周长约为 2 * pi * 60 = 377)
const CIRCUMFERENCE = 377

const runningPct = computed(() => {
  const tot = dashboardData.value.total_equipments || 1
  return Math.round(((dashboardData.value.equipment_stats.RUNNING || 0) / tot) * 100)
})
const repairingPct = computed(() => {
  const tot = dashboardData.value.total_equipments || 1
  return Math.round(((dashboardData.value.equipment_stats.REPAIRING || 0) / tot) * 100)
})
const maintainingPct = computed(() => {
  const tot = dashboardData.value.total_equipments || 1
  return Math.round(((dashboardData.value.equipment_stats.MAINTAINING || 0) / tot) * 100)
})

const runningStroke = computed(() => (runningPct.value / 100) * CIRCUMFERENCE)
const repairingStroke = computed(() => (repairingPct.value / 100) * CIRCUMFERENCE)
const maintainingStroke = computed(() => (maintainingPct.value / 100) * CIRCUMFERENCE)

// 部门排行
const deptList = computed(() => dashboardData.value.department_issue_stats || [])

function getDeptRunPct(d: any) {
  if (!d.total_devs) return 100
  return Math.round(((d.running_devs || 0) / d.total_devs) * 100)
}

function getDeptRepPct(d: any) {
  if (!d.total_devs) return 0
  return Math.round(((d.repairing_devs || 0) / d.total_devs) * 100)
}

const hasCriticalIssues = computed(() => {
  const repairing = dashboardData.value.equipment_stats.REPAIRING || 0
  const overdue = dashboardData.value.countdown_stats?.overdue_count || 0
  const pending = dashboardData.value.work_order_stats.PENDING || 0
  return repairing > 0 || overdue > 0 || pending > 0
})

const criticalAlertTitle = computed(() => {
  const repairing = dashboardData.value.equipment_stats.REPAIRING || 0
  const overdue = dashboardData.value.countdown_stats?.overdue_count || 0
  if (repairing > 0) return `🚨 车间安灯警报：当前有 ${repairing} 台核心设备处于故障停机状态！`
  if (overdue > 0) return `⚠️ 预防性维护告警：当前有 ${overdue} 台设备超出维护运行工时周期！`
  return `📋 工单响应提醒：当前有待派发的突发维修工单`
})

const criticalAlertDesc = computed(() => {
  return '请立即查看并调度主管工程师与一线技术员快速介入排故与保养，避免非计划停产扩散。'
})

async function fetchDashboard() {
  try {
    const res = await apiClient.get('/system/dashboard')
    dashboardData.value = res.data
  } catch (e) {
  }
}

onMounted(() => {
  fetchDashboard()
})
</script>

<style scoped>
.welcome-banner {
  background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
  color: #ffffff;
  padding: 22px 28px;
  border-radius: 12px;
  margin-bottom: 16px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
}
.banner-title {
  font-size: 20px;
  font-weight: bold;
  display: flex;
  align-items: center;
  gap: 12px;
}
.role-desc {
  font-size: 13px;
  background-color: rgba(59, 130, 246, 0.2);
  border: 1px solid rgba(59, 130, 246, 0.4);
  color: #93c5fd;
  padding: 2px 10px;
  border-radius: 20px;
}
.banner-sub {
  margin-top: 8px;
  font-size: 13px;
  color: #94a3b8;
}
.banner-kpis {
  display: flex;
  gap: 20px;
}
.kpi-mini {
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.1);
  padding: 10px 18px;
  border-radius: 8px;
  text-align: center;
  min-width: 120px;
}
.kpi-val {
  font-size: 22px;
  font-weight: bold;
  display: block;
}
.kpi-lbl {
  font-size: 11px;
  color: #94a3b8;
  margin-top: 4px;
}
.andon-alert {
  margin-bottom: 16px;
}
.alert-action-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 4px;
}
.stat-card {
  text-align: center;
  border-radius: 10px;
  position: relative;
  overflow: hidden;
}
.stat-num {
  font-size: 32px;
  font-weight: bold;
}
.text-success { color: #10b981; }
.text-danger { color: #ef4444; }
.text-warning { color: #f59e0b; }
.text-primary { color: #3b82f6; }
.stat-label {
  font-size: 13px;
  color: #64748b;
  margin-top: 4px;
}
.running-card { border-top: 4px solid #10b981; }
.repairing-card { border-top: 4px solid #ef4444; }
.maintaining-card { border-top: 4px solid #f59e0b; }
.total-card { border-top: 4px solid #3b82f6; }

.badge-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  display: inline-block;
  margin-bottom: 6px;
}
.dot-success { background: #10b981; box-shadow: 0 0 8px #10b981; }
.dot-danger { background: #ef4444; box-shadow: 0 0 8px #ef4444; }
.dot-warning { background: #f59e0b; box-shadow: 0 0 8px #f59e0b; }
.dot-primary { background: #3b82f6; box-shadow: 0 0 8px #3b82f6; }

.chart-card {
  height: 280px;
}
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.header-title {
  font-size: 15px;
  font-weight: bold;
  color: #1e293b;
}
.header-left {
  display: flex;
  align-items: center;
  gap: 10px;
}
.header-tip {
  font-size: 12px;
  color: #94a3b8;
  font-weight: normal;
}

/* Donut Chart */
.donut-chart-wrapper {
  display: flex;
  align-items: center;
  justify-content: space-around;
  height: 190px;
}
.donut-svg-container {
  width: 160px;
  height: 160px;
}
.donut-svg {
  transform: rotate(-90deg);
  width: 100%;
  height: 100%;
}
.donut-segment {
  transition: stroke-dasharray 0.5s ease;
}
.donut-legend {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.legend-item {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
}
.legend-badge {
  width: 10px;
  height: 10px;
  border-radius: 2px;
}
.bg-success { background-color: #10b981; }
.bg-danger { background-color: #ef4444; }
.bg-warning { background-color: #f59e0b; }
.legend-name { color: #475569; width: 70px; }
.legend-cnt { font-weight: bold; color: #1e293b; width: 50px; }
.legend-pct { font-weight: bold; width: 45px; text-align: right; }

/* Department issue bar */
.dept-bars-wrapper {
  display: flex;
  flex-direction: column;
  gap: 14px;
  padding: 8px 0;
  height: 190px;
  overflow-y: auto;
}
.dept-bar-row {
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.dept-bar-label {
  display: flex;
  justify-content: space-between;
  font-size: 13px;
}
.dept-name { font-weight: 600; color: #1e293b; }
.dept-counts { font-size: 12px; color: #64748b; }
.c-run { color: #10b981; font-weight: bold; }
.c-rep { color: #94a3b8; }
.c-rep.has-rep { color: #ef4444; font-weight: bold; }
.c-total { color: #94a3b8; }
.dept-bar-track {
  height: 12px;
  background: #f1f5f9;
  border-radius: 6px;
  display: flex;
  overflow: hidden;
}
.dept-bar-fill-running {
  background: #10b981;
  height: 100%;
}
.dept-bar-fill-repairing {
  background: #ef4444;
  height: 100%;
}

.cd-summary-box {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.cd-metric {
  padding: 10px 14px;
  border-radius: 6px;
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.cd-metric.overdue { background-color: #fee2e2; color: #991b1b; }
.cd-metric.warning { background-color: #fef3c7; color: #92400e; }
.cd-metric.healthy { background-color: #ecfdf5; color: #065f46; }
.cd-metric .cnt { font-size: 20px; font-weight: bold; }
.cd-metric .lbl { font-size: 13px; }

.urgent-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
  gap: 12px;
}
.urgent-item-card {
  background: #ffffff;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  padding: 12px;
  display: flex;
  flex-direction: column;
  gap: 6px;
  transition: all 0.2s;
}
.urgent-item-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
}
.urgent-item-card.is-overdue {
  border-color: #fca5a5;
  background-color: #fffaf0;
}
.urgent-item-card.is-warning {
  border-color: #fde68a;
}
.item-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.item-name {
  font-weight: bold;
  font-size: 14px;
  color: #1e293b;
}
.item-loc {
  font-size: 12px;
  color: #64748b;
}
.item-foot {
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-top: 1px dashed #f1f5f9;
  padding-top: 6px;
  margin-top: 2px;
}
.todo-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.todo-text {
  font-size: 13px;
  color: #334155;
}
.empty-todo {
  text-align: center;
  padding: 40px;
  color: #94a3b8;
  font-size: 13px;
}
.wo-kanban-mini {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
  padding: 10px 0;
}
.mini-col {
  text-align: center;
  padding: 16px 8px;
  border-radius: 8px;
  background-color: #f8fafc;
}
.mini-col.red-col { border-top: 3px solid #ef4444; }
.mini-col.blue-col { border-top: 3px solid #3b82f6; }
.mini-col.orange-col { border-top: 3px solid #f59e0b; }
.mini-col.green-col { border-top: 3px solid #10b981; }
.m-title {
  font-size: 12px;
  color: #64748b;
  margin-bottom: 8px;
}
.m-cnt {
  font-size: 24px;
  font-weight: bold;
  color: #0f172a;
}
</style>
