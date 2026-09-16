<template>
  <el-container class="layout-container">
    <el-aside width="240px" class="layout-aside">
      <div class="logo-area">
        <el-icon :size="24" color="#409EFF"><Tools /></el-icon>
        <span class="logo-title">MaintainWise 2.0</span>
      </div>
      <el-menu
        :default-active="activeRoute"
        class="aside-menu"
        router
        background-color="#1e222d"
        text-color="#c1c6d0"
        active-text-color="#409eff"
      >
        <el-menu-item index="/dashboard">
          <el-icon><Odometer /></el-icon>
          <span>数据平台</span>
        </el-menu-item>
        <el-menu-item index="/equipments">
          <el-icon><Files /></el-icon>
          <span>设备信息</span>
        </el-menu-item>
        <el-menu-item index="/maintenance">
          <el-icon><Check /></el-icon>
          <span>设备维护</span>
        </el-menu-item>
        <el-menu-item index="/workorders">
          <el-icon><Bell /></el-icon>
          <span>现场维护单</span>
        </el-menu-item>
        <el-menu-item index="/knowledge">
          <el-icon><Reading /></el-icon>
          <span>后来人知识库</span>
        </el-menu-item>
        <el-menu-item index="/system-docs">
          <el-icon><Document /></el-icon>
          <span>设计文档与帮助</span>
        </el-menu-item>
        <el-menu-item v-if="userStore.isAdmin" index="/users">
          <el-icon><User /></el-icon>
          <span>用户管理</span>
        </el-menu-item>
        <el-menu-item v-if="userStore.isAdmin" index="/settings">
          <el-icon><Setting /></el-icon>
          <span>系统设置与热备</span>
        </el-menu-item>
      </el-menu>
    </el-aside>

    <el-container>
      <el-header class="layout-header">
        <div class="header-left">
          <span class="page-title">{{ currentTitle }}</span>
        </div>
        <div class="header-right">
          <!-- 醒目角色徽标 -->
          <el-tag :type="roleTagType" effect="dark" class="role-badge">
            {{ roleText }}
          </el-tag>
          <span class="user-name">{{ userStore.user?.full_name }} ({{ userStore.user?.employee_no }})</span>
          <el-button link type="info" @click="router.push('/system-docs')" style="margin-left: 12px; font-weight: 500;">
            <el-icon style="margin-right: 4px;"><Document /></el-icon>帮助文档
          </el-button>
          <el-button link type="primary" @click="openChangePwdDialog" style="margin-left: 10px;">修改密码</el-button>
          <el-button link type="danger" @click="handleLogout" style="margin-left: 10px;">退出登录</el-button>
        </div>
      </el-header>

      <!-- 180天密码临期预警条 (提前3天) -->
      <div v-if="userStore.user?.password_expiring_soon" class="pwd-warning-banner">
        <el-alert
          type="warning"
          show-icon
          :closable="false"
        >
          <template #title>
            <div style="display: flex; justify-content: space-between; align-items: center;">
              <span>⏰ <strong>密码安全期限预警</strong>：您的登录密码将在 {{ userStore.user?.days_remaining ?? 3 }} 天后到达 180 天上限，请及时修改密码避免账号被系统自动冻结！</span>
              <el-button size="small" type="warning" plain @click="openChangePwdDialog">立即修改密码 &gt;</el-button>
            </div>
          </template>
        </el-alert>
      </div>

      <el-main class="layout-main">
        <router-view />
      </el-main>
    </el-container>

    <!-- 自主修改密码对话框 -->
    <el-dialog v-model="changePwdDialogVisible" title="个人登录密码修改" width="460px">
      <el-form :model="changePwdForm" label-width="90px">
        <el-form-item label="当前旧密码">
          <el-input v-model="changePwdForm.old_password" type="password" placeholder="输入当前旧密码" show-password />
        </el-form-item>
        <el-form-item label="设置新密码" required>
          <el-input v-model="changePwdForm.new_password" type="password" placeholder="至少 6 位新密码" show-password />
        </el-form-item>
        <el-form-item label="确认新密码" required>
          <el-input v-model="changePwdForm.confirm_password" type="password" placeholder="再次输入新密码" show-password />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="changePwdDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="changePwdLoading" @click="submitChangePassword">确认更新密码</el-button>
      </template>
    </el-dialog>
  </el-container>
</template>

<script setup lang="ts">
import { computed, ref, reactive } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useUserStore } from '../stores/user'
import { ElMessage } from 'element-plus'
import apiClient from '../api/client'
import { Tools, Odometer, Files, Check, Bell, Reading, User, Setting, Document } from '@element-plus/icons-vue'

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()

const activeRoute = computed(() => route.path)
const currentTitle = computed(() => (route.meta.title as string) || '数据平台')

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

// 用户主动改密
const changePwdDialogVisible = ref(false)
const changePwdLoading = ref(false)
const changePwdForm = reactive({
  old_password: '',
  new_password: '',
  confirm_password: ''
})

function openChangePwdDialog() {
  changePwdForm.old_password = ''
  changePwdForm.new_password = ''
  changePwdForm.confirm_password = ''
  changePwdDialogVisible.value = true
}

async function submitChangePassword() {
  if (!changePwdForm.new_password || changePwdForm.new_password.length < 6) {
    ElMessage.warning('新密码长度不能少于 6 位')
    return
  }
  if (changePwdForm.new_password !== changePwdForm.confirm_password) {
    ElMessage.warning('两次输入的新密码不一致')
    return
  }
  changePwdLoading.value = true
  try {
    await apiClient.post('/auth/change-password', {
      old_password: changePwdForm.old_password,
      new_password: changePwdForm.new_password
    })
    ElMessage.success('密码修改成功！为保障系统安全，请使用新密码重新登录。')
    changePwdDialogVisible.value = false
    handleLogout()
  } catch (e) {
  } finally {
    changePwdLoading.value = false
  }
}

function handleLogout() {
  userStore.logout()
  router.push('/login')
}
</script>

<style scoped>
.layout-container {
  height: 100vh;
  width: 100vw;
}
.pwd-warning-banner {
  padding: 8px 24px 0 24px;
}
.layout-aside {
  background-color: #1e222d;
  display: flex;
  flex-direction: column;
}
.logo-area {
  height: 60px;
  display: flex;
  align-items: center;
  gap: 10px;
  padding-left: 20px;
  background-color: #161922;
}
.logo-title {
  color: #ffffff;
  font-weight: bold;
  font-size: 16px;
}
.aside-menu {
  border-right: none;
  flex: 1;
}
.layout-header {
  height: 60px;
  background-color: #ffffff;
  border-bottom: 1px solid #e2e8f0;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px;
}
.page-title {
  font-size: 18px;
  font-weight: 600;
  color: #1e293b;
}
.header-right {
  display: flex;
  align-items: center;
}
.role-badge {
  font-weight: bold;
  margin-right: 12px;
}
.user-name {
  font-size: 14px;
  color: #475569;
}
.layout-main {
  background-color: #f8fafc;
  padding: 20px;
  overflow-y: auto;
}
</style>
