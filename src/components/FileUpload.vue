<template>
  <div class="upload-container">
    <a-card class="upload-card" :bordered="false">
      <template #title>
        <div class="card-title">
          <file-excel-outlined class="title-icon" />
          <span>表格文件上传</span>
        </div>
      </template>
      
      <a-upload-dragger
        v-model:fileList="fileList"
        name="file"
        :multiple="true"
        :accept="acceptTypes"
        :before-upload="beforeUpload"
        :custom-request="customRequest"
        @change="handleChange"
        @drop="handleDrop"
        class="upload-dragger"
      >
        <p class="ant-upload-drag-icon">
          <file-excel-outlined />
        </p>
        <p class="ant-upload-text">点击或拖拽表格文件到此区域上传</p>
        <p class="ant-upload-hint">
          仅支持 Excel (.xlsx, .xls) 和 CSV (.csv) 格式的表格文件，单个文件大小不超过 10MB
        </p>
      </a-upload-dragger>

      <a-divider v-if="uploadedFiles.length > 0">已上传文件</a-divider>
      
      <a-table
        v-if="uploadedFiles.length > 0"
        :columns="columns"
        :data-source="uploadedFiles"
        :pagination="false"
        row-key="uid"
        class="file-table"
      >
        <template #bodyCell="{ column, record }">
          <template v-if="column.key === 'name'">
            <div class="file-name-cell">
              <file-excel-outlined class="file-icon" />
              <a-button type="link" size="small" @click="openPreview(record)">
                {{ record.name }}
              </a-button>
            </div>
          </template>
          <template v-else-if="column.key === 'size'">
            {{ formatFileSize(record.size) }}
          </template>
          <template v-else-if="column.key === 'type'">
            <a-tag :color="getTypeColor(record.name)">
              {{ getFileExtension(record.name) }}
            </a-tag>
          </template>
          <template v-else-if="column.key === 'status'">
            <a-tag :color="getStatusColor(record.status)">
              {{ getStatusText(record.status) }}
            </a-tag>
          </template>
          <template v-else-if="column.key === 'action'">
            <a-space>
              <a-button type="link" size="small" @click="openPreview(record)">
                <eye-outlined /> 预览
              </a-button>
              <a-popconfirm
                title="确定要删除这个文件吗？"
                ok-text="确定"
                cancel-text="取消"
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

      <div class="actions" v-if="uploadedFiles.length > 0">
        <a-space>
          <a-button @click="clearAll" danger>
            <template #icon><clear-outlined /></template>
            清空全部
          </a-button>
        </a-space>
      </div>
    </a-card>

    <!-- 文件预览弹窗 -->
    <FilePreview
      v-model:open="previewVisible"
      :file="previewFileData"
    />
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { message } from 'ant-design-vue'
import {
  FileExcelOutlined,
  DeleteOutlined,
  ClearOutlined,
  EyeOutlined
} from '@ant-design/icons-vue'
import FilePreview from './FilePreview.vue'

const fileList = ref([])
const previewVisible = ref(false)
const previewFileData = ref(null)

// 支持的表格文件类型
const acceptTypes = '.xlsx,.xls,.csv'
const allowedExtensions = ['xlsx', 'xls', 'csv']

// 表格列配置
const columns = [
  {
    title: '文件名',
    dataIndex: 'name',
    key: 'name',
    ellipsis: true
  },
  {
    title: '大小',
    dataIndex: 'size',
    key: 'size',
    width: 100
  },
  {
    title: '类型',
    dataIndex: 'type',
    key: 'type',
    width: 80
  },
  {
    title: '状态',
    dataIndex: 'status',
    key: 'status',
    width: 80
  },
  {
    title: '操作',
    key: 'action',
    width: 150
  }
]

// 计算已上传的文件列表
const uploadedFiles = computed(() => {
  return fileList.value.filter(file => file.status !== 'removed')
})

const beforeUpload = (file) => {
  // 检查文件扩展名
  const extension = file.name.split('.').pop().toLowerCase()
  if (!allowedExtensions.includes(extension)) {
    message.error(`不支持的文件格式！仅支持 ${allowedExtensions.join(', ').toUpperCase()} 格式`)
    return false
  }
  
  // 检查文件大小
  const isLt10M = file.size / 1024 / 1024 < 10
  if (!isLt10M) {
    message.error('文件大小不能超过 10MB!')
    return false
  }
  
  return true
}

// 自定义上传请求（模拟上传）
const customRequest = ({ file, onSuccess }) => {
  // 模拟上传延迟
  setTimeout(() => {
    onSuccess({ status: 'done' })
    message.success(`${file.name} 上传成功`)
  }, 1000)
}

const handleChange = (info) => {
  // 处理文件状态变化
}

const handleDrop = (e) => {
  console.log('Dropped files:', e.dataTransfer.files)
}

const formatFileSize = (bytes) => {
  if (!bytes) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
}

const getFileExtension = (filename) => {
  return filename.split('.').pop().toUpperCase()
}

const getTypeColor = (filename) => {
  const ext = filename.split('.').pop().toLowerCase()
  const colors = {
    xlsx: 'green',
    xls: 'lime',
    csv: 'blue'
  }
  return colors[ext] || 'default'
}

const getStatusColor = (status) => {
  const colors = {
    uploading: 'processing',
    done: 'success',
    error: 'error'
  }
  return colors[status] || 'default'
}

const getStatusText = (status) => {
  const texts = {
    uploading: '上传中',
    done: '已完成',
    error: '失败'
  }
  return texts[status] || '待上传'
}

// 预览文件
const openPreview = (file) => {
  previewFileData.value = file.originFileObj || file
  previewVisible.value = true
}

const removeFile = (file) => {
  const index = fileList.value.findIndex(f => f.uid === file.uid)
  if (index !== -1) {
    fileList.value.splice(index, 1)
    message.info(`已删除 ${file.name}`)
  }
}

const clearAll = () => {
  fileList.value = []
  message.info('已清空所有文件')
}
</script>

<style scoped>
.upload-container {
  min-height: 100vh;
  background: linear-gradient(135deg, #1d976c 0%, #93f9b9 100%);
  padding: 40px 20px;
  display: flex;
  justify-content: center;
  align-items: flex-start;
}

.upload-card {
  width: 100%;
  max-width: 900px;
  border-radius: 16px;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.15);
  background: rgba(255, 255, 255, 0.98);
  backdrop-filter: blur(10px);
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
  color: #1d976c;
}

.upload-dragger {
  border-radius: 12px;
  border: 2px dashed #d9d9d9;
  transition: all 0.3s ease;
  background: linear-gradient(180deg, #f6ffed 0%, #f0fff0 100%);
}

.upload-dragger:hover {
  border-color: #1d976c;
  background: linear-gradient(180deg, #e6ffe6 0%, #d9f7d9 100%);
}

:deep(.ant-upload-drag-icon) {
  margin-bottom: 20px;
}

:deep(.ant-upload-drag-icon .anticon) {
  font-size: 64px;
  color: #1d976c;
}

:deep(.ant-upload-text) {
  font-size: 16px;
  color: #333;
  font-weight: 500;
}

:deep(.ant-upload-hint) {
  color: #888;
  font-size: 14px;
}

.file-table {
  margin-top: 16px;
}

:deep(.ant-table) {
  border-radius: 8px;
  overflow: hidden;
}

:deep(.ant-table-thead > tr > th) {
  background: linear-gradient(180deg, #f6ffed 0%, #e6ffe6 100%);
  font-weight: 600;
}

:deep(.ant-table-tbody > tr:hover > td) {
  background: #f6ffed;
}

.file-name-cell {
  display: flex;
  align-items: center;
  gap: 8px;
}

.file-icon {
  font-size: 18px;
  color: #1d976c;
}

.actions {
  margin-top: 24px;
  display: flex;
  justify-content: flex-end;
}

:deep(.ant-btn-primary) {
  background: linear-gradient(135deg, #1d976c 0%, #93f9b9 100%);
  border: none;
  box-shadow: 0 4px 15px rgba(29, 151, 108, 0.4);
}

:deep(.ant-btn-primary:hover) {
  background: linear-gradient(135deg, #188f65 0%, #7be8a3 100%);
}

:deep(.ant-card-head) {
  border-bottom: 1px solid #f0f0f0;
}
</style>
