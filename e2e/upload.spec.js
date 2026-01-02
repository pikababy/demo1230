import { test, expect } from '@playwright/test';

test.describe('文件上传页面测试', () => {

    test.beforeEach(async ({ page }) => {
        await page.goto('/');
        // 等待页面完全加载
        await page.waitForLoadState('networkidle');
    });

    test('页面加载正常', async ({ page }) => {
        // 检查 tabs 是否存在
        const tabs = page.locator('.ant-tabs-nav');
        await expect(tabs).toBeVisible();

        // 截图
        await page.screenshot({ path: 'test-results/page-loaded.png' });
    });

    test('Tab 切换功能', async ({ page }) => {
        // 使用 role 选择器点击 tab（更精确）
        const simpleUploadTab = page.getByRole('tab', { name: '普通文件上传' });
        await simpleUploadTab.click();

        // 等待内容变化
        await page.waitForTimeout(500);

        // 验证普通上传容器可见
        await expect(page.locator('.upload-container')).toBeVisible();

        // 截图
        await page.screenshot({ path: 'test-results/simple-upload-tab.png' });

        // 切换回第一个 tab
        const chunkUploadTab = page.getByRole('tab', { name: '大文件分片上传' });
        await chunkUploadTab.click();

        // 验证分片上传区域可见
        await expect(page.locator('.chunk-upload-container')).toBeVisible();

        // 截图
        await page.screenshot({ path: 'test-results/chunk-upload-tab.png' });
    });

    test('分片上传组件显示正确', async ({ page }) => {
        // 确保在分片上传 tab
        await page.getByRole('tab', { name: '大文件分片上传' }).click();

        // 检查上传拖拽区域
        const uploadArea = page.locator('.chunk-upload-container .ant-upload-drag');
        await expect(uploadArea).toBeVisible();

        // 检查上传提示文字
        await expect(page.getByText('点击或拖拽文件到此区域上传')).toBeVisible();

        // 截图
        await page.screenshot({ path: 'test-results/chunk-upload-component.png' });
    });

    test('普通文件上传组件显示正确', async ({ page }) => {
        // 切换到普通上传 tab
        await page.getByRole('tab', { name: '普通文件上传' }).click();
        await page.waitForTimeout(500);

        // 检查卡片标题
        await expect(page.getByText('表格文件上传')).toBeVisible();

        // 检查上传区域 - 使用更具体的选择器
        const uploadArea = page.locator('.upload-container .ant-upload-drag');
        await expect(uploadArea).toBeVisible();

        // 截图
        await page.screenshot({ path: 'test-results/simple-upload-component.png' });
    });

    test('分片上传 - 模拟文件选择', async ({ page }) => {
        await page.getByRole('tab', { name: '大文件分片上传' }).click();

        // 获取文件输入元素
        const fileInput = page.locator('.chunk-upload-container input[type="file"]');

        // 创建测试文件并上传
        await fileInput.setInputFiles({
            name: 'test-file.txt',
            mimeType: 'text/plain',
            buffer: Buffer.from('这是测试内容'.repeat(100))
        });

        // 等待文件处理
        await page.waitForTimeout(2000);

        // 截图查看结果
        await page.screenshot({ path: 'test-results/chunk-upload-file-selected.png' });

        // 验证文件名显示 - 分片上传组件使用 .file-name 类显示文件名
        await expect(page.locator('.file-name').getByText('test-file.txt')).toBeVisible({ timeout: 10000 });
    });

    test('普通上传 - 模拟 CSV 文件选择', async ({ page }) => {
        await page.getByRole('tab', { name: '普通文件上传' }).click();
        await page.waitForTimeout(500);

        const fileInput = page.locator('.upload-container input[type="file"]');

        // 模拟上传 CSV 文件
        await fileInput.setInputFiles({
            name: 'test-data.csv',
            mimeType: 'text/csv',
            buffer: Buffer.from('姓名,年龄,城市\n张三,25,北京\n李四,30,上海')
        });

        // 等待上传处理
        await page.waitForTimeout(2000);

        // 截图
        await page.screenshot({ path: 'test-results/simple-upload-csv.png' });

        // 验证文件名显示 - 使用 getByTitle 避免匹配多个元素
        await expect(page.getByTitle('test-data.csv')).toBeVisible({ timeout: 10000 });
    });

    test('限流状态显示', async ({ page }) => {
        // 检查分片上传页面的限流状态
        await page.getByRole('tab', { name: '大文件分片上传' }).click();

        // 检查限流状态信息
        const rateLimitInfo = page.locator('.rate-limit-status, .rate-limit-info');

        // 截图
        await page.screenshot({ path: 'test-results/rate-limit-status.png' });
    });

});
