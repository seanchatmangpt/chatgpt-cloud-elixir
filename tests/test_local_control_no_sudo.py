from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
INSTALL = SCRIPTS / "install-local-control-macos-user.sh"
UNINSTALL = SCRIPTS / "uninstall-local-control-macos-user.sh"
PLAIN_INSTALL = SCRIPTS / "install-local-control-macos.sh"
PLAIN_UNINSTALL = SCRIPTS / "uninstall-local-control-macos.sh"

FORBIDDEN_TOKENS = [
    "/Library/LaunchDaemons",
    "/Library/PrivilegedHelperTools",
    "/usr/local/",
    "/opt/homebrew/",
    "launchctl bootstrap system/",
    "launchctl enable system/",
    "chown root",
]


def executable_shell_lines(text):
    # Documentation may mention the word, but executable shell lines may not invoke it.
    return "\n".join(
        line for line in text.splitlines()
        if line.strip() and not line.lstrip().startswith("#") and not line.startswith("  echo ")
    )


class NoSudoInstallerContractTest(unittest.TestCase):
    def test_user_installer_contains_no_sudo_invocation(self):
        executable = executable_shell_lines(INSTALL.read_text())
        self.assertNotIn("sudo ", executable)
        self.assertNotIn("sudo\t", executable)

    def test_user_uninstaller_contains_no_sudo_invocation(self):
        executable = executable_shell_lines(UNINSTALL.read_text())
        self.assertNotIn("sudo ", executable)
        self.assertNotIn("sudo\t", executable)

    def test_install_paths_are_user_scoped(self):
        text = INSTALL.read_text()
        for token in FORBIDDEN_TOKENS:
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


class PlainInstallerContractTest(unittest.TestCase):
    # The non-user-suffixed installers enroll the same user-domain LaunchAgent and
    # are bound by the same no-sudo contract: refuse UID 0, no sudo invocation,
    # no root-owned/system paths, paths confined to the user home.
    def test_plain_installer_contains_no_sudo_invocation(self):
        executable = executable_shell_lines(PLAIN_INSTALL.read_text())
        self.assertNotIn("sudo ", executable)
        self.assertNotIn("sudo\t", executable)

    def test_plain_uninstaller_contains_no_sudo_invocation(self):
        executable = executable_shell_lines(PLAIN_UNINSTALL.read_text())
        self.assertNotIn("sudo ", executable)
        self.assertNotIn("sudo\t", executable)

    def test_plain_install_paths_are_user_scoped(self):
        text = PLAIN_INSTALL.read_text()
        for token in FORBIDDEN_TOKENS:
            with self.subTest(token=token):
                self.assertNotIn(token, text)
        self.assertIn("$HOME/Library/LaunchAgents", text)
        self.assertIn('launchctl bootstrap "gui/', text)

    def test_plain_root_execution_is_refused(self):
        for path in (PLAIN_INSTALL, PLAIN_UNINSTALL):
            with self.subTest(path=path.name):
                text = path.read_text()
                self.assertIn('[[ "$(id -u)" -eq 0 ]]', text)
                self.assertIn("REFUSED[ROOT_EXECUTION]", text)

    def test_plain_installer_override_paths_must_remain_below_home(self):
        text = PLAIN_INSTALL.read_text()
        self.assertIn("REFUSED[NON_USERSPACE_PATH]", text)
        self.assertIn("path.relative_to(home)", text)


if __name__ == "__main__":
    unittest.main()
