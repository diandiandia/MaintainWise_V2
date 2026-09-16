import axios from 'axios'
import { ElMessage } from 'element-plus'

const apiClient = axios.create({
  baseURL: '/api/v1',
  timeout: 15000
})

apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem('maintainwise_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
}, (error) => {
  return Promise.reject(error)
})

apiClient.interceptors.response.use((response) => {
  return response
}, (error) => {
  const status = error.response ? error.response.status : null
  const detail = error.response?.data?.detail || error.message
  
  if (status === 401) {
    localStorage.removeItem('maintainwise_token')
    localStorage.removeItem('maintainwise_user')
    if (window.location.pathname !== '/login') {
      ElMessage.warning('会话已过期，请重新登录')
      window.location.href = '/login'
    }
  } else if (status === 403) {
    ElMessage.error(detail || '权限不足，禁止操作')
  } else if (status >= 400 && status < 500) {
    ElMessage.error(detail || '请求错误')
  } else if (status >= 500) {
    ElMessage.error('服务器内部错误，请检查后台日志')
  }
  return Promise.reject(error)
})

export default apiClient
