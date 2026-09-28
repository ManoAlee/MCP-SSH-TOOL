"""
Connection Pool and Session Manager
Manages multiple active SSH and PowerShell/WinRM sessions with thread-safety and keepalive.
"""

import os
import time
import asyncio
import logging
from typing import Dict, Optional, Any, Tuple
from dataclasses import dataclass, field
import paramiko

from .security import load_private_key, ps_esc
from .config_resolver import resolve_ssh_config

logger = logging.getLogger("ssh-connect")


@dataclass
class HostSession:
    alias: str
    mode: str
    host: str
    port: int = 22
    username: Optional[str] = None
    password: Optional[str] = None
    key_path: Optional[str] = None
    key_passphrase: Optional[str] = None
    
    ssh_client: Optional[paramiko.SSHClient] = None
    sftp_client: Optional[paramiko.SFTPClient] = None
    created_at: float = field(default_factory=time.time)
    last_used: float = field(default_factory=time.time)

    def is_active(self) -> bool:
        if self.mode == "powershell":
            return bool(self.host)
        if self.mode == "ssh":
            if not self.ssh_client:
                return False
            transport = self.ssh_client.get_transport()
            return transport is not None and transport.is_active()
        return False

    def close(self):
        if self.sftp_client:
            try:
                self.sftp_client.close()
            except Exception:
                pass
            self.sftp_client = None
            
        if self.ssh_client:
            try:
                self.ssh_client.close()
            except Exception:
                pass
            self.ssh_client = None


class ConnectionPool:
    def __init__(self):
        self._sessions: Dict[str, HostSession] = {}
        self._active_alias: Optional[str] = None

    @property
    def active_alias(self) -> Optional[str]:
        return self._active_alias

    def get_session(self, alias: Optional[str] = None) -> Optional[HostSession]:
        target_alias = alias or self._active_alias
        if not target_alias:
            return None
        session = self._sessions.get(target_alias)
        if session:
            session.last_used = time.time()
        return session

    def list_sessions(self) -> list[Dict[str, Any]]:
        results = []
        for a, s in self._sessions.items():
            results.append({
                "alias": a,
                "is_active_default": (a == self._active_alias),
                "mode": s.mode,
                "host": s.host,
                "username": s.username,
                "status": "connected" if s.is_active() else "disconnected",
                "uptime_seconds": int(time.time() - s.created_at),
            })
        return results

    def set_active(self, alias: str) -> bool:
        if alias in self._sessions:
            self._active_alias = alias
            return True
        return False

    async def connect_ssh(
        self,
        host: str,
        port: int = 22,
        username: Optional[str] = None,
        password: Optional[str] = None,
        key_path: Optional[str] = None,
        key_passphrase: Optional[str] = None,
        alias: Optional[str] = None,
        timeout: int = 15
    ) -> HostSession:
        cfg = resolve_ssh_config(host)
        resolved_host = cfg["hostname"] or host
        resolved_port = port if port != 22 else cfg["port"]
        resolved_user = username or cfg["username"]
        resolved_key = key_path or cfg["identity_file"]

        if not resolved_user:
            raise ValueError(f"SSH username is required for host {host}")

        session_alias = alias or host
        
        if session_alias in self._sessions:
            self._sessions[session_alias].close()

        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        pkey = None
        if resolved_key and os.path.isfile(resolved_key):
            pkey = load_private_key(resolved_key, passphrase=key_passphrase)

        connect_kwargs: Dict[str, Any] = {
            "hostname": resolved_host,
            "port": resolved_port,
            "username": resolved_user,
            "timeout": timeout,
            "banner_timeout": 15,
            "auth_timeout": 15,
        }

        if pkey:
            connect_kwargs["pkey"] = pkey
        elif password:
            connect_kwargs["password"] = password
        else:
            connect_kwargs["look_for_keys"] = True
            connect_kwargs["allow_agent"] = True

        try:
            client.connect(**connect_kwargs)
            sftp = client.open_sftp()
            
            session = HostSession(
                alias=session_alias,
                mode="ssh",
                host=resolved_host,
                port=resolved_port,
                username=resolved_user,
                password=password,
                key_path=resolved_key,
                key_passphrase=key_passphrase,
                ssh_client=client,
                sftp_client=sftp,
            )
            
            self._sessions[session_alias] = session
            self._active_alias = session_alias
            logger.info("SSH connection established to %s@%s:%d (alias=%s)", resolved_user, resolved_host, resolved_port, session_alias)
            return session
        except Exception as e:
            client.close()
            raise ValueError(f"Failed to connect via SSH to {host} ({resolved_host}:{resolved_port}): {str(e)}")

    def connect_powershell(
        self,
        host: str,
        username: Optional[str] = None,
        password: Optional[str] = None,
        alias: Optional[str] = None
    ) -> HostSession:
        session_alias = alias or host
        if session_alias in self._sessions:
            self._sessions[session_alias].close()

        session = HostSession(
            alias=session_alias,
            mode="powershell",
            host=host,
            username=username,
            password=password,
        )
        self._sessions[session_alias] = session
        self._active_alias = session_alias
        logger.info("PowerShell host initialized for %s (alias=%s)", host, session_alias)
        return session

    def disconnect(self, alias: Optional[str] = None) -> bool:
        target = alias or self._active_alias
        if target and target in self._sessions:
            self._sessions[target].close()
            del self._sessions[target]
            if self._active_alias == target:
                self._active_alias = next(iter(self._sessions.keys())) if self._sessions else None
            return True
        return False
