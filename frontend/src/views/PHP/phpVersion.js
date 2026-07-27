import request from '@/utils/request'

// 获取当前默认 PHP 版本（供各子组件复用）
export async function get_default_version() {
  try {
    const versions = await request.get('/php/versions')
    const def = versions.find((v) => v.is_default) || versions.find((v) => v.status === 'installed')
    return def ? def.version : '8.3'
  } catch (e) {
    return '8.3'
  }
}
