"""Meeting detection for various video conferencing tools."""
import psutil
from typing import List
from mm_loc_setter.logging_setup import logger


def are_ports_connected_any(connections, ports: List[int] = [8801]) -> bool:
    """Check if any connection uses one of the specified ports.
    
    Args:
        connections: List of network connections
        ports: List of ports to check
        
    Returns:
        True if any connection uses one of the ports
    """
    return any(
        getattr(getattr(conn, 'raddr', None), 'port', None) in ports
        for conn in connections
    )


def is_in_meeting(process_name: str, ports: List[int]) -> bool:
    """Generic function to check if a process is in a meeting based on network connections.
    
    Args:
        process_name: Name of the process to check
        ports: List of ports to monitor
        
    Returns:
        True if process is connected to monitored ports
    """
    try:
        for proc in psutil.process_iter(['name']):
            proc_name = proc.info.get('name', '').lower()
            if process_name in proc_name:
                try:
                    conns = proc.net_connections(kind='inet')
                    if are_ports_connected_any(conns, ports=ports):
                        return True
                except (psutil.AccessDenied, psutil.NoSuchProcess):
                    continue
    except Exception as e:
        logger.debug(f"Error checking {process_name} meeting status: {e}")
    return False


def zoom_in_meeting() -> bool:
    """Check if Zoom is actively connected (likely in a meeting).
    
    Returns:
        True if Zoom is in an active meeting
    """
    return is_in_meeting('zoom', ports=[8801, 8802, 8803])


def teams_in_meeting() -> bool:
    """Check if MS Teams is actively connected (likely in a meeting).
    
    Returns:
        True if Teams is in an active meeting
    """
    return is_in_meeting('teams', ports=[3478, 3479, 3480, 3481])


def webex_in_meeting() -> bool:
    """Check if Webex is actively connected (likely in a meeting).
    
    Returns:
        True if Webex is in an active meeting
    """
    return is_in_meeting('webex', ports=[5004, 5005, 9000, 9001])
