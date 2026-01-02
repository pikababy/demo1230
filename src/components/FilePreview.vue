<template>
  <a-modal
    v-model:open="visible"
    :title="modalTitle"
    :width="900"
    :footer="null"
    :destroyOnClose="true"
    class="file-preview-modal"
  >
    <!-- 加载状态 -->
    <div v-if="loading" class="loading-container">
      <a-spin size="large" tip="正在解析文件..." />
    </div>

    <!-- 错误状态 -->
    <div v-else-if="error" class="error-container">
      <a-result status="error" :title="error" sub-title="无法预览此文件">
        <template #extra>
          <a-button type="primary" @click="close">关闭</a-button>
        </template>
      </a-result>
    </div>

    <!-- 图片预览 -->
    <div v-else-if="fileType === 'image'" class="image-preview">
      <img :src="imageUrl" :alt="fileName" />
    </div>

    <!-- 表格预览 -->
    <div v-else-if="fileType === 'excel' || fileType === 'csv'" class="table-preview">
      <!-- Sheet 选择器 -->
      <div v-if="sheetNames.length > 1" class="sheet-selector">
        <span>工作表：</span>
        <a-radio-group v-model:value="currentSheet" button-style="solid" size="small">
          <a-radio-button v-for="name in sheetNames" :key="name" :value="name">
            {{ name }}
          </a-radio-button>
        </a-radio-group>
      </div>

      <!-- 数据统计 -->
      <div class="table-stats">
        <a-space>
          <a-tag color="blue">共 {{ tableData.length }} 行</a-tag>
          <a-tag color="green">{{ tableColumns.length }} 列</a-tag>
        </a-space>
      </div>

      <!-- 表格 -->
      <a-table
        :columns="tableColumns"
        :data-source="tableData"
        :scroll="{ x: 'max-content', y: 400 }"
        :pagination="{ pageSize: 50, showSizeChanger: true, showTotal: (total) => `共 ${total} 条` }"
        size="small"
        bordered
      />
    </div>

    <!-- 文本预览 -->
    <div v-else-if="fileType === 'text'" class="text-preview">
      <pre>{{ textContent }}</pre>
    </div>

    <!-- 不支持的文件类型 -->
    <div v-else class="unsupported-preview">
      <a-result status="info" title="暂不支持预览此类型文件">
        <template #extra>
          <a-descriptions :column="1" bordered size="small">
            <a-descriptions-item label="文件名">{{ fileName }}</a-descriptions-item>
            <a-descriptions-item label="文件大小">{{ formatFileSize(fileSize) }}</a-descriptions-item>
            <a-descriptions-item label="文件类型">{{ fileMimeType || '未知' }}</a-descriptions-item>
          </a-descriptions>
        </template>
      </a-result>
    </div>
  </a-modal>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import * as XLSX from 'xlsx'

const props = defineProps({
  open: Boolean,
  file: Object, // File 对象或文件信息对象
  fileUrl: String // 文件 URL（用于已上传的文件）
})

const emit = defineEmits(['update:open', 'close'])

// 状态
const visible = computed({
  get: () => props.open,
  set: (val) => emit('update:open', val)
})

const loading = ref(false)
const error = ref('')
const fileType = ref('')
const fileName = ref('')
const fileSize = ref(0)
const fileMimeType = ref('')

// 图片预览
const imageUrl = ref('')

// 表格预览
const sheetNames = ref([])
const currentSheet = ref('')
const workbook = ref(null)
const tableColumns = ref([])
const tableData = ref([])

// 文本预览
const textContent = ref('')

// 模态框标题
const modalTitle = computed(() => {
  return `文件预览 - ${fileName.value}`
})

// 监听文件变化
watch(() => props.file, async (newFile) => {
  if (newFile && props.open) {
    await parseFile(newFile)
  }
}, { immediate: true })

watch(() => props.open, async (isOpen) => {
  if (isOpen && props.file) {
    await parseFile(props.file)
  } else if (!isOpen) {
    resetState()
  }
})

// 监听工作表切换
watch(currentSheet, (sheetName) => {
  if (workbook.value && sheetName) {
    parseSheet(sheetName)
  }
})

// 解析文件
async function parseFile(file) {
  loading.value = true
  error.value = ''
  
  try {
    // 获取文件信息
    if (file instanceof File) {
      fileName.value = file.name
      fileSize.value = file.size
      fileMimeType.value = file.type
    } else {
      fileName.value = file.name || '未知文件'
      fileSize.value = file.size || 0
      fileMimeType.value = file.type || ''
    }

    // 判断文件类型
    const ext = fileName.value.split('.').pop().toLowerCase()
    
    if (['jpg', 'jpeg', 'png', 'gif', 'webp', 'bmp', 'svg'].includes(ext)) {
      fileType.value = 'image'
      await parseImage(file)
    } else if (['xlsx', 'xls'].includes(ext)) {
      fileType.value = 'excel'
      await parseExcel(file)
    } else if (ext === 'csv') {
      fileType.value = 'csv'
      await parseCSV(file)
    } else if (['txt', 'json', 'md', 'js', 'ts', 'css', 'html', 'xml'].includes(ext)) {
      fileType.value = 'text'
      await parseText(file)
    } else {
      fileType.value = 'unknown'
    }
  } catch (e) {
    console.error('文件解析失败:', e)
    error.value = e.message || '文件解析失败'
  } finally {
    loading.value = false
  }
}

// 解析图片
async function parseImage(file) {
  if (file instanceof File) {
    imageUrl.value = URL.createObjectURL(file)
  } else if (props.fileUrl) {
    imageUrl.value = props.fileUrl
  }
}

// 解析 Excel
async function parseExcel(file) {
  const arrayBuffer = await readFileAsArrayBuffer(file)
  workbook.value = XLSX.read(arrayBuffer, { type: 'array' })
  sheetNames.value = workbook.value.SheetNames
  currentSheet.value = sheetNames.value[0]
}

// 解析 CSV
async function parseCSV(file) {
  const text = await readFileAsText(file)
  workbook.value = XLSX.read(text, { type: 'string' })
  sheetNames.value = workbook.value.SheetNames
  currentSheet.value = sheetNames.value[0]
}

// 解析工作表
function parseSheet(sheetName) {
  if (!workbook.value) return

  const sheet = workbook.value.Sheets[sheetName]
  const json = XLSX.utils.sheet_to_json(sheet, { header: 1, defval: '' })

  if (json.length === 0) {
    tableColumns.value = []
    tableData.value = []
    return
  }

  // 第一行作为表头
  const headers = json[0]
  tableColumns.value = headers.map((header, index) => ({
    title: String(header || `列${index + 1}`),
    dataIndex: `col_${index}`,
    key: `col_${index}`,
    width: 150,
    ellipsis: true
  }))

  // 剩余行作为数据
  tableData.value = json.slice(1).map((row, rowIndex) => {
    const rowData = { key: rowIndex }
    headers.forEach((_, colIndex) => {
      rowData[`col_${colIndex}`] = row[colIndex] ?? ''
    })
    return rowData
  })
}

// 解析文本
async function parseText(file) {
  textContent.value = await readFileAsText(file)
}

// 读取文件为 ArrayBuffer
function readFileAsArrayBuffer(file) {
  return new Promise((resolve, reject) => {
    if (file instanceof File) {
      const reader = new FileReader()
      reader.onload = (e) => resolve(e.target.result)
      reader.onerror = reject
      reader.readAsArrayBuffer(file)
    } else if (file.originFileObj) {
      const reader = new FileReader()
      reader.onload = (e) => resolve(e.target.result)
      reader.onerror = reject
      reader.readAsArrayBuffer(file.originFileObj)
    } else {
      reject(new Error('无法读取文件'))
    }
  })
}

// 读取文件为文本
function readFileAsText(file) {
  return new Promise((resolve, reject) => {
    if (file instanceof File) {
      const reader = new FileReader()
      reader.onload = (e) => resolve(e.target.result)
      reader.onerror = reject
      reader.readAsText(file)
    } else if (file.originFileObj) {
      const reader = new FileReader()
      reader.onload = (e) => resolve(e.target.result)
      reader.onerror = reject
      reader.readAsText(file.originFileObj)
    } else {
      reject(new Error('无法读取文件'))
    }
  })
}

// 格式化文件大小
function formatFileSize(bytes) {
  if (!bytes || bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
}

// 重置状态
function resetState() {
  loading.value = false
  error.value = ''
  fileType.value = ''
  fileName.value = ''
  fileSize.value = 0
  fileMimeType.value = ''
  imageUrl.value = ''
  sheetNames.value = []
  currentSheet.value = ''
  workbook.value = null
  tableColumns.value = []
  tableData.value = []
  textContent.value = ''
}

// 关闭
function close() {
  emit('update:open', false)
  emit('close')
}
</script>

<style scoped>
.file-preview-modal :deep(.ant-modal-body) {
  max-height: 70vh;
  overflow: auto;
}

.loading-container {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 300px;
}

.error-container {
  min-height: 300px;
}

.image-preview {
  text-align: center;
}

.image-preview img {
  max-width: 100%;
  max-height: 60vh;
  border-radius: 8px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
}

.table-preview {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.sheet-selector {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 8px 0;
}

.table-stats {
  display: flex;
  justify-content: flex-end;
}

.text-preview {
  background: #f5f5f5;
  border-radius: 8px;
  padding: 16px;
  max-height: 60vh;
  overflow: auto;
}

.text-preview pre {
  margin: 0;
  white-space: pre-wrap;
  word-wrap: break-word;
  font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
  font-size: 13px;
  line-height: 1.5;
}

.unsupported-preview {
  padding: 20px;
}

:deep(.ant-table-thead > tr > th) {
  background: linear-gradient(180deg, #f0f5ff 0%, #e6f0ff 100%);
  font-weight: 600;
}

:deep(.ant-table-tbody > tr:hover > td) {
  background: #f0f5ff;
}
</style>
