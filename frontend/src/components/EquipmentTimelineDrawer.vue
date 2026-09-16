<template>
  <el-drawer
    v-model="visible"
    :title="`后来人终身维修病历档案 — ${equipmentName}`"
    size="60%"
    direction="rtl"
  >
    <div v-loading="loading" class="timeline-container">
      <div v-if="items.length === 0" class="empty-hint">
        暂无任何维修或巡检流水记录，该设备为全新入厂状态。
      </div>

      <el-timeline v-else>
        <el-timeline-item
          v-for="(ev, idx) in items"
          :key="idx"
          :timestamp="ev.event_time"
          placement="top"
          :type="getEventType(ev.event_type)"
          :hollow="true"
        >
          <el-card class="timeline-card">
            <div class="card-top">
              <span class="event-title">{{ ev.title }}</span>
              <el-tag size="small" :type="getEventTagType(ev.event_type)">{{ getEventTagText(ev.event_type) }}</el-tag>
            </div>
            <div class="operator-line">经办/承修人：<strong>{{ ev.operator_name }}</strong></div>

            <!-- 维修工单详情：高亮根本原因与排除步骤 -->
            <div v-if="ev.event_type === 'WORK_ORDER'" class="wo-details">
              <div class="phenomenon-box">
                <span class="lbl">故障现象：</span>{{ ev.details.phenomenon || '无详细记录' }}
              </div>
              <div class="cause-box">
                <span class="lbl-alert">⚠️ 根本原因 (后来人必看)：</span>
                <div class="cause-text">{{ ev.details.root_cause || '未录入' }}</div>
              </div>
              <div class="solution-box">
                <span class="lbl-success">🛠️ 详细排除步骤与作业标准：</span>
                <pre class="solution-text">{{ ev.details.solution_steps || '未录入' }}</pre>
              </div>
              <div class="spare-line" v-if="ev.details.spare_parts">
                <span class="lbl">更换备件：</span>{{ ev.details.spare_parts }} (耗时: {{ ev.details.duration_minutes }}分钟)
              </div>
            </div>

            <!-- 维保打卡详情 -->
            <div v-else-if="ev.event_type === 'MAINTENANCE'" class="mnt-details">
              <div v-if="ev.details.anomaly_desc" class="anomaly-text">
                <span class="lbl-alert">巡检异常：</span>{{ ev.details.anomaly_desc }}
              </div>
              <div v-if="ev.details.revision_reason" class="revision-box">
                <span class="lbl-rev">工程师复核修改批注 ({{ ev.details.revised_by_engineer }})：</span>
                <div>{{ ev.details.revision_reason }}</div>
              </div>
              <div class="checklist-summary">
                <span>检查项结果：</span>
                <el-tag
                  v-for="(ck, cidx) in ev.details.checklist"
                  :key="cidx"
                  size="small"
                  :type="ck.status === 'NORMAL' ? 'success' : 'danger'"
                  style="margin-right: 6px; margin-top: 4px;"
                >
                  {{ ck.item }}: {{ ck.status === 'NORMAL' ? '正常' : '异常' }}
                </el-tag>
              </div>
            </div>

            <!-- 工时抄表详情 -->
            <div v-else-if="ev.event_type === 'RUNTIME_LOG'" class="rt-details">
              <span class="rt-badge">累计表盘：{{ ev.details.reading_hours }} 小时</span>
              <span class="rt-badge delta">本次增量：+{{ ev.details.delta_hours }} 小时</span>
              <span v-if="ev.details.remark" class="rt-remark">备注: {{ ev.details.remark }}</span>
            </div>
          </el-card>
        </el-timeline-item>
      </el-timeline>
    </div>
  </el-drawer>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import apiClient from '../api/client'

const visible = ref(false)
const loading = ref(false)
const equipmentName = ref('')
const items = ref<any[]>([])

function open(eqId: number, name: string) {
  equipmentName.value = name
  visible.value = true
  fetchTimeline(eqId)
}

async function fetchTimeline(eqId: number) {
  loading.value = true
  try {
    const res = await apiClient.get(`/equipments/${eqId}/timeline`)
    items.value = res.data.timeline_items || []
  } catch (e) {
    // 错误由拦截器弹出
  } finally {
    loading.value = false
  }
}

function getEventType(type: string) {
  if (type === 'WORK_ORDER') return 'danger'
  if (type === 'MAINTENANCE') return 'primary'
  return 'info'
}

function getEventTagType(type: string) {
  if (type === 'WORK_ORDER') return 'danger'
  if (type === 'MAINTENANCE') return 'primary'
  return 'info'
}

function getEventTagText(type: string) {
  if (type === 'WORK_ORDER') return '突发维修工单'
  if (type === 'MAINTENANCE') return '维保打卡记录'
  return '运行工时抄表'
}

defineExpose({ open })
</script>

<style scoped>
.timeline-container {
  padding: 10px 20px;
}
.empty-hint {
  text-align: center;
  color: #94a3b8;
  padding: 40px 0;
}
.timeline-card {
  border-radius: 8px;
}
.card-top {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}
.event-title {
  font-weight: bold;
  font-size: 15px;
  color: #1e293b;
}
.operator-line {
  font-size: 13px;
  color: #64748b;
  margin-bottom: 12px;
}
.cause-box {
  background-color: #fef2f2;
  border-left: 4px solid #ef4444;
  padding: 10px;
  border-radius: 4px;
  margin-top: 8px;
}
.lbl-alert {
  color: #b91c1c;
  font-weight: bold;
}
.cause-text {
  color: #7f1d1d;
  margin-top: 4px;
}
.solution-box {
  background-color: #f0fdf4;
  border-left: 4px solid #22c55e;
  padding: 10px;
  border-radius: 4px;
  margin-top: 8px;
}
.lbl-success {
  color: #15803d;
  font-weight: bold;
}
.solution-text {
  margin: 4px 0 0;
  font-family: inherit;
  white-space: pre-wrap;
  color: #14532d;
}
.spare-line {
  margin-top: 8px;
  font-size: 13px;
  color: #475569;
}
.revision-box {
  background-color: #fffbeb;
  border-left: 4px solid #f59e0b;
  padding: 8px;
  border-radius: 4px;
  margin-top: 6px;
  font-size: 13px;
  color: #92400e;
}
.lbl-rev {
  font-weight: bold;
}
.checklist-summary {
  margin-top: 8px;
  font-size: 13px;
}
.rt-badge {
  display: inline-block;
  background-color: #f1f5f9;
  padding: 4px 8px;
  border-radius: 4px;
  font-size: 13px;
  color: #334155;
  margin-right: 8px;
}
.rt-badge.delta {
  background-color: #e0f2fe;
  color: #0369a1;
  font-weight: bold;
}
.rt-remark {
  font-size: 12px;
  color: #64748b;
}
</style>
