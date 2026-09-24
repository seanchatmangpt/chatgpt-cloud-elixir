from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
INSTALL = ROOT / "scripts" / "install-local-control-macos-user.sh"
UNINSTALL = ROOT / "scripts" / "uninstall-local-control-macos-user.sh"


class NoSudoInstallerContractTest(unittest.TestCase):
    def test_user_installer_contains_no_sudo_invocation(self):
        text = INSTALL.read_text()
        # Documentation may mention the word, but executable shell lines may not invoke it.
        executable = "\n".join(
            line for line in text.splitlines()
            if line.strip() and not line.lstrip().startswith("#") and not line.startswith("  echo ")
        )
        self.assertNotIn("sudo ", executable)
        self.assertNotIn("sudo\t", executable)

    def test_user_uninstaller_contains_no_sudo_invocation(self):
        text = UNINSTALL.read_text()
        executable = "\n".join(
            line for line in text.splitlines()
            if line.strip() and not line.lstrip().startswith("#") and not line.startswith("  echo ")
        )
        self.assertNotIn("sudo ", executable)
        self.assertNotIn("sudo\t", executable)

    def test_install_paths_are_user_scoped(self):
        text = INSTALL.read_text()
        forbidden = [
            "/Library/LaunchDaemons",
            "/Library/PrivilegedHelperTools",
            "/usr/local/",
            "/opt/homebrew/",
            "launchctl bootstrap system/",
            "launchctl enable system/",
            "chown root",
        ]
        for token in forbidden:
            with self.subTest(token=token):
                self.assertNotIn(token, text)
        self.assertIn("$HOME/Library/LaunchAgents", text)
        self.assertIn('launchctl bootstrap "gui/$uid"', text)

    def test_root_execution_is_refused(self):
        for path in (INSTALL, UNINSTALL):
            with self.subTest(path=path.name):
                text = path.read_text()
                self.assertIn('[[ "$(id -u)" -eq 0 ]]', text)
                self.assertIn("REFUSED[ROOT_EXECUTION]", text)

    def test_override_paths_must_remain_below_home(self):
        text = INSTALL.read_text()
        self.assertIn("REFUSED[NON_USERSPACE_PATH]", text)
        self.assertIn("path.relative_to(home)", text)


if __name__ == "__main__":
    unittest.main()
