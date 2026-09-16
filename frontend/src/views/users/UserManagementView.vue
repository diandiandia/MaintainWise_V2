<template>
  <div class="users-page">
    <el-card shadow="hover">
      <div class="toolbar">
        <el-input
          v-model="search"
          placeholder="搜索姓名 / 工号 / 账号..."
          clearable
          style="width: 300px;"
          @keyup.enter="fetchUsers"
          @clear="fetchUsers"
        >
          <template #append>
            <el-button @click="fetchUsers">搜索</el-button>
          </template>
        </el-input>
        <el-button type="primary" @click="openCreateDialog">+ 录入新员工账号</el-button>
      </div>

      <el-table :data="users" v-loading="loading" style="width: 100%; margin-top: 15px;" stripe>
        <el-table-column prop="employee_no" label="员工工号" width="130" />
        <el-table-column prop="full_name" label="真实姓名" width="140">
          <template #default="{ row }">
            <strong>{{ row.full_name }}</strong>
          </template>
        </el-table-column>
        <el-table-column prop="username" label="登录账号" width="140" />
        <el-table-column label="系统角色" width="140" align="center">
          <template #default="{ row }">
            <el-tag :type="getRoleTagType(row.role)">{{ getRoleText(row.role) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="phone" label="联系手机" width="140" />
        <el-table-column prop="email" label="电子邮箱" min-width="170">
          <template #default="{ row }">
            <span>{{ row.email || '-' }}</span>
          </template>
        </el-table-column>
        <el-table-column label="状态 / 安全" width="130" align="center">
          <template #default="{ row }">
            <div style="display: flex; flex-direction: column; align-items: center; gap: 4px;">
              <el-tag v-if="row.is_frozen" type="danger" effect="dark" size="small">已锁定冻结</el-tag>
              <el-tag v-else :type="row.is_active ? 'success' : 'info'" size="small">
                {{ row.is_active ? '正常运行' : '已停用' }}
              </el-tag>
              <el-tag v-if="row.must_change_password" type="warning" size="small">需改初始密</el-tag>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="230" align="center" fixed="right">
          <template #default="{ row }">
            <el-button v-if="row.is_frozen" link type="warning" size="small" @click="handleUnfreeze(row)">
              🔓 解冻
            </el-button>
            <el-button link type="primary" size="small" @click="openResetDialog(row)">重置密码</el-button>
            <el-button v-if="row.is_active && row.username !== 'admin'" link type="danger" size="small" @click="handleDisable(row)">
              停用账号
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 新建人员对话框 -->
    <el-dialog v-model="createVisible" title="录入全厂员工账号" width="520px">
      <el-form :model="createForm" :rules="createRules" ref="createFormRef" label-width="90px">
        <el-form-item label="员工工号" prop="employee_no">
          <el-input v-model="createForm.employee_no" placeholder="如: EMP008" />
        </el-form-item>
        <el-form-item label="真实姓名" prop="full_name">
          <el-input v-model="createForm.full_name" placeholder="员工姓名" />
        </el-form-item>
        <el-form-item label="登录账号" prop="username">
          <el-input v-model="createForm.username" placeholder="系统唯一登录名" />
        </el-form-item>
        <el-form-item label="初始密码" prop="password">
          <el-input v-model="createForm.password" type="password" placeholder="至少6位" show-password />
        </el-form-item>
        <el-form-item label="分配角色" prop="role">
          <el-select v-model="createForm.role" style="width: 100%;">
            <el-option label="系统管理员 (ADMIN)" value="ADMIN" />
            <el-option label="主管工程师 (ENGINEER)" value="ENGINEER" />
            <el-option label="维保技术员 (TECHNICIAN)" value="TECHNICIAN" />
          </el-select>
        </el-form-item>
        <el-form-item label="电子邮箱" prop="email">
          <el-input v-model="createForm.email" placeholder="接收派单邮件与到期预警，如 engineer@factory.com" />
        </el-form-item>
        <el-form-item label="手机号码">
          <el-input v-model="createForm.phone" placeholder="选填" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="createVisible = false">取消</el-button>
        <el-button type="primary" :loading="createLoading" @click="submitCreate">确认录入</el-button>
      </template>
    </el-dialog>

    <!-- 重置密码对话框 -->
    <el-dialog v-model="resetVisible" title="管理员一键重置密码" width="400px">
      <div v-if="selectedUser" style="margin-bottom: 15px;">
        为员工 <strong>{{ selectedUser.full_name }} ({{ selectedUser.username }})</strong> 重置登录密码：
      </div>
      <el-form label-width="90px">
        <el-form-item label="新密码" required>
          <el-input v-model="newPassword" placeholder="输入新密码 (至少6位)" show-password />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="resetVisible = false">取消</el-button>
        <el-button type="primary" :loading="resetLoading" @click="submitReset">确定重置</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import apiClient from '../../api/client'

const loading = ref(false)
const search = ref('')
const users = ref<any[]>([])

// 创建人员
const createVisible = ref(false)
const createLoading = ref(false)
const createFormRef = ref()
const createForm = reactive({
  employee_no: '',
  full_name: '',
  username: '',
  password: '',
  role: 'TECHNICIAN',
  phone: '',
  email: ''
})
const createRules = {
  employee_no: [{ required: true, message: '工号必填', trigger: 'blur' }],
  full_name: [{ required: true, message: '姓名必填', trigger: 'blur' }],
  username: [{ required: true, message: '登录名必填', trigger: 'blur' }],
  password: [{ required: true, message: '密码必填', trigger: 'blur' }],
  role: [{ required: true, message: '请选择角色', trigger: 'blur' }]
}

// 重置密码
const resetVisible = ref(false)
const resetLoading = ref(false)
const selectedUser = ref<any>(null)
const newPassword = ref('')

async function fetchUsers() {
  loading.value = true
  try {
    const params: any = {}
    if (search.value) params.search = search.value
    const res = await apiClient.get('/users', { params })
    users.value = res.data
  } catch (e) {
  } finally {
    loading.value = false
  }
}

function openCreateDialog() {
  createForm.employee_no = ''
  createForm.full_name = ''
  createForm.username = ''
  createForm.password = 'password123'
  createForm.role = 'TECHNICIAN'
  createForm.phone = ''
  createForm.email = ''
  createVisible.value = true
}

async function submitCreate() {
  if (!createFormRef.value) return
  await createFormRef.value.validate(async (valid: boolean) => {
    if (!valid) return
    createLoading.value = true
    try {
      await apiClient.post('/users', createForm)
      ElMessage.success('人员账号创建成功！')
      createVisible.value = false
      fetchUsers()
    } catch (e) {
    } finally {
      createLoading.value = false
    }
  })
}

function openResetDialog(row: any) {
  selectedUser.value = row
  newPassword.value = 'password123'
  resetVisible.value = true
}

async function submitReset() {
  if (!newPassword.value || newPassword.value.length < 6) {
    ElMessage.warning('密码长度不能少于 6 位')
    return
  }
  resetLoading.value = true
  try {
    await apiClient.put(`/users/${selectedUser.value.id}/reset-password`, { new_password: newPassword.value })
    ElMessage.success('密码已成功重置！')
    resetVisible.value = false
  } catch (e) {
  } finally {
    resetLoading.value = false
  }
}

function handleDisable(row: any) {
  ElMessageBox.confirm(`确定停用账号 [${row.username}] 吗？历史签署的工单与维保单将完整保留`, '停用警告', {
    type: 'warning'
  }).then(async () => {
    await apiClient.delete(`/users/${row.id}`)
    ElMessage.success('账号已停用')
    fetchUsers()
  }).catch(() => {})
}

function handleUnfreeze(row: any) {
  ElMessageBox.confirm(`确定解冻用户 [${row.full_name} (${row.username})] 吗？解冻后员工将恢复登录权限，登录后需遵循密码修改流程。`, '解冻确认', {
    type: 'info'
  }).then(async () => {
    try {
      await apiClient.put(`/users/${row.id}/unfreeze`)
      ElMessage.success(`用户 [${row.full_name}] 已成功解冻！`)
      fetchUsers()
    } catch (e) {}
  }).catch(() => {})
}

function getRoleTagType(role: string) {
  if (role === 'ADMIN') return 'danger'
  if (role === 'ENGINEER') return 'primary'
  return 'success'
}

function getRoleText(role: string) {
  if (role === 'ADMIN') return '系统管理员'
  if (role === 'ENGINEER') return '主管工程师'
  return '维保技术员'
}

onMounted(() => {
  fetchUsers()
})
</script>

<style scoped>
.toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
</style>
