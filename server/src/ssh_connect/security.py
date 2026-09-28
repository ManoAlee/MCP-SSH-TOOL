"""
Security and Cryptography Module
Multi-key loader (Ed25519, RSA, ECDSA, DSS, Agent), output sanitization, 
and dangerous command detection for LLM agents.
"""

import os
import re
import base64
from typing import Optional, Tuple, Any
import paramiko


def load_private_key(
    key_path: str,
    passphrase: Optional[str] = None
) -> Optional[paramiko.PKey]:
    if not os.path.isfile(key_path):
        raise FileNotFoundError(f"Private key file not found at: {key_path}")
        
    password = passphrase if passphrase else None
    
    key_classes = [
        paramiko.Ed25519Key,
        paramiko.RSAKey,
        paramiko.ECDSAKey,
        paramiko.DSSKey,
    ]
    
    last_error = None
    for k_cls in key_classes:
        try:
            return k_cls.from_private_key_file(key_path, password=password)
        except Exception as e:
            last_error = e
            continue
            
    raise ValueError(f"Failed to load private key '{key_path}': {str(last_error)}")


def is_dangerous_command(command: str) -> Tuple[bool, str]:
    cmd = command.strip().lower()
    dangerous_patterns = [
        (r"rm\s+(-[a-zA-Z]*r[a-zA-Z]*f*|-f[a-zA-Z]*r[a-zA-Z]*)\s+[/~]", "Recursive root or home directory deletion (rm -rf /)"),
        (r"mkfs(\.[a-zA-Z0-9]+)?\s+", "Filesystem formatting (mkfs)"),
        (r"dd\s+if=.*of=(/dev/sd|/dev/nvme|/dev/hd|/dev/vd)", "Direct disk overwrite (dd)"),
        (r":\(\)\s*\{\s*:\s*\|\s*:\s*&\s*\}\s*;\s*:", "Fork bomb detected"),
        (r"\b(shutdown|reboot|poweroff|init\s+0)\b", "System shutdown or reboot"),
        (r"format\s+[a-zA-Z]:", "Windows disk formatting"),
        (r"del\s+/[fF]\s+/[sS]\s+[cC]:", "Windows recursive root deletion"),
    ]
    
    for pattern, reason in dangerous_patterns:
        if re.search(pattern, cmd, re.IGNORECASE):
            return True, reason
    return False, ""

def smart_truncate(
    text: str,
    max_lines: int = 200,
    max_chars: int = 30000
) -> str:
    if not text:
        return ""
        
    lines = text.splitlines()
    total_lines = len(lines)
    
    if total_lines <= max_lines and len(text) <= max_chars:
        return text
        
    head_lines = max_lines // 2
    tail_lines = max_lines // 2
    
    preserved_head = lines[:head_lines]
    preserved_tail = lines[-tail_lines:] if tail_lines > 0 else []
    omitted = total_lines - (head_lines + tail_lines)
    
    summary = f"\n... [TRUNCATED {omitted} LINES FOR LLM CONTEXT PROTECTION] ...\n"
    result = "\n".join(preserved_head) + summary + "\n".join(preserved_tail)
    
    if len(result) > max_chars:
        result = result[:max_chars] + "\n... [TRUNCATED MAXIMUM CHARS] ..."
        
    return result


def ps_esc(s: str) -> str:
    if s is None:
        return ""
    return str(s).replace("'", "''")
