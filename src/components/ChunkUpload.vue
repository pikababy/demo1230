<template>
  <div class="chunk-upload-container">
    <a-card class="upload-card" :bordered="false">
      <template #title>
        <div class="card-title">
          <cloud-upload-outlined class="title-icon" />
          <span>大文件分片上传</span>
          <a-tag v-if="rateLimitInfo.isLimited" color="warning" class="rate-limit-tag">
            <thunderbolt-outlined /> 限流中
          </a-tag>
        </div>
      </template>

      <!-- 限流状态显示 -->
      <div v-if="showRateLimitStatus" class="rate-limit-status">
        <a-alert type="info" show-icon>
          <template #message>
            <div class="rate-limit-info">
              <span>限流状态</span>
              <a-space>
                <a-tag color="blue">
                  IP: {{ rateLimitStatus.ip?.tokens || 0 }}/{{ rateLimitStatus.ip?.capacity || 20 }}
                </a-tag>
                <a-tag color="green">
                  用户: {{ rateLimitStatus.user?.remaining || 0 }}/{{ rateLimitStatus.user?.limit || 100 }}
                </a-tag>
              </a-space>
            </div>
          </template>
        </a-alert>
      </div>

      <!-- 上传区域 -->
      <a-upload-dragger
        v-if="!currentFile"
        :before-upload="handleBeforeUpload"
        :show-upload-list="false"
        :accept="acceptTypes"
        class="upload-dragger"
      >
        <p class="ant-upload-drag-icon">
          <inbox-outlined />
        </p>
        <p class="ant-upload-text">点击或拖拽文件到此区域上传</p>
        <p class="ant-upload-hint">
          支持大文件上传，自动分片、断点续传、限流保护
        </p>
      </a-upload-dragger>

      <!-- 上传进度 -->
      <div v-else class="upload-progress">
        <div class="file-info">
          <file-outlined class="file-icon" />
          <div class="file-details">
            <div class="file-name">{{ currentFile.name }}</div>
            <div class="file-size">{{ formatFileSize(currentFile.size) }}</div>
          </div>
          <a-button 
            v-if="status !== 'done'" 
            type="text" 
            danger 
            @click="cancelUpload"
          >
            <close-outlined />
          </a-button>
        </div>

        <!-- Hash 计算进度 -->
        <div v-if="status === 'hashing'" class="progress-section">
          <div class="progress-label">
            <loading-outlined spin />
            <span>正在计算文件指纹...</span>
          </div>
          <a-progress :percent="hashProgress" :show-info="false" status="active" />
        </div>

        <!-- 秒传提示 -->
        <div v-else-if="status === 'exists'" class="progress-section success">
          <check-circle-outlined class="success-icon" />
          <span>文件已存在，秒传成功！</span>
        </div>

        <!-- 上传进度 -->
        <div v-else-if="status === 'uploading' || status === 'done'" class="progress-section">
          <div class="progress-label">
            <span v-if="status === 'uploading'">
              <loading-outlined spin /> 正在上传 ({{ uploadProgress.uploaded }}/{{ uploadProgress.total }} 分片)
              <a-tag v-if="rateLimitInfo.retrying" color="orange" size="small">
                限流重试中...
              </a-tag>
            </span>
            <span v-else class="success-text">
              <check-circle-outlined /> 上传完成！
            </span>
          </div>
          <a-progress 
            :percent="uploadProgress.percent" 
            :status="status === 'done' ? 'success' : 'active'"
          />
          <!-- 限流警告 -->
          <a-alert 
            v-if="rateLimitInfo.isLimited" 
            type="warning" 
            show-icon
            class="rate-limit-warning"
          >
            <template #message>
              请求被限流，{{ Math.ceil(rateLimitInfo.retryAfter / 1000) }}秒后自动重试
              ({{ rateLimitInfo.blockedBy }} 限制)
            </template>
          </a-alert>
        </div>

        <!-- 错误提示 -->
        <div v-else-if="status === 'error'" class="progress-section error">
          <close-circle-outlined class="error-icon" />
          <span>{{ errorMessage }}</span>
          <a-button type="link" @click="retryUpload">重试</a-button>
        </div>

        <!-- 操作按钮 -->
        <div class="actions">
          <a-button v-if="status === 'done'" type="primary" @click="resetUpload">
            <upload-outlined /> 继续上传
          </a-button>
        </div>
      </div>

      <a-divider v-if="uploadedFiles.length > 0">已上传文件</a-divider>

      <!-- 已上传文件列表 -->
      <a-table
        v-if="uploadedFiles.length > 0"
        :columns="columns"
        :data-source="uploadedFiles"
        :pagination="false"
        row-key="fileHash"
        size="small"
      >
        <template #bodyCell="{ column, record }">
          <template v-if="column.key === 'name'">
            <div class="file-name-cell">
              <file-outlined class="table-file-icon" />
              <a-button type="link" size="small" @click="openPreview(record)">
                {{ record.name }}
              </a-button>
            </div>
          </template>
          <template v-else-if="column.key === 'size'">
            {{ formatFileSize(record.size) }}
          </template>
          <template v-else-if="column.key === 'action'">
            <a-space>
              <a-button type="link" size="small" @click="openPreview(record)">
                <eye-outlined /> 预览
              </a-button>
              <a-popconfirm
                title="确定要删除这个文件吗？"
                @confirm="removeFile(record)"
              >
                <a-button type="text" danger size="small">
                  <delete-outlined /> 删除
                </a-button>
              </a-popconfirm>
            </a-space>
          </template>
        </template>
      </a-table>

      <!-- 文件预览弹窗 -->
      <FilePreview
        v-model:open="previewVisible"
        :file="previewFileData"
      />
    </a-card>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, onUnmounted } from 'vue'
import { message } from 'ant-design-vue'
import {
  CloudUploadOutlined,
  InboxOutlined,
  FileOutlined,
  DeleteOutlined,
  EyeOutlined,
  CloseOutlined,
  LoadingOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  UploadOutlined,
  ThunderboltOutlined
} from '@ant-design/icons-vue'
import { ChunkUploader, formatFileSize } from '../utils/chunk-uploader'
import { getRateLimitStatus } from '../utils/mock-server'
import FilePreview from './FilePreview.vue'

// Props
const props = defineProps({
  acceptTypes: {
    type: String,
    default: ''
  },
  maxSize: {
    type: Number,
    default: 1024 * 1024 * 1024 // 默认 1GB
  }
})

// 状态
const currentFile = ref(null)
const status = ref('idle') // idle | hashing | uploading | done | error | exists
const hashProgress = ref(0)
const uploadProgress = reactive({
  percent: 0,
  uploaded: 0,
  total: 0
})
const errorMessage = ref('')
const uploadedFiles = ref([])
const uploaderInstance = ref(null)

// 文件预览状态
const previewVisible = ref(false)
const previewFileData = ref(null)

// 限流状态
const showRateLimitStatus = ref(true)
const rateLimitStatus = reactive({
  global: { tokens: 0, capacity: 0 },
  ip: { tokens: 0, capacity: 0 },
  user: { count: 0, limit: 0, remaining: 0 }
})
const rateLimitInfo = reactive({
  isLimited: false,
  retrying: false,
  retryAfter: 0,
  blockedBy: ''
})

let rateLimitTimer = null

// 表格列配置
const columns = [
  { title: '文件名', dataIndex: 'name', key: 'name', ellipsis: true },
  { title: '大小', dataIndex: 'size', key: 'size', width: 120 },
  { title: '操作', key: 'action', width: 100 }
]

// 更新限流状态
const updateRateLimitStatus = () => {
  try {
    const status = getRateLimitStatus()
    Object.assign(rateLimitStatus, status)
  } catch (e) {
    console.warn('获取限流状态失败', e)
  }
}

// 生命周期
onMounted(() => {
  updateRateLimitStatus()
  rateLimitTimer = setInterval(updateRateLimitStatus, 2000)
})

onUnmounted(() => {
  if (rateLimitTimer) {
    clearInterval(rateLimitTimer)
  }
})

// 选择文件
const handleBeforeUpload = async (file) => {
  // 文件大小检查
  if (file.size > props.maxSize) {
    message.error(`文件大小不能超过 ${formatFileSize(props.maxSize)}`)
    return false
  }

  currentFile.value = file
  await startUpload(file)
  return false // 阻止默认上传
}

// 开始上传
const startUpload = async (file) => {
  try {
    status.value = 'hashing'
    hashProgress.value = 0
    rateLimitInfo.isLimited = false
    rateLimitInfo.retrying = false

    // 创建上传器实例
    const uploader = new ChunkUploader(file, {
      chunkSize: 5 * 1024 * 1024, // 5MB
      concurrency: 3,
      baseUrl: '/api/upload',
      maxRetries: 5,
      onRateLimited: (info) => {
        rateLimitInfo.isLimited = true
        rateLimitInfo.retrying = true
        rateLimitInfo.retryAfter = info.retryAfter
        rateLimitInfo.blockedBy = info.blockedBy
        message.warning(`请求被限流，${Math.ceil(info.retryAfter / 1000)}秒后自动重试`)
        
        // 自动清除限流状态
        setTimeout(() => {
          rateLimitInfo.isLimited = false
          rateLimitInfo.retrying = false
        }, info.retryAfter + 500)
      }
    })
    uploaderInstance.value = uploader

    // 初始化（计算 Hash + 检查已上传分片）
    const initResult = await uploader.init((progress) => {
      hashProgress.value = progress
    })

    if (initResult.status === 'exists') {
      // 秒传
      status.value = 'exists'
      message.success('文件已存在，秒传成功！')
      addToUploadedList(file, initResult.url)
      return
    }

    // 开始上传
    status.value = 'uploading'
    uploadProgress.percent = Math.round((initResult.uploadedCount / initResult.totalCount) * 100)
    uploadProgress.uploaded = initResult.uploadedCount
    uploadProgress.total = initResult.totalCount

    const result = await uploader.upload((progress) => {
      uploadProgress.percent = progress.percent
      uploadProgress.uploaded = progress.uploaded
      uploadProgress.total = progress.total
      updateRateLimitStatus()
    })

    status.value = 'done'
    message.success('上传完成！')
    addToUploadedList(file, result.url)

  } catch (error) {
    console.error('上传失败:', error)
    status.value = 'error'
    errorMessage.value = error.message || '上传失败，请重试'
    message.error(errorMessage.value)
  }
}

// 添加到已上传列表
const addToUploadedList = (file, url) => {
  uploadedFiles.value.push({
    fileHash: uploaderInstance.value?.fileHash || Date.now().toString(),
    name: file.name,
    size: file.size,
    url,
    originFile: file  // 保存原始文件用于预览
  })
}

// 取消上传
const cancelUpload = () => {
  if (uploaderInstance.value) {
    uploaderInstance.value.abort()
  }
  resetUpload()
  message.info('已取消上传')
}

// 重试上传
const retryUpload = () => {
  if (currentFile.value) {
    startUpload(currentFile.value)
  }
}

// 重置上传
const resetUpload = () => {
  currentFile.value = null
  status.value = 'idle'
  hashProgress.value = 0
  uploadProgress.percent = 0
  uploadProgress.uploaded = 0
  uploadProgress.total = 0
  errorMessage.value = ''
  uploaderInstance.value = null
  rateLimitInfo.isLimited = false
  rateLimitInfo.retrying = false
}

// 打开文件预览
const openPreview = (record) => {
  // 如果有原始文件对象，使用它；否则创建一个模拟文件对象
  if (record.originFile) {
    previewFileData.value = record.originFile
  } else {
    // 创建一个包含基本信息的对象用于预览
    previewFileData.value = {
      name: record.name,
      size: record.size,
      type: '',
      url: record.url
    }
  }
  previewVisible.value = true
}

// 删除文件
const removeFile = (record) => {
  const index = uploadedFiles.value.findIndex(f => f.fileHash === record.fileHash)
  if (index !== -1) {
    uploadedFiles.value.splice(index, 1)
    message.info(`已删除 ${record.name}`)
  }
}
</script>

<style scoped>
.chunk-upload-container {
  min-height: 100vh;
  background: linear-gradient(135deg, #2193b0 0%, #6dd5ed 100%);
  padding: 40px 20px;
  display: flex;
  justify-content: center;
  align-items: flex-start;
}

.upload-card {
  width: 100%;
  max-width: 800px;
  border-radius: 16px;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.15);
  background: rgba(255, 255, 255, 0.98);
}

.card-title {
  display: flex;
  align-items: center;
  gap: 12px;
  font-size: 20px;
  font-weight: 600;
  color: #1a1a2e;
}

.title-icon {
  font-size: 24px;
  color: #2193b0;
}

.rate-limit-tag {
  margin-left: auto;
}

.rate-limit-status {
  margin-bottom: 16px;
}

.rate-limit-info {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.rate-limit-warning {
  margin-top: 12px;
}

.upload-dragger {
  border-radius: 12px;
  border: 2px dashed #d9d9d9;
  transition: all 0.3s ease;
  background: linear-gradient(180deg, #e0f7fa 0%, #b2ebf2 100%);
}

.upload-dragger:hover {
  border-color: #2193b0;
}

:deep(.ant-upload-drag-icon .anticon) {
  font-size: 64px;
  color: #2193b0;
}

.upload-progress {
  padding: 20px;
  background: #f8f9fa;
  border-radius: 12px;
}

.file-info {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
}

.file-icon {
  font-size: 32px;
  color: #2193b0;
}

.file-details {
  flex: 1;
}

.file-name {
  font-weight: 600;
  font-size: 14px;
  color: #333;
  word-break: break-all;
}

.file-size {
  font-size: 12px;
  color: #888;
}

.progress-section {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.progress-section.success {
  flex-direction: row;
  align-items: center;
  color: #52c41a;
  font-weight: 500;
}

.progress-section.error {
  flex-direction: row;
  align-items: center;
  color: #ff4d4f;
}

.progress-label {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
  color: #666;
}

.success-icon, .error-icon {
  font-size: 20px;
  margin-right: 8px;
}

.success-text {
  color: #52c41a;
}

.actions {
  margin-top: 16px;
  display: flex;
  justify-content: center;
}

.file-name-cell {
  display: flex;
  align-items: center;
  gap: 8px;
}

.table-file-icon {
  font-size: 18px;
  color: #2193b0;
}

:deep(.ant-progress-bg) {
  background: linear-gradient(90deg, #2193b0 0%, #6dd5ed 100%);
}
</style>
