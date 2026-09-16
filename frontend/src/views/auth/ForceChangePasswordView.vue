<template>
  <div class="force-pwd-wrapper">
    <div class="force-pwd-card">
      <div class="security-badge-container">
        <div class="security-shield-icon">
          <el-icon :size="38"><Lock /></el-icon>
        </div>
        <h2 class="title">首次登录安全强制要求</h2>
        <p class="subtitle">MaintainWise 2.0 工业资产信息安全合规管控</p>
      </div>

      <!-- 当前账号身份核验 -->
      <div class="user-profile-strip">
        <div class="profile-item">
          <span class="label">当前登录人：</span>
          <span class="val font-bold">{{ userStore.user?.full_name || '工友用户' }}</span>
        </div>
        <div class="profile-item">
          <span class="label">系统账号：</span>
          <span class="val font-mono">{{ userStore.user?.username }} ({{ userStore.user?.employee_no || '-' }})</span>
        </div>
        <div class="profile-item">
          <span class="label">分配角色：</span>
          <el-tag :type="roleTagType" size="small" effect="dark">{{ roleText }}</el-tag>
        </div>
      </div>

      <!-- 隔离警示说明 -->
      <el-alert
        title="工业级账户安全隔离提示"
        type="warning"
        :closable="false"
        show-icon
        description="检测到您正在使用初始默认密码或管理员重置后的临时密码。为防止越权与车间工业数据泄漏，系统已开启数据保护屏障。您必须先设定专属高强度新密码，系统方可放行进入数据平台与设备工单中心。"
        class="mb-4"
      />

      <!-- 修改密码表单 -->
      <el-form :model="form" :rules="rules" ref="formRef" label-position="top" class="pwd-form">
        <el-form-item label="设置专属新密码" prop="new_password">
          <el-input
            v-model="form.new_password"
            type="password"
            size="large"
            placeholder="请输入至少 6 位新密码"
            :prefix-icon="Key"
            show-password
          />
        </el-form-item>

        <el-form-item label="确认新密码" prop="confirm_password">
          <el-input
            v-model="form.confirm_password"
            type="password"
            size="large"
            placeholder="请再次输入新密码核对"
            :prefix-icon="Key"
            show-password
            @keyup.enter="handleSubmit"
          />
        </el-form-item>

        <div class="security-hints">
          <div class="hint-title">密码合规规则：</div>
          <div class="hint-item" :class="{ pass: form.new_password.length >= 6 }">
            <el-icon><Check v-if="form.new_password.length >= 6" /><Close v-else /></el-icon>
            密码长度达到 6 位及以上
          </div>
          <div class="hint-item" :class="{ pass: form.new_password && form.new_password !== 'password123' }">
            <el-icon><Check v-if="form.new_password && form.new_password !== 'password123'" /><Close v-else /></el-icon>
            不能与出厂初始密码 (password123) 相同
          </div>
          <div class="hint-item" :class="{ pass: form.new_password && form.new_password === form.confirm_password }">
            <el-icon><Check v-if="form.new_password && form.new_password === form.confirm_password" /><Close v-else /></el-icon>
            两次输入的密码必须完全一致
          </div>
        </div>

        <div class="form-actions">
          <el-button
            type="primary"
            size="large"
            class="submit-btn"
            :loading="loading"
            @click="handleSubmit"
          >
            设置新密码并重新登录
          </el-button>
          <el-button
            size="default"
            class="logout-btn"
            @click="handleLogout"
          >
            退出当前账号并返回登录
          </el-button>
        </div>
      </el-form>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Lock, Key, Check, Close } from '@element-plus/icons-vue'
import apiClient from '../../api/client'
import { useUserStore } from '../../stores/user'

const router = useRouter()
const userStore = useUserStore()
const formRef = ref()
const loading = ref(false)

const form = reactive({
  new_password: '',
  confirm_password: ''
})

const roleTagType = computed(() => {
  if (userStore.user?.role === 'ADMIN') return 'danger'
  if (userStore.user?.role === 'ENGINEER') return 'primary'
  return 'success'
})

const roleText = computed(() => {
  if (userStore.user?.role === 'ADMIN') return '系统管理员'
  if (userStore.user?.role === 'ENGINEER') return '主管工程师'
  return '维保技术员'
})

const validatePass = (_rule: any, value: string, callback: any) => {
  if (!value) {
    callback(new Error('请输入新密码'))
  } else if (value.length < 6) {
    callback(new Error('新密码长度不能少于 6 位'))
  } else if (value === 'password123') {
    callback(new Error('新密码不能与出厂初始密码相同，请更换更安全的密码'))
  } else {
    if (form.confirm_password) {
      formRef.value?.validateField('confirm_password')
    }
    callback()
  }
}

const validateConfirmPass = (_rule: any, value: string, callback: any) => {
  if (!value) {
    callback(new Error('请再次输入新密码'))
  } else if (value !== form.new_password) {
    callback(new Error('两次输入的新密码不一致'))
  } else {
    callback()
  }
}

const rules = {
  new_password: [{ validator: validatePass, trigger: 'blur' }],
  confirm_password: [{ validator: validateConfirmPass, trigger: 'blur' }]
}

async function handleSubmit() {
  if (!formRef.value) return
  await formRef.value.validate(async (valid: boolean) => {
    if (!valid) return
    loading.value = true
    try {
      await apiClient.post('/auth/change-password', {
        new_password: form.new_password
      })

      // 安全合规准则：修改密码成功后强制登出并清空会话凭据，要求使用新密码重新登录
      userStore.logout()

      ElMessage.success('新密码设置成功！为保障系统安全，请使用新密码重新登录。')
      router.push('/login')
    } catch (e) {
      // 错误由客户端统一拦截
    } finally {
      loading.value = false
    }
  })
}

function handleLogout() {
  userStore.logout()
  ElMessage.info('已安全退出账号')
  router.push('/login')
}
</script>

<style scoped>
.force-pwd-wrapper {
  height: 100vh;
  width: 100vw;
  background: radial-gradient(circle at 50% 20%, #1e293b 0%, #0f172a 60%, #020617 100%);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px;
  box-sizing: border-box;
}

.force-pwd-card {
  width: 520px;
  max-width: 95vw;
  background: #ffffff;
  border-radius: 16px;
  padding: 36px 40px;
  box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.5), 0 0 0 1px rgba(255, 255, 255, 0.1);
}

.security-badge-container {
  text-align: center;
  margin-bottom: 24px;
}

.security-shield-icon {
  width: 64px;
  height: 64px;
  margin: 0 auto 14px;
  background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%);
  color: #ffffff;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 10px 15px -3px rgba(217, 119, 6, 0.3);
}

.title {
  font-size: 22px;
  font-weight: 700;
  color: #0f172a;
  margin: 0 0 6px 0;
}

.subtitle {
  font-size: 13px;
  color: #64748b;
  margin: 0;
}

.user-profile-strip {
  background-color: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  padding: 12px 16px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 18px;
  font-size: 13px;
}

.profile-item {
  display: flex;
  align-items: center;
  gap: 4px;
}

.profile-item .label {
  color: #64748b;
}

.profile-item .val {
  color: #1e293b;
}

.font-bold {
  font-weight: 600;
}

.font-mono {
  font-family: monospace;
}

.mb-4 {
  margin-bottom: 18px;
}

.pwd-form {
  margin-top: 10px;
}

.security-hints {
  background-color: #f1f5f9;
  border-radius: 8px;
  padding: 12px 16px;
  margin: 12px 0 24px 0;
  font-size: 12px;
}

.hint-title {
  color: #475569;
  font-weight: 600;
  margin-bottom: 6px;
}

.hint-item {
  display: flex;
  align-items: center;
  gap: 6px;
  color: #94a3b8;
  line-height: 1.8;
  transition: color 0.2s ease;
}

.hint-item.pass {
  color: #16a34a;
  font-weight: 500;
}

.form-actions {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.submit-btn {
  width: 100%;
  font-weight: 600;
  height: 44px;
  font-size: 15px;
}

.logout-btn {
  width: 100%;
  color: #64748b;
}
</style>
