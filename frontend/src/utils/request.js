import axios from 'axios'
import { Message } from '@arco-design/web-vue'

const service = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '/api/v1',
  timeout: 10000,
})

// Request interceptor
service.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token')
    if (token) {
      config.headers['Authorization'] = `Bearer ${token}`
    }
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// Response interceptor
service.interceptors.response.use(
  (response) => {
    return response.data
  },
  (error) => {
    const { response } = error
    if (response && response.status === 401) {
      localStorage.removeItem('token')
      window.location.href = '/login'
    }
    // 允许调用方静默处理错误（例如带本地缓存的状态检测请求）
    if (!error.config?.silent) {
      Message.error(response?.data?.detail || 'Request Error')
    }
    return Promise.reject(error)
  }
)

export default service
