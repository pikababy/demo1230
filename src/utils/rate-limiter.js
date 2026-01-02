/**
 * 限流算法实现
 * 包含：令牌桶、漏桶、滑动窗口
 */

/**
 * 令牌桶限流器 (Token Bucket) - 推荐
 * 特点：允许突发流量，适合 API 限流
 */
export class TokenBucketLimiter {
    constructor(options = {}) {
        this.capacity = options.capacity || 100;      // 桶容量（最大令牌数）
        this.refillRate = options.refillRate || 10;   // 每秒补充令牌数
        this.buckets = new Map();
    }

    /**
     * 检查是否允许请求
     * @param {string} key - 限流键（如 IP 或用户ID）
     * @param {number} tokensNeeded - 需要消耗的令牌数
     */
    isAllowed(key, tokensNeeded = 1) {
        const now = Date.now();
        let bucket = this.buckets.get(key);

        if (!bucket) {
            bucket = { tokens: this.capacity, lastRefillTime: now };
            this.buckets.set(key, bucket);
        }

        // 计算应该补充的令牌数
        const elapsed = (now - bucket.lastRefillTime) / 1000;
        const tokensToAdd = elapsed * this.refillRate;

        bucket.tokens = Math.min(this.capacity, bucket.tokens + tokensToAdd);
        bucket.lastRefillTime = now;

        // 检查是否有足够的令牌
        if (bucket.tokens < tokensNeeded) {
            return {
                allowed: false,
                remaining: Math.floor(bucket.tokens),
                retryAfter: Math.ceil((tokensNeeded - bucket.tokens) / this.refillRate * 1000)
            };
        }

        bucket.tokens -= tokensNeeded;
        return {
            allowed: true,
            remaining: Math.floor(bucket.tokens),
            retryAfter: 0
        };
    }

    /**
     * 获取当前状态
     */
    getStatus(key) {
        const bucket = this.buckets.get(key);
        if (!bucket) {
            return { tokens: this.capacity, capacity: this.capacity };
        }

        const now = Date.now();
        const elapsed = (now - bucket.lastRefillTime) / 1000;
        const tokensToAdd = elapsed * this.refillRate;
        const currentTokens = Math.min(this.capacity, bucket.tokens + tokensToAdd);

        return {
            tokens: Math.floor(currentTokens),
            capacity: this.capacity,
            refillRate: this.refillRate
        };
    }

    /**
     * 清理过期的桶（内存优化）
     */
    cleanup(maxAge = 3600000) {
        const now = Date.now();
        for (const [key, bucket] of this.buckets) {
            if (now - bucket.lastRefillTime > maxAge) {
                this.buckets.delete(key);
            }
        }
    }
}

/**
 * 漏桶限流器 (Leaky Bucket)
 * 特点：平滑流量，固定速率处理请求
 */
export class LeakyBucketLimiter {
    constructor(options = {}) {
        this.capacity = options.capacity || 100;     // 桶容量
        this.leakRate = options.leakRate || 10;      // 每秒漏出数量
        this.buckets = new Map();
    }

    isAllowed(key) {
        const now = Date.now();
        let bucket = this.buckets.get(key);

        if (!bucket) {
            bucket = { water: 0, lastLeakTime: now };
            this.buckets.set(key, bucket);
        }

        // 计算漏出的水量
        const elapsed = (now - bucket.lastLeakTime) / 1000;
        const leaked = elapsed * this.leakRate;

        bucket.water = Math.max(0, bucket.water - leaked);
        bucket.lastLeakTime = now;

        // 检查是否有空间
        if (bucket.water >= this.capacity) {
            return {
                allowed: false,
                currentLevel: Math.floor(bucket.water),
                retryAfter: Math.ceil((bucket.water - this.capacity + 1) / this.leakRate * 1000)
            };
        }

        bucket.water++;
        return {
            allowed: true,
            currentLevel: Math.floor(bucket.water),
            retryAfter: 0
        };
    }
}

/**
 * 滑动窗口限流器 (Sliding Window)
 * 特点：精确限流，无边界问题
 */
export class SlidingWindowLimiter {
    constructor(options = {}) {
        this.windowSize = options.windowSize || 60000; // 窗口大小(ms)
        this.maxRequests = options.maxRequests || 100; // 窗口内最大请求数
        this.windows = new Map();
    }

    isAllowed(key) {
        const now = Date.now();
        let requests = this.windows.get(key);

        if (!requests) {
            requests = [];
            this.windows.set(key, requests);
        }

        // 清理过期的请求记录
        const windowStart = now - this.windowSize;
        while (requests.length > 0 && requests[0] < windowStart) {
            requests.shift();
        }

        // 检查是否超过限制
        if (requests.length >= this.maxRequests) {
            const oldestRequest = requests[0];
            const retryAfter = oldestRequest + this.windowSize - now;
            return {
                allowed: false,
                currentCount: requests.length,
                retryAfter: Math.max(0, retryAfter)
            };
        }

        requests.push(now);
        return {
            allowed: true,
            currentCount: requests.length,
            retryAfter: 0
        };
    }

    getStatus(key) {
        const requests = this.windows.get(key);
        if (!requests) {
            return { count: 0, limit: this.maxRequests };
        }

        const now = Date.now();
        const windowStart = now - this.windowSize;
        const validRequests = requests.filter(t => t >= windowStart);

        return {
            count: validRequests.length,
            limit: this.maxRequests,
            remaining: this.maxRequests - validRequests.length
        };
    }
}

/**
 * 多级限流器
 * 同时应用多个限流策略
 */
export class MultiLevelLimiter {
    constructor() {
        this.limiters = [];
    }

    /**
     * 添加限流器
     * @param {string} name - 限流器名称
     * @param {object} limiter - 限流器实例
     * @param {function} getKey - 获取限流键的函数
     * @param {number} tokensNeeded - 需要的令牌数（仅令牌桶）
     */
    addLimiter(name, limiter, getKey, tokensNeeded = 1) {
        this.limiters.push({ name, limiter, getKey, tokensNeeded });
    }

    /**
     * 检查所有限流器
     */
    isAllowed(context) {
        const results = [];

        for (const { name, limiter, getKey, tokensNeeded } of this.limiters) {
            const key = getKey(context);
            const result = limiter.isAllowed(key, tokensNeeded);
            results.push({ name, key, ...result });

            if (!result.allowed) {
                return {
                    allowed: false,
                    blockedBy: name,
                    retryAfter: result.retryAfter,
                    results
                };
            }
        }

        return { allowed: true, results };
    }
}

/**
 * 创建预配置的上传限流器
 */
export function createUploadRateLimiter() {
    const multiLimiter = new MultiLevelLimiter();

    // 1. 全局限流：每秒最多处理 1000 个分片
    const globalLimiter = new TokenBucketLimiter({
        capacity: 1000,
        refillRate: 1000
    });
    multiLimiter.addLimiter('global', globalLimiter, () => 'global');

    // 2. IP 限流：每 IP 每秒最多 20 个分片
    const ipLimiter = new TokenBucketLimiter({
        capacity: 20,
        refillRate: 20
    });
    multiLimiter.addLimiter('ip', ipLimiter, (ctx) => ctx.ip || 'unknown');

    // 3. 用户限流：每用户每分钟最多 100 个分片
    const userLimiter = new SlidingWindowLimiter({
        windowSize: 60000,
        maxRequests: 100
    });
    multiLimiter.addLimiter('user', userLimiter, (ctx) => ctx.userId || ctx.ip || 'anonymous');

    return {
        multiLimiter,
        globalLimiter,
        ipLimiter,
        userLimiter,

        // 快捷方法
        check(context) {
            return multiLimiter.isAllowed(context);
        },

        getStatus(context) {
            return {
                global: globalLimiter.getStatus('global'),
                ip: ipLimiter.getStatus(context.ip || 'unknown'),
                user: userLimiter.getStatus(context.userId || context.ip || 'anonymous')
            };
        }
    };
}
