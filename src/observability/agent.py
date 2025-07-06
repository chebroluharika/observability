from langchain.tools import Tool

from .backend.metrics_operations import (
    check_degraded_pgs,
    check_recent_osd_crashes,
    get_ceph_daemon_counts,
    get_cluster_health,
    get_diskoccupation,
    get_high_latency_osds,
)

# Define Tools
tools = [
    Tool(
        name="Get disk occupation",
        func=get_diskoccupation,
        description="Fetches the disk occupation per node.",
    ),
    Tool(
        name="Check degraded PGs",
        func=check_degraded_pgs,
        description="Checks degraded PGs.",
    ),
    Tool(
        name="Check recent OSD crashes",
        func=check_recent_osd_crashes,
        description="Checks recent OSD crashes.",
    ),
    Tool(
        name="Check cluster health",
        func=get_cluster_health,
        description="Check cluster health",
    ),
    Tool(
        name="Check high latency OSDs",
        func=get_high_latency_osds,
        description="Check high latency OSDs",
    ),
    Tool(
        name="Check count of daemons",
        func=get_ceph_daemon_counts,
        description="Check count of daemons",
    ),
]
