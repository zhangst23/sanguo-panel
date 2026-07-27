import request from '../utils/request'

// WordPress Runtime Observability 数据层
// 对应后端 /api/v1/monitor/wp-runtime
export function getWpRuntime() {
  return request.get('/monitor/wp-runtime')
}

export function applyWpOptimize(action) {
  return request.post('/monitor/wp-runtime/optimize', { action })
}
