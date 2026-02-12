<template>
  <div class="security-container">
    <a-typography-title :heading="2">Security Management</a-typography-title>
    
    <a-row :gutter="20">
      <!-- Change Password -->
      <a-col :span="12">
        <a-card title="Change Administrator Password">
          <a-form :model="passwordForm" @submit="handlePasswordChange">
            <a-form-item field="old_password" label="Old Password" required>
              <a-input-password v-model="passwordForm.old_password" />
            </a-form-item>
            <a-form-item field="new_password" label="New Password" required>
              <a-input-password v-model="passwordForm.new_password" />
            </a-form-item>
            <a-form-item field="confirm_password" label="Confirm Password" required>
              <a-input-password v-model="passwordForm.confirm_password" />
            </a-form-item>
            <a-form-item>
              <a-button type="primary" html-type="submit" :loading="loading.password">Update Password</a-button>
            </a-form-item>
          </a-form>
        </a-card>
      </a-col>

      <!-- Security Settings -->
      <a-col :span="12">
        <a-card title="Panel Security Settings">
          <a-space direction="vertical" fill>
            <div class="setting-item">
              <span>JWT Token Expiry (Minutes)</span>
              <a-input-number v-model="securitySettings.tokenExpiry" :style="{width: '120px'}" />
            </div>
            <div class="setting-item">
              <span>Two-Factor Authentication</span>
              <a-switch v-model="securitySettings.twoFactor" />
            </div>
            <div class="setting-item">
              <span>Login IP Whitelist</span>
              <a-input v-model="securitySettings.ipWhitelist" placeholder="e.g. 192.168.1.1, 10.0.0.0/24" />
            </div>
            <a-button type="outline" long @click="saveSettings" :loading="loading.settings">Save Security Settings</a-button>
          </a-space>
        </a-card>
      </a-col>
    </a-row>
  </div>
</template>

<script setup>
import { reactive } from 'vue'
import { Message } from '@arco-design/web-vue'

const loading = reactive({
  password: false,
  settings: false
})

const passwordForm = reactive({
  old_password: '',
  new_password: '',
  confirm_password: ''
})

const securitySettings = reactive({
  tokenExpiry: 1440,
  twoFactor: false,
  ipWhitelist: ''
})

const handlePasswordChange = async () => {
  if (passwordForm.new_password !== passwordForm.confirm_password) {
    Message.error('New passwords do not match')
    return
  }
  loading.password = true
  try {
    // Mock password change
    await new Promise(resolve => setTimeout(resolve, 1000))
    Message.success('Password updated successfully')
    passwordForm.old_password = ''
    passwordForm.new_password = ''
    passwordForm.confirm_password = ''
  } catch (error) {
    console.error(error)
  } finally {
    loading.password = false
  }
}

const saveSettings = async () => {
  loading.settings = true
  try {
    // Mock settings save
    await new Promise(resolve => setTimeout(resolve, 1000))
    Message.success('Security settings saved')
  } catch (error) {
    console.error(error)
  } finally {
    loading.settings = false
  }
}
</script>

<style scoped>
.setting-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}
</style>
