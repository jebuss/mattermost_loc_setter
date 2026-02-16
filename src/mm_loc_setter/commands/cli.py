"""CLI command definitions."""
import logging
import sys
from datetime import datetime
import socket as sock_module

import click

from mm_loc_setter.config import (
    MATTERMOST_URL,
    ACCESS_TOKEN,
    USER_ID,
    WORKING_DAYS,
    WORKING_START_HOUR,
    WORKING_START_MINUTE,
    WORKING_END_HOUR,
    WORKING_END_MINUTE,
    get_working_hours_for_day,
)
from mm_loc_setter.logging_setup import logger
from mm_loc_setter.api import (
    fetch_user_id_from_api,
    set_mattermost_custom_status,
    set_mattermost_status,
    clear_mattermost_custom_status,
)
from mm_loc_setter.network import (
    check_network_route,
    check_mattermost_reachable,
)
from mm_loc_setter.status import handle_status_update


@click.group()
@click.option('--log-level', '-v', type=click.Choice(['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'], case_sensitive=False),
              default=None, help='Set logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)')
@click.pass_context
def cli(ctx, log_level):
    """Mattermost location status setter."""
    if log_level:
        logger.setLevel(getattr(logging, log_level.upper()))
    
    if not all([ACCESS_TOKEN, USER_ID]):
        logger.error("❌ Environment variables MM_ACCESS_TOKEN and MM_USER_ID must be set.")
        sys.exit(1)


@cli.command('custom')
@click.argument('message')
@click.argument('emoji', default='house')
@click.option('--duration', type=str, default=None, help='How long the custom status should last (e.g., "30m", "1h", "today")')
@click.option('--expires-at', type=str, default=None, help='When the custom status should expire (Unix timestamp, ISO 8601, or relative like "1h")')
def set_custom_status(message, emoji, duration, expires_at):
    """Update Mattermost custom status (emoji + text).
    
    Examples:
        mm-status custom "In a meeting" zoom
        mm-status custom "Working from home" house --duration "1h"
        mm-status custom "At lunch" utensils --expires-at "30m"
        mm-status custom "Away" palm_tree --duration "today"
        mm-status custom "Busy" hourglass --expires-at "2025-12-18T17:00:00"
    """
    success = set_mattermost_custom_status(message, emoji, duration=duration, expires_at=expires_at)
    if not success:
        sys.exit(1)


@cli.command('set')
@click.argument('status', type=click.Choice(['online', 'away', 'dnd', 'offline']))
@click.option('--dnd-end-time', type=str, default=None, help='DND end time (Unix timestamp, ISO 8601, or relative like "1h", "30m")')
def set_status(status, dnd_end_time):
    """Update Mattermost presence status (online, away, dnd, offline).
    
    Examples:
        mm-status set online
        mm-status set dnd --dnd-end-time 1703001600
        mm-status set dnd --dnd-end-time "2025-12-18T10:30:00"
        mm-status set dnd --dnd-end-time "1h"
        mm-status set dnd --dnd-end-time "30m"
    """
    success = set_mattermost_status(status, dnd_end_time=dnd_end_time)
    if not success:
        sys.exit(1)


@cli.command('clear')
def clear_status():
    """Clear Mattermost custom status."""
    clear_mattermost_custom_status()


@cli.command('userid')
def get_user_id():
    """Fetch and display the user_id from Mattermost API."""
    if not ACCESS_TOKEN:
        logger.error("❌ MM_ACCESS_TOKEN must be set.")
        sys.exit(1)
    
    fetched_id = fetch_user_id_from_api(retries=3, delay=2)
    if fetched_id:
        logger.info(f"✅ User ID fetched successfully: {fetched_id}")
        click.echo(fetched_id)
    else:
        logger.error("❌ Failed to fetch user ID from Mattermost API")
        sys.exit(1)


@cli.command('auto')
def auto_update():
    """Automatically update status based on location and meeting state."""
    now = datetime.now()
    
    if now.weekday() not in WORKING_DAYS:
        logger.debug(f"⏸️  Today ({now.strftime('%A')}) is not a working day - skipping.")
        sys.exit(0)
    
    # Get working hours for today (may be different each day)
    today_hours = get_working_hours_for_day(now.weekday())
    start_time = now.replace(
        hour=today_hours["start_hour"],
        minute=today_hours["start_minute"],
        second=0,
        microsecond=0
    )
    end_time = now.replace(
        hour=today_hours["end_hour"],
        minute=today_hours["end_minute"],
        second=0,
        microsecond=0
    )
    
    if now < start_time or now >= end_time:
        logger.debug(f"⏸️  Outside working hours ({start_time.strftime('%H:%M')}-{end_time.strftime('%H:%M')}) - skipping.")
        sys.exit(0)

    logger.info("=" * 60)
    logger.info("🚀 Starting automatic status update")

    if not check_network_route(MATTERMOST_URL):
        logger.warning("⚠️  Cannot establish TCP connection to Mattermost server. Skipping.")
        sys.exit(0)

    if not check_mattermost_reachable():
        logger.warning("⚠️  Mattermost server not reachable. Skipping.")
        sys.exit(0)

    logger.info("✅ Mattermost server is reachable")
    
    handle_status_update()


@cli.command('test')
def test_connection():
    """Test connection to Mattermost server."""
    
    logger.info("=" * 60)
    logger.info("🧪 Testing connection")
    hostname = MATTERMOST_URL.replace('https://', '')
    
    try:
        ipv4 = sock_module.gethostbyname(hostname)
        logger.info(f"✅ DNS IPv4: {hostname} -> {ipv4}")
    except sock_module.gaierror as e:
        logger.error(f"❌ DNS failed: {e}")
        return

    if check_network_route(hostname):
        logger.info("✅ TCP connection works")
    else:
        logger.error("❌ TCP connection failed")
        return

    if check_mattermost_reachable(retries=1):
        logger.info("✅ HTTPS connection works")
    else:
        logger.error("❌ HTTPS connection failed")
