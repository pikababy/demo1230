/**
 * 模拟分片上传服务器（带限流功能）
 * 在实际项目中，这些逻辑应该在后端实现
 */

import { createUploadRateLimiter } from './rate-limiter';

const STORAGE_KEY = 'chunk_upload_storage';

// 创建限流器实例
const rateLimiter = createUploadRateLimiter();

// 限流配置（可调整）
const RATE_LIMIT_CONFIG = {
    enabled: true,
    // 模拟 IP（实际项目中从请求获取）
    mockIp: '192.168.1.100',
    mockUserId: 'user_001'
};

// 获取存储数据
function getStorage() {
    try {
        const data = localStorage.getItem(STORAGE_KEY);
        return data ? JSON.parse(data) : { files: {}, chunks: {} };
    } catch {
        return { files: {}, chunks: {} };
    }
}

// 保存存储数据
function saveStorage(data) {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(data));
}

/**
 * 检查限流
 */
function checkRateLimit() {
    if (!RATE_LIMIT_CONFIG.enabled) {
        return { allowed: true };
    }

    const context = {
        ip: RATE_LIMIT_CONFIG.mockIp,
        userId: RATE_LIMIT_CONFIG.mockUserId
    };

    return rateLimiter.check(context);
}

/**
 * 获取限流状态
 */
export function getRateLimitStatus() {
    const context = {
        ip: RATE_LIMIT_CONFIG.mockIp,
        userId: RATE_LIMIT_CONFIG.mockUserId
    };
    return rateLimiter.getStatus(context);
}

/**
 * 设置限流配置
 */
export function setRateLimitConfig(config) {
    Object.assign(RATE_LIMIT_CONFIG, config);
}

/**
 * 模拟检查已上传分片
 */
export async function mockCheckChunks(params) {
    await delay(300);

    const { fileHash } = params;
    const storage = getStorage();

    if (storage.files[fileHash]) {
        return {
            uploaded: true,
            url: storage.files[fileHash].url
        };
    }

    const uploadedChunks = storage.chunks[fileHash] || [];
    return {
        uploaded: false,
        uploadedChunks
    };
}

/**
 * 模拟上传分片（带限流）
 */
export async function mockUploadChunk(formData) {
    // 检查限流
    const rateLimitResult = checkRateLimit();

    if (!rateLimitResult.allowed) {
        const error = new Error('请求过于频繁，请稍后重试');
        error.code = 'RATE_LIMITED';
        error.retryAfter = rateLimitResult.retryAfter;
        error.blockedBy = rateLimitResult.blockedBy;
        throw error;
    }

    await delay(300 + Math.random() * 400);

    const chunkIndex = parseInt(formData.get('chunkIndex'));
    const fileHash = formData.get('fileHash');

    const storage = getStorage();

    if (!storage.chunks[fileHash]) {
        storage.chunks[fileHash] = [];
    }
    if (!storage.chunks[fileHash].includes(chunkIndex)) {
        storage.chunks[fileHash].push(chunkIndex);
    }

    saveStorage(storage);

    return {
        success: true,
        chunkIndex,
        rateLimit: getRateLimitStatus()
    };
}

/**
 * 模拟合并分片
 */
export async function mockMergeChunks(params) {
    await delay(500);

    const { fileHash, fileName, totalChunks } = params;
    const storage = getStorage();

    const uploadedChunks = storage.chunks[fileHash] || [];
    if (uploadedChunks.length < totalChunks) {
        throw new Error(`分片不完整: ${uploadedChunks.length}/${totalChunks}`);
    }

    const url = `/uploads/${fileHash}/${fileName}`;

    storage.files[fileHash] = {
        fileName,
        url,
        uploadedAt: new Date().toISOString()
    };

    delete storage.chunks[fileHash];
    saveStorage(storage);

    return { success: true, url };
}

/**
 * 延迟函数
 */
function delay(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
}

/**
 * 设置全局 fetch 拦截器
 */
export function setupMockServer() {
    const originalFetch = window.fetch;

    window.fetch = async (url, options = {}) => {
        if (typeof url === 'string' && url.startsWith('/api/upload')) {
            const endpoint = url.replace('/api/upload', '');

            try {
                let result;

                if (endpoint === '/check') {
                    const body = JSON.parse(options.body);
                    result = await mockCheckChunks(body);
                } else if (endpoint === '/chunk') {
                    result = await mockUploadChunk(options.body);
                } else if (endpoint === '/merge') {
                    const body = JSON.parse(options.body);
                    result = await mockMergeChunks(body);
                } else if (endpoint === '/rate-limit-status') {
                    result = getRateLimitStatus();
                } else {
                    throw new Error('Unknown endpoint');
                }

                return new Response(JSON.stringify(result), {
                    status: 200,
                    headers: { 'Content-Type': 'application/json' }
                });
            } catch (error) {
                const status = error.code === 'RATE_LIMITED' ? 429 : 500;
                return new Response(JSON.stringify({
                    error: error.message,
                    code: error.code,
                    retryAfter: error.retryAfter,
                    blockedBy: error.blockedBy
                }), {
                    status,
                    headers: {
                        'Content-Type': 'application/json',
                        'Retry-After': error.retryAfter ? Math.ceil(error.retryAfter / 1000) : undefined
                    }
                });
            }
        }

        return originalFetch(url, options);
    };

    console.log('✅ Mock server with rate limiting is ready');
    console.log('📊 Rate limit status:', getRateLimitStatus());
}

/**
 * 清除模拟存储
 */
export function clearMockStorage() {
    localStorage.removeItem(STORAGE_KEY);
    console.log('✅ Mock storage cleared');
}
