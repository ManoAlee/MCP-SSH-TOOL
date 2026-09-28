import os
import sys
import unittest
import asyncio

current_dir = os.path.dirname(os.path.abspath(__file__))
server_src = os.path.abspath(os.path.join(current_dir, "..", "server", "src"))
if server_src not in sys.path:
    sys.path.insert(0, server_src)

from ssh_connect.config_resolver import resolve_ssh_config, get_default_ssh_config_paths
from ssh_connect.security import load_private_key, is_dangerous_command, smart_truncate, ps_esc
from ssh_connect.pool import ConnectionPool

class TestEnterpriseFeatures(unittest.TestCase):

    def test_config_resolver(self):
        # Test resolving host
        res = resolve_ssh_config("192.168.1.100")
        self.assertEqual(res["host"], "192.168.1.100")
        self.assertIn("username", res)
        self.assertIn("port", res)


    def test_multi_key_loading(self):
        user_home = os.path.expanduser("~")
        ed25519_key = os.path.join(user_home, ".ssh", "id_ed25519")
        rsa_key = os.path.join(user_home, ".ssh", "id_rsa")

        if os.path.isfile(ed25519_key):
            key = load_private_key(ed25519_key)
            self.assertIsNotNone(key)
            self.assertEqual(key.get_name(), "ssh-ed25519")

        if os.path.isfile(rsa_key):
            key = load_private_key(rsa_key)
            self.assertIsNotNone(key)
            self.assertEqual(key.get_name(), "ssh-rsa")

    def test_dangerous_command_detection(self):
        danger, reason = is_dangerous_command("rm -rf /")
        self.assertTrue(danger)

        danger, reason = is_dangerous_command("rm -rf /var/log")
        self.assertTrue(danger)

        danger, reason = is_dangerous_command("mkfs.ext4 /dev/sdb1")
        self.assertTrue(danger)

        danger, reason = is_dangerous_command("shutdown -h now")
        self.assertTrue(danger)

        safe, _ = is_dangerous_command("ls -la /var/log")
        self.assertFalse(safe)

        safe, _ = is_dangerous_command("cat config.json")
        self.assertFalse(safe)

    def test_smart_truncate(self):
        short_text = "line 1\nline 2\nline 3"
        self.assertEqual(smart_truncate(short_text, max_lines=10), short_text)

        long_text = "\n".join([f"line {i}" for i in range(500)])
        truncated = smart_truncate(long_text, max_lines=50)
        self.assertTrue("TRUNCATED" in truncated)
        self.assertTrue("line 0" in truncated)
        self.assertTrue("line 499" in truncated)

    def test_connection_pool_lifecycle(self):
        pool = ConnectionPool()
        session = pool.connect_powershell("localhost", alias="local-test")
        self.assertEqual(pool.active_alias, "local-test")
        self.assertEqual(pool.get_session().host, "localhost")

        sessions = pool.list_sessions()
        self.assertEqual(len(sessions), 1)
        self.assertEqual(sessions[0]["alias"], "local-test")

        pool.disconnect("local-test")
        self.assertEqual(len(pool.list_sessions()), 0)

if __name__ == "__main__":
    unittest.main()
