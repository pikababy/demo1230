"""
Textual 演示应用 - 系统监控面板
展示 Textual 的主要组件和功能
"""

from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical, ScrollableContainer
from textual.widgets import (
    Header, Footer, Static, Button, DataTable, 
    Input, Label, ProgressBar, Log, Tabs, Tab, ContentSwitcher
)
from textual.reactive import reactive
from textual import on
import random
from datetime import datetime
import psutil


class SystemMonitor(Static):
    """系统监控组件"""
    
    cpu_usage = reactive(0.0)
    memory_usage = reactive(0.0)
    disk_usage = reactive(0.0)
    
    def compose(self) -> ComposeResult:
        yield Static("🖥️ 系统监控面板", classes="section-title")
        yield Static("CPU 使用率", classes="label")
        yield ProgressBar(total=100, id="cpu-bar")
        yield Static("内存使用率", classes="label")
        yield ProgressBar(total=100, id="memory-bar")
        yield Static("磁盘使用率", classes="label")
        yield ProgressBar(total=100, id="disk-bar")
        yield Static("", id="stats-text")
    
    def on_mount(self) -> None:
        """组件挂载时启动定时更新"""
        self.query_one("#cpu-bar", ProgressBar).update(progress=self.cpu_usage)
        self.query_one("#memory-bar", ProgressBar).update(progress=self.memory_usage)
        self.query_one("#disk-bar", ProgressBar).update(progress=self.disk_usage)
        self.set_interval(1.0, self.update_stats)
    
    def update_stats(self) -> None:
        """获取真实系统状态"""
        self.cpu_usage = psutil.cpu_percent(interval=None)
        self.memory_usage = psutil.virtual_memory().percent
        self.disk_usage = psutil.disk_usage('/').percent
        
        self.query_one("#cpu-bar", ProgressBar).update(progress=self.cpu_usage)
        self.query_one("#memory-bar", ProgressBar).update(progress=self.memory_usage)
        self.query_one("#disk-bar", ProgressBar).update(progress=self.disk_usage)
        
        self.query_one("#stats-text", Static).update(
            f"CPU: {self.cpu_usage:.1f}% | 内存: {self.memory_usage:.1f}% | 磁盘: {self.disk_usage:.1f}%"
        )


class TaskManager(Static):
    """任务管理组件"""
    
    task_counter = 3
    
    def compose(self) -> ComposeResult:
        yield Static("📋 任务管理", classes="section-title")
        yield Horizontal(
            Input(placeholder="输入新任务...", id="task-input"),
            Button("添加任务", id="add-task", variant="primary"),
            classes="input-row"
        )
        yield DataTable(id="task-table")
    
    def on_mount(self) -> None:
        """初始化表格"""
        table = self.query_one("#task-table", DataTable)
        table.add_columns("ID", "任务内容", "状态", "时间")
        table.add_row("1", "学习 Textual 框架", "✅ 完成", "14:00")
        table.add_row("2", "创建演示项目", "🔄 进行中", "14:30")
        table.add_row("3", "编写文档", "⏳ 待办", "15:00")
        table.cursor_type = "row"
    
    @on(Button.Pressed, "#add-task")
    def add_task(self) -> None:
        """添加新任务"""
        input_widget = self.query_one("#task-input", Input)
        task_text = input_widget.value.strip()
        
        if task_text:
            self.task_counter += 1
            table = self.query_one("#task-table", DataTable)
            current_time = datetime.now().strftime("%H:%M")
            table.add_row(str(self.task_counter), task_text, "⏳ 待办", current_time)
            input_widget.value = ""
            self.app.notify(f"✅ 任务已添加: {task_text}")
        else:
            self.app.notify("⚠️ 请输入任务内容", severity="warning")
    
    @on(Input.Submitted, "#task-input")
    def on_input_submitted(self) -> None:
        """回车键添加任务"""
        self.add_task()


class LogViewer(Static):
    """日志查看器组件"""
    
    def compose(self) -> ComposeResult:
        yield Static("📜 实时日志", classes="section-title")
        yield Horizontal(
            Button("生成日志", id="gen-log", variant="success"),
            Button("错误日志", id="error-log", variant="error"),
            Button("清空日志", id="clear-log", variant="warning"),
            classes="button-row"
        )
        yield Log(id="log-view", highlight=True, max_lines=100)
    
    def on_mount(self) -> None:
        """启动自动日志生成"""
        log = self.query_one("#log-view", Log)
        log.write_line("=== 日志系统启动 ===")
        self.set_interval(3.0, self.auto_log)
    
    def auto_log(self) -> None:
        """自动生成日志"""
        log = self.query_one("#log-view", Log)
        messages = [
            "[INFO] 系统运行正常",
            "[DEBUG] 心跳检测成功",
            "[INFO] 用户请求已处理",
            "[INFO] 定时任务执行完成",
            "[DEBUG] 缓存已更新",
        ]
        timestamp = datetime.now().strftime('%H:%M:%S')
        log.write_line(f"[{timestamp}] {random.choice(messages)}")
    
    @on(Button.Pressed, "#gen-log")
    def generate_log(self) -> None:
        """生成普通日志"""
        log = self.query_one("#log-view", Log)
        timestamp = datetime.now().strftime('%H:%M:%S')
        log.write_line(f"[{timestamp}] [INFO] 用户手动触发日志记录")
    
    @on(Button.Pressed, "#error-log")
    def generate_error_log(self) -> None:
        """生成错误日志"""
        log = self.query_one("#log-view", Log)
        timestamp = datetime.now().strftime('%H:%M:%S')
        log.write_line(f"[{timestamp}] [ERROR] 模拟错误: 连接超时")
        self.app.notify("⚠️ 已生成错误日志", severity="error")
    
    @on(Button.Pressed, "#clear-log")
    def clear_log(self) -> None:
        """清空日志"""
        log = self.query_one("#log-view", Log)
        log.clear()
        log.write_line("=== 日志已清空 ===")
        self.app.notify("日志已清空")


class DemoApp(App):
    """Textual 演示应用主类"""
    
    CSS = """
    Screen {
        background: $surface;
    }
    
    .section-title {
        text-style: bold;
        color: $primary;
        padding: 1 0;
        text-align: center;
    }
    
    .label {
        padding: 0 1;
        color: $text-muted;
    }
    
    #main-container {
        padding: 1;
    }
    
    Tabs {
        dock: top;
    }
    
    ContentSwitcher {
        height: 1fr;
        padding: 1;
    }
    
    SystemMonitor, TaskManager, LogViewer {
        border: round $primary;
        padding: 1 2;
        margin: 1;
        height: auto;
    }
    
    .input-row {
        height: 3;
        margin: 1 0;
    }
    
    .input-row Input {
        width: 3fr;
    }
    
    .input-row Button {
        width: 1fr;
        margin-left: 1;
    }
    
    .button-row {
        height: 3;
        margin: 1 0;
    }
    
    .button-row Button {
        margin-right: 1;
    }
    
    DataTable {
        height: 12;
        margin: 1 0;
    }
    
    Log {
        height: 12;
        border: solid $surface-lighten-2;
        margin: 1 0;
    }
    
    ProgressBar {
        margin: 0 1 1 1;
    }
    
    #stats-text {
        text-align: center;
        color: $success;
        margin-top: 1;
    }
    """
    
    BINDINGS = [
        ("q", "quit", "退出"),
        ("d", "toggle_dark", "切换主题"),
        ("1", "show_monitor", "监控"),
        ("2", "show_tasks", "任务"),
        ("3", "show_logs", "日志"),
    ]
    
    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield Container(
            Tabs(
                Tab("📊 系统监控", id="tab-monitor"),
                Tab("📋 任务管理", id="tab-tasks"),
                Tab("📜 日志查看", id="tab-logs"),
            ),
            ContentSwitcher(
                SystemMonitor(id="content-monitor"),
                TaskManager(id="content-tasks"),
                LogViewer(id="content-logs"),
                initial="content-monitor",
            ),
            id="main-container"
        )
        yield Footer()
    
    @on(Tabs.TabActivated)
    def on_tab_activated(self, event: Tabs.TabActivated) -> None:
        """切换标签页"""
        tab_id = event.tab.id
        content_id = tab_id.replace("tab-", "content-")
        self.query_one(ContentSwitcher).current = content_id
    
    def action_toggle_dark(self) -> None:
        """切换深色/浅色主题"""
        self.theme = "textual-light" if self.theme == "textual-dark" else "textual-dark"
        self.notify(f"主题已切换: {'浅色' if 'light' in self.theme else '深色'}")
    
    def action_show_monitor(self) -> None:
        """显示监控面板"""
        self.query_one(Tabs).active = "tab-monitor"
        self.query_one(ContentSwitcher).current = "content-monitor"
    
    def action_show_tasks(self) -> None:
        """显示任务管理"""
        self.query_one(Tabs).active = "tab-tasks"
        self.query_one(ContentSwitcher).current = "content-tasks"
    
    def action_show_logs(self) -> None:
        """显示日志查看"""
        self.query_one(Tabs).active = "tab-logs"
        self.query_one(ContentSwitcher).current = "content-logs"


def main():
    """程序入口"""
    app = DemoApp()
    app.run()


if __name__ == "__main__":
    main()
