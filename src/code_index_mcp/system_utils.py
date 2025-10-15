#!/usr/bin/env python
"""
System detection utilities for identifying Linux distribution and package manager.
"""
import platform
import subprocess
import os
import sys
from typing import Dict, Optional, Tuple
from pathlib import Path


class SystemInfo:
    """System information and package manager detection."""

    def __init__(self):
        self.system = platform.system().lower()
        self.distribution = self._detect_distribution()
        self.package_manager = self._detect_package_manager()
        self.version = self._get_version()

    def _detect_distribution(self) -> str:
        """Detect Linux distribution."""
        if self.system != 'linux':
            return self.system

        # Try multiple methods to detect distribution
        methods = [
            self._detect_from_os_release,
            self._detect_from_lsb_release,
            self._detect_from_etc_issue,
            self._detect_from_platform_module
        ]

        for method in methods:
            distro = method()
            if distro:
                return distro.lower()

        return "unknown"

    def _detect_from_os_release(self) -> Optional[str]:
        """Detect distribution from /etc/os-release."""
        os_release = Path("/etc/os-release")
        if not os_release.exists():
            return None

        try:
            with open(os_release, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("ID="):
                        return line.split("=")[1].strip('"')
                    elif line.startswith("ID_LIKE="):
                        # For Ubuntu derivatives, etc.
                        return line.split("=")[1].strip('"').split()[0]
        except (IOError, OSError):
            pass

        return None

    def _detect_from_lsb_release(self) -> Optional[str]:
        """Detect distribution from lsb_release command."""
        try:
            result = subprocess.run(
                ["lsb_release", "-si"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                return result.stdout.strip().lower()
        except (subprocess.TimeoutExpired, subprocess.CalledProcessError, FileNotFoundError):
            pass

        return None

    def _detect_from_etc_issue(self) -> Optional[str]:
        """Detect distribution from /etc/issue."""
        etc_issue = Path("/etc/issue")
        if not etc_issue.exists():
            return None

        try:
            with open(etc_issue, 'r') as f:
                content = f.read().lower()
                if "ubuntu" in content:
                    return "ubuntu"
                elif "debian" in content:
                    return "debian"
                elif "centos" in content:
                    return "centos"
                elif "red hat" in content or "rhel" in content:
                    return "rhel"
                elif "fedora" in content:
                    return "fedora"
                elif "arch" in content:
                    return "arch"
                elif "opensuse" in content:
                    return "opensuse"
        except (IOError, OSError):
            pass

        return None

    def _detect_from_platform_module(self) -> Optional[str]:
        """Detect distribution using platform module."""
        try:
            distro_info = platform.freedesktop_os_release()
            return distro_info.get("ID", "unknown").lower()
        except (AttributeError, OSError):
            # Fallback for older Python versions
            distro = platform.linux_distribution()
            if distro and distro[0]:
                return distro[0].lower()

        return None

    def _detect_package_manager(self) -> str:
        """Detect the primary package manager."""
        if self.system != 'linux':
            return "unknown"

        # Map distributions to package managers
        distro_to_pm = {
            "ubuntu": "apt",
            "debian": "apt",
            "linuxmint": "apt",
            "pop": "apt",
            "elementary": "apt",
            "centos": "yum",
            "rhel": "yum",
            "red hat": "yum",
            "fedora": "dnf",
            "arch": "pacman",
            "manjaro": "pacman",
            "opensuse": "zypper",
            "suse": "zypper"
        }

        # First try distribution-specific mapping
        for distro_name, pm in distro_to_pm.items():
            if distro_name in self.distribution:
                return pm

        # Fallback: detect by checking if package manager binaries exist
        package_managers = [
            ("apt", "apt-get"),
            ("dnf", "dnf"),
            ("yum", "yum"),
            ("pacman", "pacman"),
            ("zypper", "zypper"),
            ("snap", "snap")
        ]

        for pm_name, pm_binary in package_managers:
            if self._command_exists(pm_binary):
                return pm_name

        return "unknown"

    def _command_exists(self, command: str) -> bool:
        """Check if a command exists on the system."""
        try:
            subprocess.run(
                ["which", command],
                capture_output=True,
                timeout=3
            )
            return True
        except (subprocess.TimeoutExpired, subprocess.CalledProcessError, FileNotFoundError):
            return False

    def _get_version(self) -> str:
        """Get system version information."""
        if self.system == 'linux':
            try:
                result = subprocess.run(
                    ["lsb_release", "-rs"],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if result.returncode == 0:
                    return result.stdout.strip()
            except (subprocess.TimeoutExpired, subprocess.CalledProcessError, FileNotFoundError):
                pass

        return platform.version().split()[0] if platform.version() else "unknown"

    def is_root(self) -> bool:
        """Check if running with root privileges."""
        return os.geteuid() == 0

    def supports_sudo(self) -> bool:
        """Check if sudo is available."""
        return self._command_exists("sudo")

    def get_architecture(self) -> str:
        """Get system architecture."""
        return platform.machine().lower()

    def get_summary(self) -> Dict[str, str]:
        """Get complete system summary."""
        return {
            "system": self.system,
            "distribution": self.distribution,
            "package_manager": self.package_manager,
            "version": self.version,
            "architecture": self.get_architecture(),
            "is_root": str(self.is_root()),
            "supports_sudo": str(self.supports_sudo())
        }


def detect_system() -> SystemInfo:
    """Convenience function to detect system information."""
    return SystemInfo()


def print_system_info():
    """Print system information for debugging."""
    info = detect_system()
    print("System Information:")
    print(f"  OS: {info.system}")
    print(f"  Distribution: {info.distribution}")
    print(f"  Package Manager: {info.package_manager}")
    print(f"  Version: {info.version}")
    print(f"  Architecture: {info.get_architecture()}")
    print(f"  Root privileges: {info.is_root()}")
    print(f"  Sudo available: {info.supports_sudo()}")


if __name__ == "__main__":
    print_system_info()