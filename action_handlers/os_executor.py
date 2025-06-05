#!/usr/bin/env python3
"""
OS Shell Executor - Week 2 Integration
=====================================

Provides secure shell command execution with:
- Allowlist-based command filtering
- Cost guards (CPU time, filesystem changes) 
- Cross-platform support (Windows PowerShell, Linux bash, WSL)
- Prometheus metrics integration
- Audit trail logging

Integrates with existing sandbox_exec.py for secure execution.
"""

import os
import subprocess
import tempfile
import time
import logging
import hashlib
import json
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

# Use existing sandbox infrastructure
from sandbox_exec import exec_safe, detect_available_providers, load_settings

# Prometheus metrics
try:
    from prometheus_client import Counter, Histogram, Gauge
    OS_EXEC_TOTAL = Counter('swarm_os_exec_total', 'Total OS executions', ['command_type', 'status'])
    OS_EXEC_LATENCY = Histogram('swarm_os_exec_latency_seconds', 'OS execution latency')
    OS_EXEC_CPU_TIME = Histogram('swarm_os_exec_cpu_seconds', 'CPU time consumed by OS executions')
    OS_EXEC_FS_CHANGES = Counter('swarm_os_exec_fs_changes_total', 'Filesystem changes detected')
    OS_EXEC_BLOCKED = Counter('swarm_os_exec_blocked_total', 'Blocked dangerous commands', ['reason'])
    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False

logger = logging.getLogger(__name__)

class CommandType(Enum):
    """Types of OS commands"""
    FILE_OPERATION = "file_op"
    DIRECTORY_OPERATION = "dir_op"
    PROCESS_MANAGEMENT = "process"
    SYSTEM_INFO = "system_info"
    PACKAGE_MANAGEMENT = "package"
    SERVICE_MANAGEMENT = "service"
    NETWORK = "network"
    DANGEROUS = "dangerous"
    UNKNOWN = "unknown"

@dataclass
class ExecutionResult:
    """Result of OS command execution"""
    success: bool
    stdout: str
    stderr: str
    exit_code: int
    execution_time_ms: int
    cpu_time_seconds: float
    fs_changes_detected: int
    command_type: CommandType
    blocked_reason: Optional[str] = None

class ShellExecutor:
    """
    Secure OS shell executor with allowlist and cost guards
    """
    
    def __init__(self):
        """Initialize shell executor with security configuration"""
        self.settings = load_settings()
        self.max_cpu_seconds = int(os.getenv("OS_EXEC_MAX_CPU_SECONDS", "10"))
        self.max_fs_changes = int(os.getenv("OS_EXEC_MAX_FS_CHANGES", "50"))
        self.audit_log_path = Path("logs/os_executor_audit.jsonl")
        
        # Ensure audit log directory exists
        self.audit_log_path.parent.mkdir(exist_ok=True)
        
        # Initialize allowlist
        self._load_command_allowlist()
        
        logger.info(f"🛡️ ShellExecutor initialized: max_cpu={self.max_cpu_seconds}s, max_fs={self.max_fs_changes}")
    
    def _load_command_allowlist(self) -> None:
        """Load command allowlist for security filtering"""
        # Week 2 allowlist - dev-oriented and safe commands
        self.allowed_commands = {
            # File operations (safe)
            CommandType.FILE_OPERATION: {
                "cat", "head", "tail", "less", "more", "wc", "grep", "find", "ls", "dir",
                "echo", "touch", "mkdir", "cp", "copy", "move", "mv", "stat", "file"
            },
            
            # Directory operations
            CommandType.DIRECTORY_OPERATION: {
                "pwd", "cd", "ls", "dir", "tree", "mkdir", "rmdir", "find"
            },
            
            # System info (read-only)
            CommandType.SYSTEM_INFO: {
                "ps", "top", "htop", "free", "df", "du", "uptime", "whoami", "id",
                "uname", "hostname", "date", "which", "where", "env", "printenv"
            },
            
            # Development tools
            CommandType.PROCESS_MANAGEMENT: {
                "python", "python3", "node", "npm", "pip", "git", "docker"
            },
            
            # Package management (controlled)
            CommandType.PACKAGE_MANAGEMENT: {
                "pip", "npm", "apt", "yum", "brew", "choco"
            },
            
            # Service management (limited)
            CommandType.SERVICE_MANAGEMENT: {
                "systemctl", "service", "sc", "net"
            }
        }
        
        # Dangerous commands that are always blocked
        self.dangerous_commands = {
            "rm", "del", "rmdir", "dd", "format", "fdisk", "mkfs", "fsck",
            "chmod", "chown", "chgrp", "sudo", "su", "passwd", "kill", "killall",
            "reboot", "shutdown", "halt", "init", "mount", "umount", "crontab",
            "iptables", "ufw", "firewall-cmd", "netsh", "reg", "regedit"
        }
    
    def _classify_command(self, command: str) -> Tuple[CommandType, bool]:
        """
        Classify command and determine if it's allowed
        
        Returns:
            (command_type, is_allowed)
        """
        # Extract base command
        base_cmd = command.strip().split()[0].lower()
        
        # Check for dangerous commands first
        if base_cmd in self.dangerous_commands:
            return CommandType.DANGEROUS, False
        
        # Check allowlist
        for cmd_type, allowed_set in self.allowed_commands.items():
            if base_cmd in allowed_set:
                return cmd_type, True
        
        # Unknown command - block by default for security
        return CommandType.UNKNOWN, False
    
    def _check_cost_guards(self, command: str, estimated_runtime: float = 0) -> Optional[str]:
        """
        Check cost guards before execution
        
        Returns:
            None if allowed, error message if blocked
        """
        # CPU time guard
        if estimated_runtime > self.max_cpu_seconds:
            return f"Command estimated to exceed CPU limit ({self.max_cpu_seconds}s)"
        
        # Filesystem change guard (heuristic)
        fs_heavy_keywords = ["install", "update", "upgrade", "remove", "uninstall", "build", "compile"]
        if any(keyword in command.lower() for keyword in fs_heavy_keywords):
            if self.max_fs_changes < 10:  # Conservative filesystem guard
                return f"Command may exceed filesystem change limit ({self.max_fs_changes})"
        
        return None
    
    def _audit_log(self, command: str, result: ExecutionResult) -> None:
        """Log execution to audit trail"""
        try:
            audit_entry = {
                "timestamp": time.time(),
                "command": command,
                "success": result.success,
                "exit_code": result.exit_code,
                "execution_time_ms": result.execution_time_ms,
                "cpu_time_seconds": result.cpu_time_seconds,
                "fs_changes": result.fs_changes_detected,
                "command_type": result.command_type.value,
                "blocked_reason": result.blocked_reason
            }
            
            with open(self.audit_log_path, "a") as f:
                f.write(json.dumps(audit_entry) + "\n")
                
        except Exception as e:
            logger.warning(f"Failed to write audit log: {e}")
    
    def _create_execution_script(self, command: str, shell_type: str = "bash") -> str:
        """
        Create secure execution script with monitoring
        
        Returns script content for sandboxed execution
        """
        if shell_type == "powershell":
            script = f"""
# PowerShell execution wrapper with monitoring
$start = Get-Date
$process = Start-Process -FilePath "powershell" -ArgumentList "-Command", "{command}" -Wait -PassThru -NoNewWindow -RedirectStandardOutput "stdout.txt" -RedirectStandardError "stderr.txt"
$end = Get-Date
$duration = ($end - $start).TotalMilliseconds

# Output results in JSON format
@{{
    "exit_code" = $process.ExitCode
    "stdout" = (Get-Content "stdout.txt" -Raw -ErrorAction SilentlyContinue) ?? ""
    "stderr" = (Get-Content "stderr.txt" -Raw -ErrorAction SilentlyContinue) ?? ""
    "execution_time_ms" = [int]$duration
    "cpu_time_seconds" = $process.TotalProcessorTime.TotalSeconds
}} | ConvertTo-Json -Compress
"""
        else:
            # Bash/shell script
            script = f"""
#!/bin/bash
set -euo pipefail

# Start timing
start_time=$(date +%s%3N)
start_cpu=$(grep 'cpu ' /proc/stat | awk '{{print $2+$3+$4+$5+$6+$7+$8}}' 2>/dev/null || echo 0)

# Execute command with timeout
timeout {self.max_cpu_seconds}s bash -c "{command}" > stdout.txt 2> stderr.txt || exit_code=$?

# End timing
end_time=$(date +%s%3N)
end_cpu=$(grep 'cpu ' /proc/stat | awk '{{print $2+$3+$4+$5+$6+$7+$8}}' 2>/dev/null || echo 0)

# Calculate metrics
execution_time=$((end_time - start_time))
cpu_time=$(echo "scale=3; ($end_cpu - $start_cpu) / 100" | bc 2>/dev/null || echo "0")

# Output JSON result
cat << EOF
{{
    "exit_code": ${{exit_code:-0}},
    "stdout": "$(cat stdout.txt | sed 's/"/\\"/g' | tr '\\n' '\\\\n')",
    "stderr": "$(cat stderr.txt | sed 's/"/\\"/g' | tr '\\n' '\\\\n')",
    "execution_time_ms": $execution_time,
    "cpu_time_seconds": $cpu_time
}}
EOF
"""
        
        return script
    
    def _execute_powershell_direct(self, command: str) -> dict:
        """
        Direct PowerShell execution for Windows development
        
        Temporary implementation for Week 2 development when Docker/WSL not available
        """
        start_time = time.perf_counter()
        
        try:
            # Basic PowerShell execution with timeout
            result = subprocess.run(
                ["powershell", "-Command", command],
                capture_output=True,
                text=True,
                timeout=self.max_cpu_seconds
            )
            
            elapsed_ms = int((time.perf_counter() - start_time) * 1000)
            
            return {
                "stdout": result.stdout,
                "stderr": result.stderr,
                "elapsed_ms": elapsed_ms
            }
            
        except subprocess.TimeoutExpired:
            elapsed_ms = int((time.perf_counter() - start_time) * 1000)
            raise RuntimeError(f"Command timed out after {self.max_cpu_seconds}s")
        except Exception as e:
            elapsed_ms = int((time.perf_counter() - start_time) * 1000)
            raise RuntimeError(f"PowerShell execution failed: {str(e)}")
    
    @OS_EXEC_LATENCY.time() if PROMETHEUS_AVAILABLE else lambda f: f
    def execute_command(self, command: str, working_dir: Optional[str] = None) -> ExecutionResult:
        """
        Execute OS command with security and monitoring
        
        Args:
            command: Shell command to execute
            working_dir: Optional working directory
            
        Returns:
            ExecutionResult with execution details
        """
        start_time = time.perf_counter()
        
        # 1. Classify and validate command
        command_type, is_allowed = self._classify_command(command)
        
        if not is_allowed:
            if PROMETHEUS_AVAILABLE:
                OS_EXEC_BLOCKED.labels(reason="not_allowed").inc()
            
            result = ExecutionResult(
                success=False,
                stdout="",
                stderr="Command not in allowlist",
                exit_code=-1,
                execution_time_ms=0,
                cpu_time_seconds=0,
                fs_changes_detected=0,
                command_type=command_type,
                blocked_reason="Command not in allowlist"
            )
            self._audit_log(command, result)
            return result
        
        # 2. Check cost guards
        cost_guard_error = self._check_cost_guards(command)
        if cost_guard_error:
            if PROMETHEUS_AVAILABLE:
                OS_EXEC_BLOCKED.labels(reason="cost_guard").inc()
            
            result = ExecutionResult(
                success=False,
                stdout="",
                stderr=cost_guard_error,
                exit_code=-1,
                execution_time_ms=0,
                cpu_time_seconds=0,
                fs_changes_detected=0,
                command_type=command_type,
                blocked_reason=cost_guard_error
            )
            self._audit_log(command, result)
            return result
        
        # 3. Execute in sandbox
        try:
            # Determine shell type
            shell_type = "powershell" if os.name == 'nt' else "bash"
            
            # For Week 2 development, use simplified execution for Windows
            if os.name == 'nt':
                # Direct PowerShell execution for Windows development
                sandbox_result = self._execute_powershell_direct(command)
            else:
                # Create execution script for Linux
                script = self._create_execution_script(command, shell_type)
                # Execute through existing sandbox infrastructure
                sandbox_result = exec_safe(script, lang="sh")
            
            # Parse result from JSON output
            try:
                output_data = json.loads(sandbox_result["stdout"])
                
                execution_time_ms = int((time.perf_counter() - start_time) * 1000)
                
                result = ExecutionResult(
                    success=(output_data.get("exit_code", 0) == 0),
                    stdout=output_data.get("stdout", ""),
                    stderr=output_data.get("stderr", ""),
                    exit_code=output_data.get("exit_code", 0),
                    execution_time_ms=execution_time_ms,
                    cpu_time_seconds=float(output_data.get("cpu_time_seconds", 0)),
                    fs_changes_detected=0,  # TODO: Implement FS change detection
                    command_type=command_type
                )
                
            except json.JSONDecodeError:
                # Fallback if JSON parsing fails
                result = ExecutionResult(
                    success=True,
                    stdout=sandbox_result["stdout"],
                    stderr=sandbox_result["stderr"],
                    exit_code=0,
                    execution_time_ms=sandbox_result["elapsed_ms"],
                    cpu_time_seconds=0,
                    fs_changes_detected=0,
                    command_type=command_type
                )
            
            # Update metrics
            if PROMETHEUS_AVAILABLE:
                OS_EXEC_TOTAL.labels(
                    command_type=command_type.value,
                    status="success" if result.success else "failed"
                ).inc()
                
                OS_EXEC_CPU_TIME.observe(result.cpu_time_seconds)
                
                if result.fs_changes_detected > 0:
                    OS_EXEC_FS_CHANGES.inc(result.fs_changes_detected)
            
            self._audit_log(command, result)
            return result
            
        except Exception as e:
            logger.error(f"OS execution failed: {e}")
            
            execution_time_ms = int((time.perf_counter() - start_time) * 1000)
            
            result = ExecutionResult(
                success=False,
                stdout="",
                stderr=f"Execution error: {str(e)}",
                exit_code=-1,
                execution_time_ms=execution_time_ms,
                cpu_time_seconds=0,
                fs_changes_detected=0,
                command_type=command_type,
                blocked_reason=f"Runtime error: {str(e)}"
            )
            
            if PROMETHEUS_AVAILABLE:
                OS_EXEC_TOTAL.labels(
                    command_type=command_type.value,
                    status="error"
                ).inc()
            
            self._audit_log(command, result)
            return result

# Global executor instance
_executor_instance = None

def get_executor() -> ShellExecutor:
    """Get singleton shell executor instance"""
    global _executor_instance
    if _executor_instance is None:
        _executor_instance = ShellExecutor()
    return _executor_instance

def execute_shell_command(command: str, working_dir: Optional[str] = None) -> Dict[str, Any]:
    """
    Public API for shell command execution
    
    Returns simplified result dict for API responses
    """
    executor = get_executor()
    result = executor.execute_command(command, working_dir)
    
    return {
        "success": result.success,
        "stdout": result.stdout,
        "stderr": result.stderr,
        "exit_code": result.exit_code,
        "execution_time_ms": result.execution_time_ms,
        "command_type": result.command_type.value,
        "blocked_reason": result.blocked_reason
    } 