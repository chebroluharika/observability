import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from connection import get_db_conn


# Tool Functions
def get_diskoccupation():
    print("get_diskoccupation function called")
    query_disk_occupation = """
        SELECT 
            labels->>'instance' AS instance, 
            SUM(value) AS total_disk_occupation 
        FROM ceph_cephdiskoccupation_metrics 
        GROUP BY instance;
        """

    conn = get_db_conn()
    if not conn:
        return "❌ Database connection failed."
    cursor = conn.cursor()
    try:
        cursor.execute(query_disk_occupation)
        disk_occupation_results = cursor.fetchall()

        print("\n### Ceph Disk Occupation Per Node ###")

        occupation_results = []
        for row in disk_occupation_results:
            occupation_results.append(f"Node: {row[0]}, Disk Occupation: {row[1]}")

        print(f"{occupation_results = }")

        return "\n".join(occupation_results)
    except Exception as e:
        print("❌ Error getting disk occupation status:", e)
    finally:
        cursor.close()
        conn.close()


def check_degraded_pgs():
    # Query to check if any degraded PGs exist
    query = """
    SELECT 
        CASE 
            WHEN MAX(value) > 0 THEN 'True'
            ELSE 'False'
        END AS degraded_pgs
    FROM ceph_cephpgdegraded_metrics;
    """
    conn = get_db_conn()
    if not conn:
        return "❌ Database connection failed."
    cursor = conn.cursor()
    try:
        cursor.execute(query)
        result = cursor.fetchone()[0]

        print(f"Degraded PGs: {result}")
        cursor.close()
        conn.close()
        return result

    except Exception as e:
        print("❌ Error checking degraded PGs:", e)
    finally:
        cursor.close()
        conn.close()


def check_recent_osd_crashes():
    # Query to check if any failed OSDs exist
    query = """
        WITH osd_status AS (
        SELECT 
            labels->>'ceph_daemon' AS osd_id, 
            value, 
            timestamp,
            LAG(value) OVER (
                PARTITION BY labels->>'ceph_daemon' 
                ORDER BY timestamp ASC
            ) AS previous_value
        FROM ceph_cephosdup_metrics
        WHERE metric_name = 'ceph_osd_up'
    )
    SELECT osd_id, value AS current_status, previous_value, timestamp 
    FROM osd_status
    WHERE previous_value = 1.0 AND value = 0.0
    ORDER BY timestamp DESC;
    """

    conn = get_db_conn()
    if not conn:
        return "❌ Database connection failed."
    cursor = conn.cursor()

    try:
        cursor.execute(query)
        crashed_osds = cursor.fetchall()

        if crashed_osds:
            response = "\n🚨 **YES!! AN OSD CRASH DETECTED!** 🚨\n"
            for osd in crashed_osds:
                osd_id, current_status, previous_value, timestamp = osd
                response += f"🛑 **OSD {osd_id} went DOWN at {timestamp}**\n"
            return response  # Return a formatted response with OSD crash details
        else:
            return "✅ No OSD failures detected."

    except Exception as e:
        return f"❌ Error executing query: {e}"
    finally:
        cursor.close()
        conn.close()


def get_cluster_health():
    query = "SELECT MAX(value) FROM ceph_cephhealthstatus_metrics;"

    conn = get_db_conn()
    if not conn:
        return {"status": "error", "message": "❌ Database connection failed."}

    cursor = conn.cursor()
    try:
        cursor.execute(query)
        result = cursor.fetchone()

        if not result or result[0] is None:
            return {"status": "error", "message": "⚠️ No health data available."}

        health_status = int(result[0])

        health_messages = {
            0: "🟢 Cluster is healthy (HEALTH_OK)",
            1: "🟡 Cluster has warnings (HEALTH_WARN)",
            2: "🔴 Cluster has critical issues (HEALTH_ERR)",
        }

        return {
            "status": "success",
            "health": health_messages.get(health_status, "Unknown health status"),
        }

    except Exception as e:
        return {
            "status": "error",
            "message": f"❌ Error fetching cluster health: {str(e)}",
        }

    finally:
        cursor.close()
        conn.close()


def get_high_latency_osds():
    query = """
    SELECT 
        labels->>'ceph_daemon' AS osd_id, 
        MAX(value) AS max_latency 
    FROM ceph_cephosdapplylatencyms_metrics
    WHERE timestamp >= %s AND timestamp <= %s
    GROUP BY labels->>'ceph_daemon'
    ORDER BY max_latency DESC
    LIMIT 5;
    """

    conn = get_db_conn()
    if not conn:
        return {"status": "error", "message": "❌ Database connection failed."}

    cursor = conn.cursor()
    try:
        start_time = "2025-02-14 16:40:00"
        end_time = "2025-02-17 16:40:10"

        cursor.execute(query, (start_time, end_time))
        results = cursor.fetchall()

        if not results:
            return {"status": "error", "message": "⚠️ No high-latency OSDs found."}

        latency_thresholds = {
            "low": {
                "status": "🟢 Latency is within normal range",
                "description": "The OSD is performing well with acceptable latency.",
            },
            "medium": {
                "status": "🟡 Latency is higher than usual",
                "description": "The OSD has some latency, but it is not critical.",
            },
            "high": {
                "status": "🔴 High latency detected",
                "description": "The OSD is experiencing significant latency, which may impact cluster performance.",
            },
        }

        high_latency_osds = []

        for row in results:
            osd_id, max_latency = row

            # Determine latency category based on thresholds
            if max_latency < 50:
                latency_category = "low"
            elif max_latency < 200:
                latency_category = "medium"
            else:
                latency_category = "high"

            latency_info = latency_thresholds[latency_category]

            high_latency_osds.append(
                {
                    "osd_id": osd_id,
                    "max_latency": max_latency,
                    "status": latency_info["status"],
                    "description": latency_info["description"],
                }
            )

        return {"high_latency_osds": high_latency_osds}

    except Exception as e:
        return {
            "status": "error",
            "message": f"❌ Error fetching high-latency OSDs: {str(e)}",
        }

    finally:
        cursor.close()
        conn.close()


def get_ceph_daemon_counts():
    query = """
    SELECT 'MON' AS daemon_type, COUNT(DISTINCT labels->>'ceph_daemon') AS count
    FROM ceph_cephmonmetadata_metrics
    WHERE value = 1.0

    UNION ALL

    SELECT 'MGR' AS daemon_type, COUNT(DISTINCT labels->>'hostname') AS count
    FROM ceph_cephmgrmetadata_metrics
    WHERE value = 1.0
    UNION ALL

    SELECT 'OSD' AS daemon_type, COUNT(DISTINCT labels->>'hostname') AS count
    FROM ceph_cephosdmetadata_metrics
    WHERE value = 1.0;
    """

    conn = get_db_conn()
    if not conn:
        return {"message": "❌ Database connection failed."}

    cursor = conn.cursor()
    try:
        cursor.execute(query)
        results = cursor.fetchall()

        message = ""
        for daemon_type, count in results:
            message += f"\n **{daemon_type} Count**: {count}\n"

        return {"status": "success", "message": message}

    except Exception as e:
        return {
            "status": "error",
            "message": f"❌ Error fetching Ceph daemon counts: {str(e)}",
        }

    finally:
        cursor.close()
        conn.close()
