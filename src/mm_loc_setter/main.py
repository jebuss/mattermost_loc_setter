"""Mattermost location status setter - main entry point."""
from mm_loc_setter.network import setup_ipv4_enforcement
from mm_loc_setter.commands.cli import cli

# Setup IPv4 enforcement
setup_ipv4_enforcement()


def main():
    """Entry point for the CLI."""
    cli()


if __name__ == "__main__":
    main()