<template>
  <div class="about-container">
    <a-card :bordered="false" class="about-hero">
      <div class="about-brand">
        <div>
          <a-typography-title :heading="2" :style="{ margin: 0 }">三国面板</a-typography-title>
          <div class="about-subtitle">Sanguo Panel · 开源主机控制面板</div>
        </div>
      </div>
      <p class="about-intro">
        三国面板是一套基于 OpenLiteSpeed 的轻量级主机控制面板，用于在一台服务器上管理 WordPress
        站点、数据库、缓存、SSL、备份与系统服务。前端为 Vue 3 + Vite + Arco Design，后端为
        FastAPI + SQLAlchemy，面板与 API 由同一个系统服务提供。
      </p>
      <a-space wrap>
        <a-button type="primary" @click="openLink('https://github.com/zhangst23/sanguo-panel')">
          <template #icon><icon-link /></template>
          GitHub 仓库
        </a-button>
        <a-button @click="openLink('/api-docs')">
          <template #icon><icon-file /></template>
          API 接口文档
        </a-button>
      </a-space>
    </a-card>

    <a-row :gutter="16" class="about-grid">
      <a-col :span="12">
        <a-card title="技术栈" :bordered="false">
          <a-descriptions :column="1" size="small">
            <a-descriptions-item label="Web 服务器">OpenLiteSpeed（Panel80 / Panel443 监听器）</a-descriptions-item>
            <a-descriptions-item label="PHP">LSAPI（lsphp 8.3 / 8.2 / 8.1 / 7.4）</a-descriptions-item>
            <a-descriptions-item label="后端">FastAPI + SQLAlchemy + SQLite</a-descriptions-item>
            <a-descriptions-item label="前端">Vue 3 + Vite + Arco Design + ECharts</a-descriptions-item>
            <a-descriptions-item label="数据库">MariaDB（每个站点独立库/用户）</a-descriptions-item>
            <a-descriptions-item label="缓存">Redis / LiteSpeed Cache</a-descriptions-item>
          </a-descriptions>
        </a-card>
      </a-col>
      <a-col :span="12">
        <a-card title="主要功能" :bordered="false">
          <a-list :bordered="false" size="small">
            <a-list-item>一键创建 WordPress 站点，自动配置数据库与 OLS 虚拟主机</a-list-item>
            <a-list-item>站点别名、PHP 版本切换、伪静态与 SSL 证书管理</a-list-item>
            <a-list-item>数据库、文件管理、phpMyAdmin 与备份/迁移</a-list-item>
            <a-list-item>系统信息、服务状态、监控中心与运行时可观测性</a-list-item>
            <a-list-item>安全防御、任务队列与面板在线更新</a-list-item>
          </a-list>
        </a-card>
      </a-col>
    </a-row>

    <a-card title="开源信息" :bordered="false" class="about-grid">
      <a-descriptions :column="1" size="small">
        <a-descriptions-item label="仓库地址">
          <a-link href="https://github.com/zhangst23/sanguo-panel" target="_blank">
            https://github.com/zhangst23/sanguo-panel
          </a-link>
        </a-descriptions-item>
        <a-descriptions-item label="问题反馈">
          可在仓库 Issues 中提交 Bug 与功能建议
        </a-descriptions-item>
      </a-descriptions>
    </a-card>
  </div>
</template>

<script setup>
import { IconLink, IconFile } from '@arco-design/web-vue/es/icon'

const openLink = (url) => {
  window.open(url, '_blank')
}
</script>

<style scoped>
.about-container {
  padding: 0;
}
.about-hero {
  margin-bottom: 16px;
}
.about-brand {
  margin-bottom: 16px;
}
.about-subtitle {
  margin-top: 4px;
  color: var(--color-text-3);
  font-size: 14px;
}
.about-intro {
  line-height: 1.8;
  margin: 0 0 16px;
}
.about-grid {
  margin-bottom: 16px;
}
</style>
