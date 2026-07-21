<template>
  <router-view />
</template>

<script setup>
import { onMounted } from 'vue'

onMounted(() => {
  const theme = localStorage.getItem('theme') || 'dark'
  if (theme === 'dark') {
    document.body.setAttribute('arco-theme', 'dark')
    document.documentElement.setAttribute('arco-theme', 'dark')
  } else {
    document.body.removeAttribute('arco-theme')
    document.documentElement.removeAttribute('arco-theme')
  }
})
</script>

<style>
/* Global styles already in global.scss */
</style>
