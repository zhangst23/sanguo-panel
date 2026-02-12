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
    Message.error(response?.data?.detail || 'Request Error')
    return Promise.reject(error)
  }
)

export default service
