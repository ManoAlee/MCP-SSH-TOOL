"""
SSH Config Resolver Module
Loads and resolves ~/.ssh/config parameters (HostName, User, Port, IdentityFile, ProxyJump, etc.)
"""

import os
from typing import Any, Dict, Optional
import paramiko


def get_default_ssh_config_paths() -> list[str]:
    paths = []
    if os.environ.get("SSH_CONFIG_PATH"):
        paths.append(os.environ["SSH_CONFIG_PATH"])
    user_home = os.path.expanduser("~")
    paths.append(os.path.join(user_home, ".ssh", "config"))
    if os.name == "nt" and os.environ.get("USERPROFILE"):
        paths.append(os.path.join(os.environ["USERPROFILE"], ".ssh", "config"))
    return [p for p in paths if os.path.isfile(p)]


def resolve_ssh_config(
    host: str,
    config_path: Optional[str] = None
) -> Dict[str, Any]:
    result: Dict[str, Any] = {
        "host": host,
        "hostname": host,
        "port": 22,
        "username": None,
        "identity_file": None,
        "proxy_jump": None,
        "raw_config": {},
    }
    
    candidates = [config_path] if config_path and os.path.isfile(config_path) else get_default_ssh_config_paths()
    if not candidates:
        return result
        
    config_file = candidates[0]
    ssh_config = paramiko.SSHConfig()
    
    try:
        with open(config_file, "r", encoding="utf-8", errors="replace") as f:
            ssh_config.parse(f)
            
        host_config = ssh_config.lookup(host)
        if host_config:
            result["raw_config"] = host_config
            if "hostname" in host_config:
                result["hostname"] = host_config["hostname"]
            if "user" in host_config:
                result["username"] = host_config["user"]
            if "port" in host_config:
                try:
                    result["port"] = int(host_config["port"])
                except ValueError:
                    pass
            if "identityfile" in host_config:
                identities = host_config["identityfile"]
                if isinstance(identities, list) and len(identities) > 0:
                    id_file = os.path.expanduser(identities[0])
                    if os.path.isfile(id_file):
                        result["identity_file"] = id_file
                elif isinstance(identities, str):
                    id_file = os.path.expanduser(identities)
                    if os.path.isfile(id_file):
                        result["identity_file"] = id_file
            if "proxyjump" in host_config:
                result["proxy_jump"] = host_config["proxyjump"]
    except Exception:
        pass
        
    return result
