#!/usr/bin/env python
"""
Standalone Elasticsearch installation script for Code Index MCP.
This script can be used to install Elasticsearch independently of the main server.
"""
import sys
import os
import argparse

# Add src directory to path
src_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'src')
sys.path.insert(0, src_path)

from code_index_mcp.system_utils import detect_system, print_system_info
from code_index_mcp.elasticsearch_installer import ElasticsearchInstaller


def main():
    """Main installation script."""
    parser = argparse.ArgumentParser(
        description="Install Elasticsearch for Code Index MCP",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                    # Auto-install with default settings
  %(prog)s --verbose          # Show detailed installation output
  %(prog)s --version 7.x      # Install Elasticsearch 7.x
  %(prog)s --check            # Check if Elasticsearch is installed
  %(prog)s --status           # Get service status
        """
    )

    parser.add_argument(
        "--version",
        default="8.x",
        help="Elasticsearch version to install (default: 8.x)"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose output"
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Check if Elasticsearch is installed and running"
    )
    parser.add_argument(
        "--status",
        action="store_true",
        help="Get Elasticsearch service status"
    )
    parser.add_argument(
        "--auto-install",
        action="store_true",
        help="Automatically install without prompts (sets environment variable)"
    )

    args = parser.parse_args()

    # Print system information
    print("Code Index MCP - Elasticsearch Installation")
    print("=" * 50)
    print_system_info()
    print()

    # Set auto-install environment if requested
    if args.auto_install:
        os.environ['CODE_INDEX_AUTO_INSTALL_ES'] = '1'

    # Create installer
    installer = ElasticsearchInstaller(version=args.version, verbose=args.verbose)

    if args.check:
        print("Checking Elasticsearch installation...")
        if installer._check_elasticsearch_installed():
            print("✅ Elasticsearch is installed and running")
            return 0
        else:
            print("❌ Elasticsearch is not installed or not running")
            return 1

    if args.status:
        print("Getting Elasticsearch service status...")
        status = installer.get_service_status()
        print(f"Service: {status['service']}")
        print(f"Status: {status['status']}")
        if status['output']:
            print(f"Details: {status['output']}")
        return 0

    # Install Elasticsearch
    print(f"Installing Elasticsearch {args.version}...")
    print("This may require root privileges and will attempt to install using your system's package manager.")
    print()

    try:
        success = installer.install_elasticsearch()

        if success:
            print("\n✅ Elasticsearch installation completed successfully!")

            # Get final status
            status = installer.get_service_status()
            print(f"Service status: {status['status']}")

            if status['status'] == 'running':
                print("✅ Elasticsearch is now running on http://localhost:9200")
                print("You can now use the Code Index MCP server.")
            else:
                print("⚠️ Elasticsearch may require manual configuration to start")
                print("Try: sudo systemctl start elasticsearch")

            return 0
        else:
            print("\n❌ Elasticsearch installation failed")
            print("Please check the logs above and try manual installation:")
            print()
            system_info = detect_system()
            if system_info.package_manager == 'apt':
                print("# For Debian/Ubuntu:")
                print("wget -qO - https://artifacts.elastic.co/GPG-KEY-elasticsearch | sudo gpg --dearmor -o /usr/share/keyrings/elasticsearch-keyring.gpg")
                print("echo 'deb [signed-by=/usr/share/keyrings/elasticsearch-keyring.gpg] https://artifacts.elastic.co/packages/8.x/apt stable main' | sudo tee /etc/apt/sources.list.d/elastic-8.x.list")
                print("sudo apt update")
                print("sudo apt install elasticsearch")
                print("sudo systemctl enable elasticsearch")
                print("sudo systemctl start elasticsearch")
            elif system_info.package_manager in ['yum', 'dnf']:
                print(f"# For RHEL/CentOS/Fedora:")
                print("sudo rpm --import https://artifacts.elastic.co/GPG-KEY-elasticsearch")
                print("sudo tee /etc/yum.repos.d/elasticsearch.repo <<EOF")
                print("[elasticsearch]")
                print("name=Elasticsearch repository for 8.x packages")
                print("baseurl=https://artifacts.elastic.co/packages/8.x/yum")
                print("gpgcheck=1")
                print("gpgkey=https://artifacts.elastic.co/GPG-KEY-elasticsearch")
                print("enabled=0")
                print("autorefresh=1")
                print("type=rpm-md")
                print("EOF")
                print(f"sudo {system_info.package_manager} install elasticsearch")
                print("sudo systemctl enable elasticsearch")
                print("sudo systemctl start elasticsearch")

            return 1

    except KeyboardInterrupt:
        print("\nInstallation cancelled by user")
        return 1
    except Exception as e:
        print(f"\n❌ Installation failed with error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())