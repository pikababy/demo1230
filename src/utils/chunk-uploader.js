import SparkMD5 from 'spark-md5';

// 默认分片大小: 5MB
const DEFAULT_CHUNK_SIZE = 5 * 1024 * 1024;

/**
 * 创建文件分片
 */
export function createChunks(file, chunkSize = DEFAULT_CHUNK_SIZE) {
    const chunks = [];
    let start = 0;
    let index = 0;

    while (start < file.size) {
        const end = Math.min(start + chunkSize, file.size);
        chunks.push({
            index,
            chunk: file.slice(start, end),
            start,
            end,
            size: end - start
        });
        start = end;
        index++;
    }

    return chunks;
}

/**
 * 计算文件 Hash (使用 Web Worker 避免阻塞主线程)
 */
export async function calculateFileHash(file, onProgress) {
    return new Promise((resolve, reject) => {
        const chunkSize = DEFAULT_CHUNK_SIZE;
        const chunks = Math.ceil(file.size / chunkSize);
        const spark = new SparkMD5.ArrayBuffer();
        const reader = new FileReader();
        let currentChunk = 0;

        reader.onload = (e) => {
            spark.append(e.target.result);
            currentChunk++;

            if (onProgress) {
                onProgress(Math.round((currentChunk / chunks) * 100));
            }

            if (currentChunk < chunks) {
                loadNext();
            } else {
                resolve(spark.end());
            }
        };

        reader.onerror = () => {
            reject(new Error('文件读取失败'));
        };

        function loadNext() {
            const start = currentChunk * chunkSize;
            const end = Math.min(start + chunkSize, file.size);
            reader.readAsArrayBuffer(file.slice(start, end));
        }

        loadNext();
    });
}

/**
 * 分片上传器类
 */
export class ChunkUploader {
    constructor(file, options = {}) {
        this.file = file;
        this.chunkSize = options.chunkSize || DEFAULT_CHUNK_SIZE;
        this.concurrency = options.concurrency || 3; // 并发数
        this.baseUrl = options.baseUrl || '/api/upload';
        this.maxRetries = options.maxRetries || 3; // 最大重试次数
        this.onRateLimited = options.onRateLimited || null; // 限流回调

        this.chunks = [];
        this.fileHash = '';
        this.uploadedChunks = new Set();
        this.aborted = false;
    }

    /**
     * 初始化：切片 + 计算 Hash + 检查已上传分片
     */
    async init(onHashProgress) {
        // 1. 创建分片
        this.chunks = createChunks(this.file, this.chunkSize);

        // 2. 计算文件 Hash
        this.fileHash = await calculateFileHash(this.file, onHashProgress);

        // 3. 检查服务器已上传的分片
        const checkResult = await this.checkUploadedChunks();

        return checkResult;
    }

    /**
     * 查询已上传的分片
     */
    async checkUploadedChunks() {
        try {
            const response = await fetch(`${this.baseUrl}/check`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    fileHash: this.fileHash,
                    fileName: this.file.name,
                    totalChunks: this.chunks.length,
                    fileSize: this.file.size
                })
            });

            const data = await response.json();

            if (data.uploaded) {
                // 文件已存在，秒传
                return { status: 'exists', url: data.url };
            }

            // 记录已上传的分片
            this.uploadedChunks = new Set(data.uploadedChunks || []);

            return {
                status: 'partial',
                uploadedCount: this.uploadedChunks.size,
                totalCount: this.chunks.length
            };
        } catch (error) {
            // 如果检查接口失败，假设没有已上传的分片
            console.warn('检查已上传分片失败，将从头开始上传', error);
            this.uploadedChunks = new Set();
            return {
                status: 'new',
                uploadedCount: 0,
                totalCount: this.chunks.length
            };
        }
    }

    /**
     * 上传单个分片（带重试机制）
     */
    async uploadChunk(chunkInfo, retryCount = 0) {
        if (this.aborted) {
            throw new Error('上传已取消');
        }

        const formData = new FormData();
        formData.append('chunk', chunkInfo.chunk);
        formData.append('chunkIndex', chunkInfo.index);
        formData.append('totalChunks', this.chunks.length);
        formData.append('fileHash', this.fileHash);
        formData.append('fileName', this.file.name);
        formData.append('fileSize', this.file.size);

        const response = await fetch(`${this.baseUrl}/chunk`, {
            method: 'POST',
            body: formData
        });

        // 处理限流响应
        if (response.status === 429) {
            const data = await response.json();
            const retryAfter = data.retryAfter || 1000;

            if (retryCount < this.maxRetries) {
                console.warn(`分片 ${chunkInfo.index} 被限流，${retryAfter}ms 后重试 (${retryCount + 1}/${this.maxRetries})`);

                // 触发限流回调
                if (this.onRateLimited) {
                    this.onRateLimited({
                        chunkIndex: chunkInfo.index,
                        retryAfter,
                        retryCount: retryCount + 1,
                        blockedBy: data.blockedBy
                    });
                }

                // 等待后重试
                await this.delay(retryAfter);
                return this.uploadChunk(chunkInfo, retryCount + 1);
            }

            throw new Error(`分片 ${chunkInfo.index} 上传失败：请求过于频繁`);
        }

        if (!response.ok) {
            // 其他错误也支持重试
            if (retryCount < this.maxRetries) {
                const backoffTime = Math.min(1000 * Math.pow(2, retryCount), 10000);
                console.warn(`分片 ${chunkInfo.index} 上传失败，${backoffTime}ms 后重试`);
                await this.delay(backoffTime);
                return this.uploadChunk(chunkInfo, retryCount + 1);
            }
            throw new Error(`分片 ${chunkInfo.index} 上传失败`);
        }

        return await response.json();
    }

    /**
     * 延迟函数
     */
    delay(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }


    /**
     * 并发上传所有分片
     */
    async upload(onProgress) {
        // 过滤出未上传的分片
        const pendingChunks = this.chunks.filter(
            chunk => !this.uploadedChunks.has(chunk.index)
        );

        if (pendingChunks.length === 0) {
            // 所有分片已上传，直接合并
            return await this.mergeChunks();
        }

        let completedCount = this.uploadedChunks.size;
        const totalCount = this.chunks.length;

        // 并发控制
        const uploadWithConcurrency = async () => {
            const executing = [];

            for (const chunk of pendingChunks) {
                if (this.aborted) break;

                const promise = this.uploadChunk(chunk).then(() => {
                    completedCount++;
                    this.uploadedChunks.add(chunk.index);

                    if (onProgress) {
                        onProgress({
                            percent: Math.round((completedCount / totalCount) * 100),
                            uploaded: completedCount,
                            total: totalCount
                        });
                    }
                });

                executing.push(promise);

                if (executing.length >= this.concurrency) {
                    await Promise.race(executing);
                    // 移除已完成的 promise
                    const completedIndex = executing.findIndex(p => p.settled);
                    if (completedIndex !== -1) {
                        executing.splice(completedIndex, 1);
                    }
                }
            }

            await Promise.all(executing);
        };

        await uploadWithConcurrency();

        if (this.aborted) {
            throw new Error('上传已取消');
        }

        // 合并分片
        return await this.mergeChunks();
    }

    /**
     * 请求服务器合并分片
     */
    async mergeChunks() {
        const response = await fetch(`${this.baseUrl}/merge`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                fileHash: this.fileHash,
                fileName: this.file.name,
                totalChunks: this.chunks.length,
                fileSize: this.file.size
            })
        });

        if (!response.ok) {
            throw new Error('文件合并失败');
        }

        return await response.json();
    }

    /**
     * 取消上传
     */
    abort() {
        this.aborted = true;
    }

    /**
     * 获取上传状态
     */
    getStatus() {
        return {
            fileHash: this.fileHash,
            fileName: this.file.name,
            fileSize: this.file.size,
            totalChunks: this.chunks.length,
            uploadedChunks: this.uploadedChunks.size,
            progress: Math.round((this.uploadedChunks.size / this.chunks.length) * 100)
        };
    }
}

/**
 * 格式化文件大小
 */
export function formatFileSize(bytes) {
    if (!bytes || bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}
