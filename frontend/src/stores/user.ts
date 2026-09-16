import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

export interface UserInfo {
  id: number
  username: string
  full_name: string
  employee_no: string
  role: 'ADMIN' | 'ENGINEER' | 'TECHNICIAN'
  phone?: string
  email?: string
  must_change_password?: boolean
  is_frozen?: boolean
  password_expiring_soon?: boolean
  days_remaining?: number
}

export const useUserStore = defineStore('user', () => {
  const token = ref<string | null>(localStorage.getItem('maintainwise_token'))
  const userStr = localStorage.getItem('maintainwise_user')
  const user = ref<UserInfo | null>(userStr ? JSON.parse(userStr) : null)

  const isAuthenticated = computed(() => !!token.value)
  const role = computed(() => user.value?.role || '')
  const isAdmin = computed(() => role.value === 'ADMIN')
  const isEngineer = computed(() => role.value === 'ENGINEER' || role.value === 'ADMIN')
  const isTechnician = computed(() => role.value === 'TECHNICIAN')

  function setLogin(newToken: string, newUser: UserInfo) {
    token.value = newToken
    user.value = newUser
    localStorage.setItem('maintainwise_token', newToken)
    localStorage.setItem('maintainwise_user', JSON.stringify(newUser))
  }

  function logout() {
    token.value = null
    user.value = null
    localStorage.removeItem('maintainwise_token')
    localStorage.removeItem('maintainwise_user')
  }

  return {
    token,
    user,
    isAuthenticated,
    role,
    isAdmin,
    isEngineer,
    isTechnician,
    setLogin,
    logout
  }
})
