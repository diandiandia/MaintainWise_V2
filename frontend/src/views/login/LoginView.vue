<template>
  <div class="login-wrapper">
    <div class="login-box">
      <div class="header-section">
        <h2 class="title">MaintainWise 2.0</h2>
        <p class="subtitle">智能工厂设备在线化便利系统</p>
      </div>

      <el-form :model="form" :rules="rules" ref="formRef" class="login-form">
        <el-form-item prop="username">
          <el-input v-model="form.username" placeholder="工号 / 用户名" size="large" :prefix-icon="User" />
        </el-form-item>
        <el-form-item prop="password">
          <el-input v-model="form.password" type="password" placeholder="登录密码" size="large" :prefix-icon="Lock" show-password @keyup.enter="handleLogin" />
        </el-form-item>
        <el-button type="primary" size="large" class="submit-btn" :loading="loading" @click="handleLogin">
          登 录
        </el-button>
      </el-form>

      <div class="quick-roles">
        <div class="quick-title">快速体验账号切换：</div>
        <div class="role-btns">
          <el-button size="small" type="danger" plain @click="fillAccount('admin', 'password123')">管理员 (admin)</el-button>
          <el-button size="small" type="primary" plain @click="fillAccount('engineer1', 'password123')">工程师 (engineer1)</el-button>
          <el-button size="small" type="success" plain @click="fillAccount('tech1', 'password123')">技术员 (tech1)</el-button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { User, Lock } from '@element-plus/icons-vue'
import apiClient from '../../api/client'
import { useUserStore } from '../../stores/user'

const router = useRouter()
const userStore = useUserStore()
const formRef = ref()
const loading = ref(false)

const form = reactive({
  username: '',
  password: ''
})

const rules = {
  username: [{ required: true, message: '请输入工号或用户名', trigger: 'blur' }],
  password: [{ required: true, message: '请输入登录密码', trigger: 'blur' }]
}

function fillAccount(u: string, p: string) {
  form.username = u
  form.password = p
}

async function handleLogin() {
  if (!formRef.value) return
  await formRef.value.validate(async (valid: boolean) => {
    if (!valid) return
    loading.value = true
    try {
      const formData = new URLSearchParams()
      formData.append('username', form.username)
      formData.append('password', form.password)

      const res = await apiClient.post('/auth/login', formData, {
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' }
      })

      const { access_token, user, password_expiring_soon, days_remaining } = res.data
      user.password_expiring_soon = password_expiring_soon
      user.days_remaining = days_remaining
      userStore.setLogin(access_token, user)
      ElMessage.success(`欢迎回来，${user.full_name}`)
      router.push('/dashboard')
    } catch (e) {
      // 错误已被拦截器提示
    } finally {
      loading.value = false
    }
  })
}
</script>

<style scoped>
.login-wrapper {
  height: 100vh;
  width: 100vw;
  background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
  display: flex;
  align-items: center;
  justify-content: center;
}
.login-box {
  width: 420px;
  background: #ffffff;
  border-radius: 12px;
  padding: 40px;
  box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.3);
}
.header-section {
  text-align: center;
  margin-bottom: 30px;
}
.title {
  font-size: 26px;
  color: #0f172a;
  margin-bottom: 8px;
}
.subtitle {
  font-size: 14px;
  color: #64748b;
}
.submit-btn {
  width: 100%;
  margin-top: 10px;
  font-weight: 600;
}
.quick-roles {
  margin-top: 30px;
  border-top: 1px dashed #e2e8f0;
  padding-top: 20px;
}
.quick-title {
  font-size: 12px;
  color: #94a3b8;
  margin-bottom: 10px;
  text-align: center;
}
.role-btns {
  display: flex;
  justify-content: space-between;
}
</style>
