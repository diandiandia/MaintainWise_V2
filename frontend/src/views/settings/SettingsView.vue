<template>
  <div class="settings-page">
    <el-row :gutter="20">
      <el-col :span="12">
        <el-card shadow="hover">
          <template #header>
            <div class="card-title">🏭 系统工厂企业定制</div>
          </template>
          <el-form :model="settingsForm" label-width="120px">
            <el-form-item label="企业大标题">
              <el-input v-model="settingsForm.factory_name" placeholder="显示于系统各端的大标题" />
            </el-form-item>
            <el-form-item label="维保临期预警">
              <el-input-number v-model="settingsForm.notify_lead_days" :min="1" :max="30" /> 天
            </el-form-item>
            <el-form-item>
              <el-button type="primary" :loading="saveLoading" @click="saveSettings">保存基础参数</el-button>
            </el-form-item>
          </el-form>
        </el-card>

        <el-card shadow="hover" style="margin-top: 20px;">
          <template #header>
            <div class="card-title">📧 全厂邮件通知服务配置 (SMTP)</div>
          </template>
          <p style="color: #64748b; font-size: 13px; line-height: 1.6; margin-bottom: 15px;">
            配置 SMTP 邮件服务器后，系统将在<strong>突发工单派发</strong>、<strong>设备维保巡检异常</strong>、<strong>账号密码180天到期临期3天预警</strong>时，自动向相关责任工程师与技术员推送邮件。
          </p>
          <el-form :model="settingsForm" label-width="120px">
            <el-form-item label="启用邮件通知">
              <el-switch v-model="settingsForm.smtp_enabled" active-text="已启用" inactive-text="已停用" />
            </el-form-item>
            <el-form-item label="SMTP 服务器">
              <el-input v-model="settingsForm.smtp_host" placeholder="如: smtp.exmail.qq.com / smtp.163.com" />
            </el-form-item>
            <el-form-item label="SMTP 端口">
              <el-input-number v-model="settingsForm.smtp_port" :min="1" :max="65535" style="width: 160px;" />
              <span style="color: #94a3b8; font-size: 12px; margin-left: 10px;">(常用 SSL: 465, STARTTLS: 587)</span>
            </el-form-item>
            <el-form-item label="发信邮箱账号">
              <el-input v-model="settingsForm.smtp_user" placeholder="如: notify@factory-mes.com" />
            </el-form-item>
            <el-form-item label="发信授权码/密码">
              <el-input v-model="settingsForm.smtp_pass" type="password" show-password placeholder="输入发信邮箱的客户端授权码或密码" />
            </el-form-item>
            <el-divider />
            <el-form-item label="联通性测试">
              <div style="display: flex; gap: 10px; width: 100%;">
                <el-input v-model="testEmailTarget" placeholder="接收测试邮件的目标邮箱" />
                <el-button type="warning" :loading="testLoading" @click="testSmtp">测试发信</el-button>
              </div>
            </el-form-item>
            <el-form-item>
              <el-button type="primary" :loading="saveLoading" @click="saveSettings">保存邮件配置</el-button>
            </el-form-item>
          </el-form>
        </el-card>
      </el-col>

      <el-col :span="12">
        <el-card shadow="hover">
          <template #header>
            <div class="card-title">📦 SQLite WAL 纯内存一键全量热备份</div>
          </template>
          <p style="color: #64748b; font-size: 13px; line-height: 1.6;">
            无需停止服务、无需专业 DBA！系统将在后台流式将当前 SQLite 单文件数据库及所有二维码、图纸附件打包压缩为一个标准 ZIP 归档包，存放在 <code>data/backups/</code> 目录。
          </p>
          <div style="margin-top: 20px;">
            <el-button type="success" size="large" :loading="backupLoading" @click="triggerBackup">
              ⚡ 立即执行全量热备份
            </el-button>
          </div>

          <div v-if="lastBackup" class="backup-result">
            <el-alert title="备份成功！" type="success" :closable="false" show-icon>
              <div>归档文件：<strong>{{ lastBackup.backup_file }}</strong></div>
              <div>文件体积：{{ (lastBackup.size_bytes / 1024).toFixed(1) }} KB</div>
              <div>存储路径：{{ lastBackup.backup_path }}</div>
            </el-alert>
          </div>
        </el-card>

        <el-card shadow="hover" style="margin-top: 20px;">
          <template #header>
            <div class="card-title">🔒 全厂密码安全合规策略说明</div>
          </template>
          <el-timeline style="margin-top: 10px; padding-left: 10px;">
            <el-timeline-item timestamp="首次登录必改" type="primary">
              新录入的技术员或工程师，首次使用初始密码登录时，系统将强制弹出改密对话框，修改完成前不可进入任何业务界面。
            </el-timeline-item>
            <el-timeline-item timestamp="180 天强制轮换" type="warning">
              遵循工业信息系统安全等级保护规范，用户密码有效期为 180 天。
            </el-timeline-item>
            <el-timeline-item timestamp="到期前 3 天邮件/站内预警" type="warning">
              密码到期前 3 天，系统将在顶部常驻告警条，并自动发送邮件提醒员工尽快更换密码。
            </el-timeline-item>
            <el-timeline-item timestamp="超期自动冻结" type="danger">
              若超过 180 天仍未更换密码，账号将被系统自动锁定冻结，需由系统管理员在【用户管理】界面进行审核并手动解冻。
            </el-timeline-item>
          </el-timeline>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import apiClient from '../../api/client'
import { useUserStore } from '../../stores/user'

const userStore = useUserStore()
const saveLoading = ref(false)
const backupLoading = ref(false)
const testLoading = ref(false)
const lastBackup = ref<any>(null)
const testEmailTarget = ref('')

const settingsForm = reactive({
  factory_name: 'MaintainWise 智能工厂',
  notify_lead_days: 3,
  smtp_host: '',
  smtp_port: 465,
  smtp_user: '',
  smtp_pass: '',
  smtp_enabled: false
})

async function fetchSettings() {
  try {
    const res = await apiClient.get('/system/settings')
    settingsForm.factory_name = res.data.factory_name
    settingsForm.notify_lead_days = res.data.notify_lead_days
    settingsForm.smtp_host = res.data.smtp_host || ''
    settingsForm.smtp_port = res.data.smtp_port || 465
    settingsForm.smtp_user = res.data.smtp_user || ''
    settingsForm.smtp_pass = res.data.smtp_pass || ''
    settingsForm.smtp_enabled = !!res.data.smtp_enabled
    if (userStore.user?.email && !testEmailTarget.value) {
      testEmailTarget.value = userStore.user.email
    }
  } catch (e) {
  }
}

async function saveSettings() {
  saveLoading.value = true
  try {
    await apiClient.put('/system/settings', settingsForm)
    ElMessage.success('系统配置参数与邮件服务设置已成功保存！')
  } catch (e) {
  } finally {
    saveLoading.value = false
  }
}

async function testSmtp() {
  if (!settingsForm.smtp_host || !settingsForm.smtp_user) {
    ElMessage.warning('请先填写 SMTP 主机与发信账号')
    return
  }
  testLoading.value = true
  try {
    const res = await apiClient.post('/system/smtp/test', {
      host: settingsForm.smtp_host,
      port: settingsForm.smtp_port,
      user: settingsForm.smtp_user,
      password: settingsForm.smtp_pass,
      to_email: testEmailTarget.value || settingsForm.smtp_user
    })
    if (res.data.success) {
      ElMessageBox.alert(`测试邮件已成功发送！服务器响应：${res.data.message}`, 'SMTP 通信成功', { type: 'success' })
    } else {
      ElMessageBox.alert(`测试失败：${res.data.message}`, 'SMTP 通信异常', { type: 'error' })
    }
  } catch (e: any) {
    ElMessage.error(e.response?.data?.detail || 'SMTP 发送失败，请检查网络和服务器端口配置')
  } finally {
    testLoading.value = false
  }
}

async function triggerBackup() {
  backupLoading.value = true
  try {
    const res = await apiClient.post('/system/backup')
    lastBackup.value = res.data
    ElMessage.success('数据热备份生成成功！')
  } catch (e) {
  } finally {
    backupLoading.value = false
  }
}

onMounted(() => {
  fetchSettings()
})
</script>

<style scoped>
.card-title {
  font-weight: bold;
  font-size: 15px;
}
.backup-result {
  margin-top: 20px;
}
</style>
