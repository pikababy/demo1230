"""
Git TUI - 终端 Git 可视化操作工具
使用 Textual 构建现代化的 Git 操作界面
"""

from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical, ScrollableContainer
from textual.widgets import (
    Header, Footer, Static, Button, DataTable, 
    Input, Label, Log, Tabs, Tab, ContentSwitcher,
    Tree, RichLog
)
from textual.reactive import reactive
from textual import on
from textual.binding import Binding
from rich.syntax import Syntax
from rich.text import Text
import subprocess
import os
from datetime import datetime


def run_git_command(cmd: list[str], cwd: str = None) -> tuple[bool, str]:
    """执行 Git 命令并返回结果"""
    try:
        result = subprocess.run(
            ["git"] + cmd,
            capture_output=True,
            text=True,
            cwd=cwd or os.getcwd()
        )
        if result.returncode == 0:
            return True, result.stdout.strip()
        else:
            return False, result.stderr.strip()
    except Exception as e:
        return False, str(e)


def get_repo_root() -> str | None:
    """获取 Git 仓库根目录"""
    success, output = run_git_command(["rev-parse", "--show-toplevel"])
    return output if success else None


class GitStatus(Static):
    """Git 状态面板"""
    
    def compose(self) -> ComposeResult:
        yield Static("📊 工作区状态", classes="section-title")
        yield Horizontal(
            Button("刷新", id="refresh-status", variant="primary"),
            Button("暂存全部", id="stage-all", variant="success"),
            Button("取消暂存", id="unstage-all", variant="warning"),
            classes="button-row"
        )
        yield Static("", id="repo-info", classes="repo-info")
        yield Static("📁 已暂存", classes="subsection-title")
        yield DataTable(id="staged-table")
        yield Static("📝 未暂存", classes="subsection-title")
        yield DataTable(id="unstaged-table")
        yield Static("❓ 未跟踪", classes="subsection-title")
        yield DataTable(id="untracked-table")
    
    def on_mount(self) -> None:
        """初始化表格"""
        for table_id in ["staged-table", "unstaged-table", "untracked-table"]:
            table = self.query_one(f"#{table_id}", DataTable)
            table.add_columns("状态", "文件")
            table.cursor_type = "row"
        self.refresh_status()
    
    def refresh_status(self) -> None:
        """刷新 Git 状态"""
        repo_root = get_repo_root()
        repo_info = self.query_one("#repo-info", Static)
        
        if not repo_root:
            repo_info.update("[red]⚠️ 当前目录不是 Git 仓库[/red]")
            return
        
        # 获取分支信息
        success, branch = run_git_command(["branch", "--show-current"])
        if success:
            repo_info.update(f"[green]📂 {repo_root}[/green]\n[cyan]🌿 分支: {branch}[/cyan]")
        
        # 获取状态
        success, status = run_git_command(["status", "--porcelain"])
        
        staged_table = self.query_one("#staged-table", DataTable)
        unstaged_table = self.query_one("#unstaged-table", DataTable)
        untracked_table = self.query_one("#untracked-table", DataTable)
        
        # 清空表格
        staged_table.clear()
        unstaged_table.clear()
        untracked_table.clear()
        
        if not status:
            return
        
        for line in status.split("\n"):
            if len(line) < 3:
                continue
            
            index_status = line[0]
            worktree_status = line[1]
            filename = line[3:]
            
            # 已暂存的更改
            if index_status in "MADRC":
                status_map = {"M": "修改", "A": "新增", "D": "删除", "R": "重命名", "C": "复制"}
                staged_table.add_row(f"[green]{status_map.get(index_status, index_status)}[/green]", filename)
            
            # 未暂存的更改
            if worktree_status in "MD":
                status_map = {"M": "修改", "D": "删除"}
                unstaged_table.add_row(f"[yellow]{status_map.get(worktree_status, worktree_status)}[/yellow]", filename)
            
            # 未跟踪的文件
            if index_status == "?" and worktree_status == "?":
                untracked_table.add_row("[red]新文件[/red]", filename)
    
    @on(Button.Pressed, "#refresh-status")
    def on_refresh(self) -> None:
        self.refresh_status()
        self.app.notify("状态已刷新")
    
    @on(Button.Pressed, "#stage-all")
    def on_stage_all(self) -> None:
        success, output = run_git_command(["add", "-A"])
        if success:
            self.refresh_status()
            self.app.notify("✅ 已暂存所有更改")
        else:
            self.app.notify(f"❌ 暂存失败: {output}", severity="error")
    
    @on(Button.Pressed, "#unstage-all")
    def on_unstage_all(self) -> None:
        success, output = run_git_command(["reset", "HEAD"])
        if success:
            self.refresh_status()
            self.app.notify("✅ 已取消所有暂存")
        else:
            self.app.notify(f"❌ 操作失败: {output}", severity="error")


class GitLog(Static):
    """Git 提交历史面板"""
    
    def compose(self) -> ComposeResult:
        yield Static("📜 提交历史", classes="section-title")
        yield Horizontal(
            Button("刷新", id="refresh-log", variant="primary"),
            Button("显示更多", id="load-more", variant="default"),
            classes="button-row"
        )
        yield DataTable(id="log-table")
        yield Static("", id="commit-detail", classes="commit-detail")
    
    def on_mount(self) -> None:
        table = self.query_one("#log-table", DataTable)
        table.add_columns("哈希", "作者", "日期", "提交信息")
        table.cursor_type = "row"
        self.load_commits(20)
    
    def load_commits(self, count: int = 20) -> None:
        """加载提交历史"""
        success, output = run_git_command([
            "log", f"-{count}", 
            "--pretty=format:%h|%an|%ar|%s"
        ])
        
        table = self.query_one("#log-table", DataTable)
        table.clear()
        
        if not success or not output:
            return
        
        for line in output.split("\n"):
            parts = line.split("|", 3)
            if len(parts) == 4:
                hash_val, author, date, message = parts
                table.add_row(
                    f"[cyan]{hash_val}[/cyan]",
                    author,
                    f"[dim]{date}[/dim]",
                    message[:50] + "..." if len(message) > 50 else message
                )
    
    @on(Button.Pressed, "#refresh-log")
    def on_refresh(self) -> None:
        self.load_commits(20)
        self.app.notify("历史已刷新")
    
    @on(Button.Pressed, "#load-more")
    def on_load_more(self) -> None:
        table = self.query_one("#log-table", DataTable)
        current_count = table.row_count
        self.load_commits(current_count + 20)
        self.app.notify(f"已加载 {table.row_count} 条记录")
    
    @on(DataTable.RowSelected, "#log-table")
    def on_row_selected(self, event: DataTable.RowSelected) -> None:
        """显示提交详情"""
        table = self.query_one("#log-table", DataTable)
        row_key = event.row_key
        if row_key:
            # 获取哈希值（去除颜色标记）
            cell_value = table.get_cell_at((event.cursor_row, 0))
            # 提取哈希
            hash_val = str(cell_value).replace("[cyan]", "").replace("[/cyan]", "")
            
            success, detail = run_git_command(["show", "--stat", hash_val])
            if success:
                detail_widget = self.query_one("#commit-detail", Static)
                detail_widget.update(f"[dim]{detail[:500]}...[/dim]" if len(detail) > 500 else f"[dim]{detail}[/dim]")


class GitBranches(Static):
    """Git 分支管理面板"""
    
    def compose(self) -> ComposeResult:
        yield Static("🌿 分支管理", classes="section-title")
        yield Horizontal(
            Button("刷新", id="refresh-branches", variant="primary"),
            Button("拉取", id="git-pull", variant="success"),
            Button("推送", id="git-push", variant="warning"),
            classes="button-row"
        )
        yield Horizontal(
            Input(placeholder="新分支名称...", id="new-branch-input"),
            Button("创建分支", id="create-branch", variant="primary"),
            classes="input-row"
        )
        yield Static("本地分支", classes="subsection-title")
        yield DataTable(id="local-branches-table")
        yield Static("远程分支", classes="subsection-title")
        yield DataTable(id="remote-branches-table")
    
    def on_mount(self) -> None:
        for table_id in ["local-branches-table", "remote-branches-table"]:
            table = self.query_one(f"#{table_id}", DataTable)
            table.add_columns("状态", "分支名", "最后提交")
            table.cursor_type = "row"
        self.refresh_branches()
    
    def refresh_branches(self) -> None:
        """刷新分支列表"""
        # 本地分支
        success, output = run_git_command(["branch", "-v"])
        local_table = self.query_one("#local-branches-table", DataTable)
        local_table.clear()
        
        if success and output:
            for line in output.split("\n"):
                line = line.strip()
                if not line:
                    continue
                
                is_current = line.startswith("*")
                parts = line.lstrip("* ").split(None, 2)
                
                if len(parts) >= 2:
                    branch_name = parts[0]
                    commit_info = parts[1] if len(parts) > 1 else ""
                    message = parts[2] if len(parts) > 2 else ""
                    
                    status = "[green]●[/green]" if is_current else "[dim]○[/dim]"
                    local_table.add_row(status, branch_name, f"{commit_info} {message}"[:40])
        
        # 远程分支
        success, output = run_git_command(["branch", "-r"])
        remote_table = self.query_one("#remote-branches-table", DataTable)
        remote_table.clear()
        
        if success and output:
            for line in output.split("\n"):
                branch = line.strip()
                if branch and "->" not in branch:
                    remote_table.add_row("[cyan]→[/cyan]", branch, "")
    
    @on(Button.Pressed, "#refresh-branches")
    def on_refresh(self) -> None:
        self.refresh_branches()
        self.app.notify("分支已刷新")
    
    @on(Button.Pressed, "#git-pull")
    def on_pull(self) -> None:
        self.app.notify("正在拉取...")
        success, output = run_git_command(["pull"])
        if success:
            self.refresh_branches()
            self.app.notify("✅ 拉取成功")
        else:
            self.app.notify(f"❌ 拉取失败: {output[:50]}", severity="error")
    
    @on(Button.Pressed, "#git-push")
    def on_push(self) -> None:
        self.app.notify("正在推送...")
        success, output = run_git_command(["push"])
        if success:
            self.app.notify("✅ 推送成功")
        else:
            self.app.notify(f"❌ 推送失败: {output[:50]}", severity="error")
    
    @on(Button.Pressed, "#create-branch")
    def on_create_branch(self) -> None:
        input_widget = self.query_one("#new-branch-input", Input)
        branch_name = input_widget.value.strip()
        
        if not branch_name:
            self.app.notify("请输入分支名称", severity="warning")
            return
        
        success, output = run_git_command(["checkout", "-b", branch_name])
        if success:
            input_widget.value = ""
            self.refresh_branches()
            self.app.notify(f"✅ 已创建并切换到分支: {branch_name}")
        else:
            self.app.notify(f"❌ 创建失败: {output}", severity="error")
    
    @on(DataTable.RowSelected, "#local-branches-table")
    def on_branch_selected(self, event: DataTable.RowSelected) -> None:
        """切换到选中的分支"""
        table = self.query_one("#local-branches-table", DataTable)
        branch_name = str(table.get_cell_at((event.cursor_row, 1)))
        
        success, output = run_git_command(["checkout", branch_name])
        if success:
            self.refresh_branches()
            self.app.notify(f"✅ 已切换到分支: {branch_name}")
        else:
            self.app.notify(f"❌ 切换失败: {output}", severity="error")


class GitCommit(Static):
    """Git 提交面板"""
    
    def compose(self) -> ComposeResult:
        yield Static("✍️ 提交更改", classes="section-title")
        yield Static("", id="changes-summary")
        yield Input(placeholder="提交信息...", id="commit-message")
        yield Horizontal(
            Button("提交", id="do-commit", variant="success"),
            Button("提交并推送", id="commit-push", variant="primary"),
            classes="button-row"
        )
        yield Static("快速操作", classes="subsection-title")
        yield Horizontal(
            Button("撤销上次提交", id="undo-commit", variant="warning"),
            Button("修改上次提交", id="amend-commit", variant="default"),
            classes="button-row"
        )
        yield RichLog(id="commit-log", highlight=True, markup=True)
    
    def on_mount(self) -> None:
        self.update_summary()
    
    def update_summary(self) -> None:
        """更新变更摘要"""
        success, status = run_git_command(["status", "--short"])
        summary = self.query_one("#changes-summary", Static)
        
        if success:
            lines = status.split("\n") if status else []
            staged = sum(1 for l in lines if l and l[0] in "MADRC")
            unstaged = sum(1 for l in lines if l and len(l) > 1 and l[1] in "MD")
            untracked = sum(1 for l in lines if l.startswith("??"))
            
            summary.update(
                f"[green]已暂存: {staged}[/green] | "
                f"[yellow]未暂存: {unstaged}[/yellow] | "
                f"[red]未跟踪: {untracked}[/red]"
            )
        else:
            summary.update("[red]无法获取状态[/red]")
    
    def log_message(self, message: str) -> None:
        """写入日志"""
        log = self.query_one("#commit-log", RichLog)
        timestamp = datetime.now().strftime("%H:%M:%S")
        log.write(f"[dim]{timestamp}[/dim] {message}")
    
    @on(Button.Pressed, "#do-commit")
    def on_commit(self) -> None:
        input_widget = self.query_one("#commit-message", Input)
        message = input_widget.value.strip()
        
        if not message:
            self.app.notify("请输入提交信息", severity="warning")
            return
        
        success, output = run_git_command(["commit", "-m", message])
        if success:
            input_widget.value = ""
            self.update_summary()
            self.log_message(f"[green]✅ 提交成功[/green]: {message}")
            self.app.notify("✅ 提交成功")
        else:
            self.log_message(f"[red]❌ 提交失败[/red]: {output}")
            self.app.notify(f"❌ 提交失败", severity="error")
    
    @on(Button.Pressed, "#commit-push")
    def on_commit_push(self) -> None:
        input_widget = self.query_one("#commit-message", Input)
        message = input_widget.value.strip()
        
        if not message:
            self.app.notify("请输入提交信息", severity="warning")
            return
        
        # 先提交
        success, output = run_git_command(["commit", "-m", message])
        if not success:
            self.log_message(f"[red]❌ 提交失败[/red]: {output}")
            return
        
        self.log_message(f"[green]✅ 提交成功[/green]: {message}")
        
        # 再推送
        success, output = run_git_command(["push"])
        if success:
            input_widget.value = ""
            self.update_summary()
            self.log_message("[green]✅ 推送成功[/green]")
            self.app.notify("✅ 提交并推送成功")
        else:
            self.log_message(f"[yellow]⚠️ 推送失败[/yellow]: {output}")
            self.app.notify("提交成功，但推送失败", severity="warning")
    
    @on(Button.Pressed, "#undo-commit")
    def on_undo_commit(self) -> None:
        success, output = run_git_command(["reset", "--soft", "HEAD~1"])
        if success:
            self.update_summary()
            self.log_message("[yellow]↩️ 已撤销上次提交[/yellow]")
            self.app.notify("✅ 已撤销上次提交")
        else:
            self.log_message(f"[red]❌ 操作失败[/red]: {output}")
            self.app.notify("❌ 操作失败", severity="error")
    
    @on(Button.Pressed, "#amend-commit")
    def on_amend_commit(self) -> None:
        input_widget = self.query_one("#commit-message", Input)
        message = input_widget.value.strip()
        
        if message:
            success, output = run_git_command(["commit", "--amend", "-m", message])
        else:
            success, output = run_git_command(["commit", "--amend", "--no-edit"])
        
        if success:
            input_widget.value = ""
            self.log_message("[green]✏️ 已修改上次提交[/green]")
            self.app.notify("✅ 已修改上次提交")
        else:
            self.log_message(f"[red]❌ 操作失败[/red]: {output}")
            self.app.notify("❌ 操作失败", severity="error")


class GitTUI(App):
    """Git TUI 主应用"""
    
    CSS = """
    Screen {
        background: $surface;
    }
    
    .section-title {
        text-style: bold;
        color: $primary;
        padding: 1 0;
        text-align: center;
        background: $primary-background;
    }
    
    .subsection-title {
        color: $text-muted;
        padding: 1 0 0 0;
        text-style: italic;
    }
    
    .repo-info {
        padding: 1;
        margin: 1 0;
        border: solid $success;
    }
    
    .commit-detail {
        padding: 1;
        margin: 1 0;
        border: solid $primary;
        max-height: 10;
        overflow-y: auto;
    }
    
    #main-container {
        padding: 0 1;
    }
    
    Tabs {
        dock: top;
    }
    
    ContentSwitcher {
        height: 1fr;
        padding: 1;
    }
    
    GitStatus, GitLog, GitBranches, GitCommit {
        height: auto;
        padding: 1;
    }
    
    .button-row {
        height: 3;
        margin: 1 0;
    }
    
    .button-row Button {
        margin-right: 1;
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
    
    DataTable {
        height: 8;
        margin: 0 0 1 0;
        border: solid $surface-lighten-2;
    }
    
    Input {
        margin: 1 0;
    }
    
    RichLog {
        height: 8;
        border: solid $surface-lighten-2;
        margin: 1 0;
    }
    """
    
    BINDINGS = [
        Binding("q", "quit", "退出"),
        Binding("d", "toggle_dark", "主题"),
        Binding("r", "refresh", "刷新"),
        Binding("1", "show_status", "状态"),
        Binding("2", "show_log", "历史"),
        Binding("3", "show_branches", "分支"),
        Binding("4", "show_commit", "提交"),
    ]
    
    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield Container(
            Tabs(
                Tab("📊 状态", id="tab-status"),
                Tab("📜 历史", id="tab-log"),
                Tab("🌿 分支", id="tab-branches"),
                Tab("✍️ 提交", id="tab-commit"),
            ),
            ContentSwitcher(
                ScrollableContainer(GitStatus(), id="content-status"),
                ScrollableContainer(GitLog(), id="content-log"),
                ScrollableContainer(GitBranches(), id="content-branches"),
                ScrollableContainer(GitCommit(), id="content-commit"),
                initial="content-status",
            ),
            id="main-container"
        )
        yield Footer()
    
    @on(Tabs.TabActivated)
    def on_tab_activated(self, event: Tabs.TabActivated) -> None:
        tab_id = event.tab.id
        content_id = tab_id.replace("tab-", "content-")
        self.query_one(ContentSwitcher).current = content_id
    
    def action_toggle_dark(self) -> None:
        self.theme = "textual-light" if self.theme == "textual-dark" else "textual-dark"
    
    def action_refresh(self) -> None:
        """刷新当前页面"""
        switcher = self.query_one(ContentSwitcher)
        current = switcher.current
        
        if current == "content-status":
            self.query_one(GitStatus).refresh_status()
        elif current == "content-log":
            self.query_one(GitLog).load_commits(20)
        elif current == "content-branches":
            self.query_one(GitBranches).refresh_branches()
        elif current == "content-commit":
            self.query_one(GitCommit).update_summary()
        
        self.notify("已刷新")
    
    def action_show_status(self) -> None:
        self.query_one(Tabs).active = "tab-status"
        self.query_one(ContentSwitcher).current = "content-status"
    
    def action_show_log(self) -> None:
        self.query_one(Tabs).active = "tab-log"
        self.query_one(ContentSwitcher).current = "content-log"
    
    def action_show_branches(self) -> None:
        self.query_one(Tabs).active = "tab-branches"
        self.query_one(ContentSwitcher).current = "content-branches"
    
    def action_show_commit(self) -> None:
        self.query_one(Tabs).active = "tab-commit"
        self.query_one(ContentSwitcher).current = "content-commit"


def main():
    """程序入口"""
    app = GitTUI()
    app.title = "Git TUI"
    app.run()


if __name__ == "__main__":
    main()
