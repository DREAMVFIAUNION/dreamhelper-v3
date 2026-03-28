"""Shell 终端执行技能

赋予 Agent 接管机器并在本地执行 shell 命令的能力。
包含安全限制和输出截断，以防破坏上下文或超时。
"""

import asyncio
import os
import subprocess
from typing import Any

from pydantic import Field
from ..skill_engine import BaseSkill, SkillSchema


class ShellExecSchema(SkillSchema):
    command: str = Field(description="要执行的完整命令语句（如 'npm install', 'git status', 'dir'）。严禁执行任何交互式命令（如 'vim' 或需要用户手动输入的命令）。")
    shell_type: str = Field(
        default="powershell", 
        description="Shell 类型: 'powershell', 'cmd', 或 'bash'"
    )
    require_admin: bool = Field(
        default=False, 
        description="是否需要管理员权限执行（如果是 Windows，这将在一独立窗口中弹起 UAC 授权弹窗请求用户确认。请仅在安装全局依赖、修改关键系统设置时使用）。"
    )
    timeout_seconds: int = Field(
        default=60, 
        description="命令执行超时时间（秒）"
    )


class ShellExecSkill(BaseSkill):
    name = "shell_exec"
    description = "执行本地系统终端命令 (CLI, Git Bash, cmd, powershell)，支持管理员提权。"
    category = "system"
    args_schema = ShellExecSchema
    tags = ["shell", "terminal", "cli", "git", "bash", "cmd", "powershell", "system", "run", "execute"]

    async def execute(self, **kwargs: Any) -> str:
        command = kwargs.get("command", "")
        if not command:
            return "❌ 错误: 空命令。"

        shell_type = kwargs.get("shell_type", "powershell").lower()
        require_admin = kwargs.get("require_admin", False)
        timeout_seconds = kwargs.get("timeout_seconds", 60)

        # 管理员提权模式 (Windows)
        if require_admin and os.name == 'nt':
            try:
                # 使用 powershell 的 Start-Process -Verb RunAs 来请求管理员权限
                # 注意：提权执行通常会在新窗口中打开，且无法轻易捕获 stdout 到当前进程。
                # 但对于某些确实需要提权的安装操作，这是唯一途径。
                ps_command = f'Start-Process {shell_type} -ArgumentList "-NoProfile -Command `"{command}`"" -Verb RunAs -Wait'
                process = await asyncio.create_subprocess_shell(
                    'powershell -Command "{}"'.format(ps_command.replace('"', '\\"')),
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                try:
                    await asyncio.wait_for(process.communicate(), timeout=timeout_seconds)
                    return f"✅ (管理员模式) 命令 '{command}' 已在新窗口请求执行并完毕。注：提权环境无法捕获标准输出日志。"
                except asyncio.TimeoutError:
                    process.kill()
                    return f"⚠️ (管理员模式) 命令执行超时 ({timeout_seconds}s)，进程已被强制终止。"
            except Exception as e:
                return f"❌ 提权执行失败: {str(e)}"

        # 普通模式 (捕获输出)
        executable = None
        if shell_type == "powershell":
            executable = "powershell.exe"
        elif shell_type == "cmd":
            executable = "cmd.exe"
        elif shell_type == "bash":
            executable = "bash" # 需系统有bash或Git Bash在环境变量中
        else:
            executable = None # default OS shell

        try:
            # 对于 cmd/powershell，我们通常直接以 shell=True 执行
            # 为了确保在 Windows 上正确以指定 shell 运行，我们直接将执行器包装在命令中
            cmd_to_run = command
            if os.name == 'nt':
                if shell_type == "powershell":
                    cmd_to_run = f'powershell -NoProfile -Command "{command}"'
                elif shell_type == "bash":
                    cmd_to_run = f'bash -c "{command}"'
            else:
                if shell_type == "bash":
                    cmd_to_run = f'/bin/bash -c "{command}"'

            process = await asyncio.create_subprocess_shell(
                cmd_to_run,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                shell=True
            )

            try:
                stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=timeout_seconds)
            except asyncio.TimeoutError:
                process.kill()
                return f"⚠️ 命令执行超时 ({timeout_seconds}s)，进程已被强制终止。\n当前命令: {command}"

            stdout_text = stdout.decode('utf-8', errors='replace').strip()
            stderr_text = stderr.decode('utf-8', errors='replace').strip()

            exit_code = process.returncode
            
            # 防撑爆上下文限制
            MAX_LEN = 4000
            if len(stdout_text) > MAX_LEN:
                stdout_text = stdout_text[:MAX_LEN] + f"\n... (输出过长，已截断 remaining {len(stdout_text) - MAX_LEN} chars)"
            if len(stderr_text) > MAX_LEN:
                stderr_text = stderr_text[:MAX_LEN] + f"\n... (错误信息过长，已截断 remaining {len(stderr_text) - MAX_LEN} chars)"

            result = []
            if exit_code == 0:
                result.append(f"✅ 命令执行成功 (Exit: 0)")
            else:
                result.append(f"❌ 命令执行失败 (Exit: {exit_code})")
            
            if stdout_text:
                result.append(f"--- Standard Output ---\n{stdout_text}")
            if stderr_text:
                result.append(f"--- Standard Error ---\n{stderr_text}")

            if not stdout_text and not stderr_text:
                result.append("(No output)")

            return "\n".join(result)

        except Exception as e:
            return f"❌ 执行异常: {str(e)}"
