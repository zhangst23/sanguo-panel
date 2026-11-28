<template>
    <div class="wp-assets-page">
        <a-card class="library-card">
            <a-tabs v-model:active-key="activeTab">
                <a-tab-pane key="speedTools" title="WP一键提速">
                    <QuickSpeedTools />
                </a-tab-pane>

                <a-tab-pane key="hardening" title="WP安全加固">
                    <WordPressHardening />
                </a-tab-pane>

                <a-tab-pane key="core" title="WP 版本">
                    <div class="toolbar">
                        <a-button type="primary" @click="openFetchModal"
                            >拉取新版本</a-button
                        >
                        <a-button @click="openUpload('core')"
                            >上传本地核心包</a-button
                        >
                    </div>
                    <a-table
                        :columns="coreColumns"
                        :data="coreAssets"
                        :loading="loading"
                        :pagination="false"
                        row-key="id"
                    >
                        <template #version="{ record }">
                            <a-tag color="blue">{{
                                record.version || "-"
                            }}</a-tag>
                        </template>
                        <template #source="{ record }">
                            {{
                                record.source === "official"
                                    ? "官网下载"
                                    : "本地上传"
                            }}
                        </template>
                        <template #size="{ record }">{{
                            formatSize(record.file_size)
                        }}</template>
                        <template #is_default="{ record }">
                            <a-tag v-if="record.is_default" color="green"
                                >默认</a-tag
                            >
                            <span v-else>-</span>
                        </template>
                        <template #actions="{ record }">
                            <a-button
                                type="text"
                                size="small"
                                :disabled="record.is_default"
                                @click="handleSetDefault(record)"
                            >
                                设为默认
                            </a-button>
                            <a-popconfirm
                                content="确定删除该版本包吗？"
                                type="warning"
                                @ok="handleDelete(record)"
                            >
                                <a-button
                                    type="text"
                                    size="small"
                                    status="danger"
                                    >删除</a-button
                                >
                            </a-popconfirm>
                        </template>
                    </a-table>
                </a-tab-pane>

                <a-tab-pane key="theme" title="主题管理">
                    <div class="toolbar">
                        <a-button type="primary" @click="openUpload('theme')"
                            >上传主题包</a-button
                        >
                        <a-button @click="openCliInstall('theme')"
                            >WP CLI 安装主题</a-button
                        >
                        <span class="toolbar-hint"
                            >设为默认的主题会在新建站点时自动安装并启用</span
                        >
                    </div>
                    <a-table
                        :columns="resourceColumns"
                        :data="themeAssets"
                        :loading="loading"
                        :pagination="false"
                        row-key="id"
                    >
                        <template #version="{ record }">{{
                            record.version || "-"
                        }}</template>
                        <template #source="{ record }">{{
                            record.source === "official"
                                ? "官网下载"
                                : "本地上传"
                        }}</template>
                        <template #size="{ record }">{{
                            formatSize(record.file_size)
                        }}</template>
                        <template #enabled="{ record }">
                            <a-switch
                                v-model="record.enabled"
                                size="small"
                                @change="(val) => handleToggle(record, val)"
                            />
                        </template>
                        <template #is_default="{ record }">
                            <a-tag v-if="record.is_default" color="green"
                                >默认</a-tag
                            >
                            <span v-else>-</span>
                        </template>
                        <template #actions="{ record }">
                            <a-button
                                type="text"
                                size="small"
                                @click="openEdit(record)"
                                >编辑</a-button
                            >
                            <a-button
                                type="text"
                                size="small"
                                :disabled="record.is_default"
                                @click="handleSetDefault(record)"
                            >
                                设为默认
                            </a-button>
                            <a-popconfirm
                                content="确定删除该主题包吗？"
                                type="warning"
                                @ok="handleDelete(record)"
                            >
                                <a-button
                                    type="text"
                                    size="small"
                                    status="danger"
                                    >删除</a-button
                                >
                            </a-popconfirm>
                        </template>
                    </a-table>
                </a-tab-pane>

                <a-tab-pane key="plugin" title="插件管理">
                    <div class="toolbar">
                        <a-button type="primary" @click="openUpload('plugin')"
                            >上传插件包</a-button
                        >
                        <a-button @click="openCliInstall('plugin')"
                            >WP CLI 安装插件</a-button
                        >
                        <span class="toolbar-hint"
                            >设为默认的插件会在新建站点时自动安装并启用</span
                        >
                    </div>
                    <a-table
                        :columns="resourceColumns"
                        :data="pluginAssets"
                        :loading="loading"
                        :pagination="false"
                        row-key="id"
                    >
                        <template #version="{ record }">{{
                            record.version || "-"
                        }}</template>
                        <template #source="{ record }">{{
                            record.source === "official"
                                ? "官网下载"
                                : "本地上传"
                        }}</template>
                        <template #size="{ record }">{{
                            formatSize(record.file_size)
                        }}</template>
                        <template #enabled="{ record }">
                            <a-switch
                                v-model="record.enabled"
                                size="small"
                                @change="(val) => handleToggle(record, val)"
                            />
                        </template>
                        <template #is_default="{ record }">
                            <a-tag v-if="record.is_default" color="green"
                                >默认</a-tag
                            >
                            <span v-else>-</span>
                        </template>
                        <template #actions="{ record }">
                            <a-button
                                type="text"
                                size="small"
                                @click="openEdit(record)"
                                >编辑</a-button
                            >
                            <a-button
                                type="text"
                                size="small"
                                :disabled="record.is_default"
                                @click="handleSetDefault(record)"
                            >
                                设为默认
                            </a-button>
                            <a-popconfirm
                                content="确定删除该插件包吗？"
                                type="warning"
                                @ok="handleDelete(record)"
                            >
                                <a-button
                                    type="text"
                                    size="small"
                                    status="danger"
                                    >删除</a-button
                                >
                            </a-popconfirm>
                        </template>
                    </a-table>
                </a-tab-pane>
            </a-tabs>
        </a-card>

        <a-modal
            v-model:visible="fetchVisible"
            title="从官网拉取 WordPress 版本"
            @ok="handleFetch"
            :confirm-loading="fetching"
        >
            <a-form layout="vertical">
                <a-form-item
                    label="版本号"
                    required
                    help="例如 6.5.5，仅允许数字版本"
                >
                    <a-input v-model="fetchVersion" placeholder="6.5.5" />
                </a-form-item>
            </a-form>
        </a-modal>

        <a-modal
            v-model:visible="cliVisible"
            :title="cliTitle"
            ok-text="安装"
            @ok="handleCliInstall"
            :confirm-loading="cliInstalling"
            :closable="!cliInstalling"
            :mask-closable="false"
        >
            <a-form layout="vertical">
                <a-form-item
                    :label="
                        cliKind === 'theme'
                            ? '主题名称 / slug'
                            : '插件名称 / slug'
                    "
                    required
                    help="输入 WordPress 官方目录中的名称或 slug，例如：hello-dolly、woocommerce"
                >
                    <a-input
                        v-model="cliInput"
                        placeholder="请输入名称或 slug"
                        allow-clear
                        @press-enter="handleCliInstall"
                    />
                </a-form-item>
            </a-form>
            <div class="cli-hint">
                面板将通过 WP-CLI
                下载该资源并加入本地资源库，可用于新建站点时自动安装。
            </div>
        </a-modal>

        <a-modal
            v-model:visible="uploadVisible"
            :title="uploadTitle"
            ok-text="上传"
            :on-before-ok="handleUpload"
            :confirm-loading="uploading"
            @ok="resetUploadState"
            @cancel="resetUploadState"
            :closable="!uploading"
            :mask-closable="false"
        >
            <a-form layout="vertical">
                <a-form-item label="zip 包" required>
                    <a-upload
                        :custom-request="handlePickFile"
                        accept=".zip"
                        :show-file-list="false"
                    >
                        <template #upload-button>
                            <a-button>选择 zip 文件</a-button>
                        </template>
                    </a-upload>
                    <div v-if="uploadFile" class="upload-status">
                        <div class="file-name">{{ uploadFile.name }}</div>
                        <a-progress
                            :percent="uploadPercent"
                            :status="
                                uploadStatus === 'done'
                                    ? 'success'
                                    : uploadStatus === 'error'
                                      ? 'error'
                                      : 'normal'
                            "
                            size="small"
                        />
                        <div
                            v-if="uploadStatus === 'uploading'"
                            class="status-hint"
                        >
                            上传中 {{ uploadPercent }}%
                        </div>
                        <div
                            v-else-if="uploadStatus === 'done'"
                            class="status-hint status-done"
                        >
                            ✓ 上传完成，资源已加入资源库
                        </div>
                        <div
                            v-else-if="uploadStatus === 'error'"
                            class="status-hint status-error"
                        >
                            上传失败：{{ uploadError }}
                        </div>
                    </div>
                </a-form-item>
                <a-form-item label="名称">
                    <a-input
                        v-model="uploadForm.name"
                        placeholder="默认取文件名，可修改"
                    />
                </a-form-item>
                <a-form-item
                    v-if="uploadForm.kind !== 'core'"
                    label="标识 (slug)"
                >
                    <a-input
                        v-model="uploadForm.slug"
                        placeholder="默认取文件名，可修改"
                    />
                </a-form-item>
                <a-form-item
                    v-if="uploadForm.kind === 'core'"
                    label="版本号"
                    required
                >
                    <a-input
                        v-model="uploadForm.version"
                        placeholder="例如 6.5.5"
                    />
                </a-form-item>
            </a-form>
        </a-modal>

        <a-modal
            v-model:visible="editVisible"
            title="编辑资源信息"
            @ok="handleSaveEdit"
            :confirm-loading="saving"
        >
            <a-form layout="vertical">
                <a-form-item label="名称"
                    ><a-input v-model="editForm.name"
                /></a-form-item>
                <a-form-item v-if="editForm.kind !== 'core'" label="标识 (slug)"
                    ><a-input v-model="editForm.slug"
                /></a-form-item>
                <a-form-item label="版本号"
                    ><a-input v-model="editForm.version"
                /></a-form-item>
                <a-form-item label="启用"
                    ><a-switch v-model="editForm.enabled"
                /></a-form-item>
            </a-form>
        </a-modal>
    </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from "vue";
import request from "@/utils/request";
import { Message } from "@arco-design/web-vue";
import QuickSpeedTools from "@/views/Tools/QuickSpeedTools.vue";
import WordPressHardening from "@/views/Security/WordPressHardening.vue";

const loading = ref(false);
const assets = ref([]);
const defaults = reactive({
    default_version: "6.5.5",
    versions: [],
    default_themes: [],
    default_plugins: [],
});
const activeTab = ref("speedTools");

const fetchVisible = ref(false);
const fetchVersion = ref("");
const fetching = ref(false);

// WP CLI 按名称安装主题 / 插件
const cliVisible = ref(false);
const cliKind = ref("theme");
const cliInput = ref("");
const cliInstalling = ref(false);
const cliTitle = computed(() =>
    cliKind.value === "theme" ? "通过 WP CLI 安装主题" : "通过 WP CLI 安装插件",
);

const uploadVisible = ref(false);
const uploadTitle = ref("上传资源包");
const uploading = ref(false);
const uploadFile = ref(null);
const uploadForm = reactive({ kind: "core", name: "", slug: "", version: "" });
const uploadPercent = ref(0);
const uploadStatus = ref("idle"); // idle | uploading | done | error
const uploadError = ref("");
const uploadOption = ref(null);
let progressTimer = null;

const stopProgressTimer = () => {
    if (progressTimer) {
        clearInterval(progressTimer);
        progressTimer = null;
    }
};

const resetUploadState = () => {
    stopProgressTimer();
    uploadFile.value = null;
    uploadPercent.value = 0;
    uploadStatus.value = "idle";
    uploadError.value = "";
    uploadOption.value = null;
};

const editVisible = ref(false);
const saving = ref(false);
const editForm = reactive({
    id: null,
    kind: "",
    name: "",
    slug: "",
    version: "",
    enabled: true,
});

const coreColumns = [
    { title: "版本", dataIndex: "version", slotName: "version" },
    { title: "名称", dataIndex: "name" },
    { title: "来源", slotName: "source" },
    { title: "大小", slotName: "size" },
    { title: "状态", slotName: "is_default" },
    { title: "操作", slotName: "actions", width: 180 },
];
const resourceColumns = [
    { title: "名称", dataIndex: "name" },
    { title: "标识", dataIndex: "slug" },
    { title: "版本", slotName: "version" },
    { title: "来源", slotName: "source" },
    { title: "大小", slotName: "size" },
    { title: "启用", slotName: "enabled" },
    { title: "默认", slotName: "is_default" },
    { title: "操作", slotName: "actions", width: 240 },
];

const coreAssets = computed(() =>
    assets.value.filter((a) => a.kind === "core"),
);
const themeAssets = computed(() =>
    assets.value.filter((a) => a.kind === "theme"),
);
const pluginAssets = computed(() =>
    assets.value.filter((a) => a.kind === "plugin"),
);

const formatSize = (size) => {
    if (!size) return "-";
    if (size < 1024 * 1024) return `${(size / 1024).toFixed(1)} KB`;
    return `${(size / 1024 / 1024).toFixed(1)} MB`;
};

const refresh = async () => {
    loading.value = true;
    try {
        const [list, defs] = await Promise.all([
            request.get("/wp-assets"),
            request.get("/wp-assets/defaults"),
        ]);
        assets.value = list || [];
        Object.assign(defaults, defs);
    } catch (error) {
        console.error(error);
    } finally {
        loading.value = false;
    }
};

const openFetchModal = () => {
    fetchVersion.value = defaults.default_version;
    fetchVisible.value = true;
};

const handleFetch = async () => {
    if (!fetchVersion.value) {
        Message.warning("请输入版本号");
        return;
    }
    fetching.value = true;
    try {
        await request.post(
            "/wp-assets/core/fetch",
            { version: fetchVersion.value },
            { timeout: 180000 },
        );
        Message.success(`WordPress ${fetchVersion.value} 已加入版本库`);
        fetchVisible.value = false;
        await refresh();
    } catch (error) {
        console.error(error);
    } finally {
        fetching.value = false;
    }
};

const openCliInstall = (kind) => {
    cliKind.value = kind;
    cliInput.value = "";
    cliInstalling.value = false;
    cliVisible.value = true;
};

const handleCliInstall = async () => {
    if (cliInstalling.value) return;
    const slug = toSlug(cliInput.value);
    if (!slug) {
        Message.warning("请输入主题名称或插件名称");
        return;
    }
    cliInstalling.value = true;
    try {
        const asset = await request.post(
            "/wp-assets/cli-install",
            {
                kind: cliKind.value,
                slug,
            },
            { timeout: 300000 },
        );
        Message.success(`已通过 WP CLI 安装：${asset?.name || slug}`);
        cliVisible.value = false;
        await refresh();
    } catch (error) {
        console.error(error);
    } finally {
        cliInstalling.value = false;
    }
};

const openUpload = (kind) => {
    Object.assign(uploadForm, {
        kind,
        name: "",
        slug: "",
        version: kind === "core" ? defaults.default_version : "",
    });
    resetUploadState();
    uploadTitle.value =
        kind === "core"
            ? "上传 WordPress 核心包"
            : kind === "theme"
              ? "上传主题包"
              : "上传插件包";
    uploadVisible.value = true;
};

const toSlug = (value) =>
    value
        .toLowerCase()
        .replace(/[^a-z0-9]+/g, "-")
        .replace(/^-+|-+$/g, "")
        .slice(0, 80);

const handlePickFile = (option) => {
    const file = option.file || option.fileItem?.file;
    uploadOption.value = option;
    uploadFile.value = file;
    const baseName = (file?.name || "").replace(/\.zip$/i, "");
    if (uploadForm.kind === "core") {
        if (!uploadForm.name) uploadForm.name = baseName;
    } else {
        // 主题/插件的名称与标识自动取文件名，用户仍可修改
        uploadForm.name = baseName;
        uploadForm.slug = toSlug(baseName) || "package";
    }
    uploadPercent.value = 0;
    uploadStatus.value = "idle";
    uploadError.value = "";
};

const handleUpload = async () => {
    if (!uploadFile.value) {
        Message.warning("请选择 zip 文件");
        return false;
    }
    if (uploadForm.kind === "core" && !uploadForm.version) {
        Message.warning("请填写核心包版本号");
        return false;
    }
    const data = new FormData();
    data.append("file", uploadFile.value);
    data.append("kind", uploadForm.kind);
    data.append("name", uploadForm.name || "");
    data.append("slug", uploadForm.slug || "");
    data.append("version", uploadForm.version || "");
    uploading.value = true;
    uploadStatus.value = "uploading";
    uploadPercent.value = 0;
    uploadError.value = "";
    stopProgressTimer();
    // 部分环境拿不到 Content-Length，用递增进度保证用户能看到上传过程
    progressTimer = setInterval(() => {
        if (uploadPercent.value < 95) uploadPercent.value += 3;
    }, 200);
    try {
        await request.post("/wp-assets/upload", data, {
            timeout: 180000,
            onUploadProgress: (event) => {
                if (event.total > 0) {
                    const fraction = Math.min(1, event.loaded / event.total);
                    uploadPercent.value = Math.min(
                        99,
                        Math.round(fraction * 100),
                    );
                    uploadOption.value?.onProgress?.(fraction);
                }
            },
        });
        stopProgressTimer();
        uploadPercent.value = 100;
        uploadOption.value?.onProgress?.(1);
        uploadOption.value?.onSuccess?.({ success: true });
        uploadStatus.value = "done";
        Message.success("上传成功");
        await refresh();
        // 等用户看到 100% 后再关闭弹窗
        await new Promise((resolve) => setTimeout(resolve, 700));
        return true;
    } catch (error) {
        stopProgressTimer();
        uploadStatus.value = "error";
        uploadError.value =
            error.response?.data?.detail || error.message || "未知错误";
        uploadOption.value?.onError?.(error);
        console.error(error);
        return false;
    } finally {
        uploading.value = false;
    }
};

const openEdit = (record) => {
    Object.assign(editForm, {
        id: record.id,
        kind: record.kind,
        name: record.name,
        slug: record.slug || "",
        version: record.version || "",
        enabled: record.enabled,
    });
    editVisible.value = true;
};

const handleSaveEdit = async () => {
    saving.value = true;
    try {
        await request.put(`/wp-assets/${editForm.id}`, {
            name: editForm.name,
            slug: editForm.slug || null,
            version: editForm.version || null,
            enabled: editForm.enabled,
        });
        Message.success("已保存");
        editVisible.value = false;
        await refresh();
    } catch (error) {
        console.error(error);
    } finally {
        saving.value = false;
    }
};

const handleToggle = async (record, val) => {
    try {
        await request.put(`/wp-assets/${record.id}`, { enabled: val });
    } catch (error) {
        console.error(error);
        record.enabled = !val;
        await refresh();
    }
};

const handleSetDefault = async (record) => {
    try {
        await request.post(`/wp-assets/${record.id}/set-default`);
        Message.success("已设为默认");
        await refresh();
    } catch (error) {
        console.error(error);
    }
};

const handleDelete = async (record) => {
    try {
        await request.delete(`/wp-assets/${record.id}`);
        Message.success("已删除");
        await refresh();
    } catch (error) {
        console.error(error);
    }
};

onMounted(refresh);
</script>

<style scoped>
.wp-assets-page {
    display: flex;
    flex-direction: column;
    gap: 16px;
}
.toolbar-hint {
    margin-top: 12px;
    font-size: 12px;
    color: var(--color-text-3);
}
.cli-hint {
    margin-top: 8px;
    font-size: 12px;
    color: var(--color-text-3);
}
.toolbar {
    display: flex;
    align-items: center;
    gap: 12px;
    margin-bottom: 16px;
}
.upload-status {
    margin-top: 8px;
}
.file-name {
    margin-bottom: 6px;
    font-size: 12px;
    color: var(--color-text-2);
}
.status-hint {
    margin-top: 4px;
    font-size: 12px;
    color: var(--color-text-3);
}
.status-done {
    color: var(--color-success-6);
}
.status-error {
    color: var(--color-danger-6);
}
</style>
