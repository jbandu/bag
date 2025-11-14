#!/bin/bash
#
# Neo4j Cluster Backup Script
# Backs up Neo4j database to S3 with retention policy
#
# Usage: ./neo4j-backup.sh [full|incremental]
#

set -euo pipefail

# Configuration
BACKUP_TYPE="${1:-full}"
NEO4J_HOST="${NEO4J_HOST:-neo4j-core1}"
NEO4J_PORT="${NEO4J_PORT:-7687}"
NEO4J_USER="${NEO4J_USER:-neo4j}"
NEO4J_PASSWORD="${NEO4J_PASSWORD}"
DATABASE="${NEO4J_DATABASE:-baggage_prod}"
BACKUP_DIR="/backups/neo4j"
S3_BUCKET="${BACKUP_S3_BUCKET:-copa-baggage-ai-backups}"
S3_PREFIX="neo4j"
RETENTION_DAYS="${BACKUP_RETENTION_DAYS:-30}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# Logging
log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $*"
}

error() {
    log "ERROR: $*" >&2
    exit 1
}

# Create backup directory
mkdir -p "${BACKUP_DIR}"

log "Starting ${BACKUP_TYPE} backup of Neo4j database '${DATABASE}'"

# Full backup
if [ "${BACKUP_TYPE}" = "full" ]; then
    BACKUP_FILE="${BACKUP_DIR}/neo4j_full_${TIMESTAMP}.backup"

    log "Creating full backup to ${BACKUP_FILE}"

    # Use neo4j-admin backup
    neo4j-admin database backup \
        --database="${DATABASE}" \
        --to-path="${BACKUP_FILE}" \
        --verbose \
        || error "Full backup failed"

    log "Full backup completed: ${BACKUP_FILE}"

# Incremental backup
elif [ "${BACKUP_TYPE}" = "incremental" ]; then
    # Find latest full backup
    LATEST_FULL=$(find "${BACKUP_DIR}" -name "neo4j_full_*.backup" -type d | sort -r | head -n 1)

    if [ -z "${LATEST_FULL}" ]; then
        log "No full backup found, performing full backup instead"
        exec "$0" full
    fi

    BACKUP_FILE="${BACKUP_DIR}/neo4j_incremental_${TIMESTAMP}.backup"

    log "Creating incremental backup based on ${LATEST_FULL}"

    neo4j-admin database backup \
        --database="${DATABASE}" \
        --to-path="${BACKUP_FILE}" \
        --from-path="${LATEST_FULL}" \
        --verbose \
        || error "Incremental backup failed"

    log "Incremental backup completed: ${BACKUP_FILE}"
else
    error "Invalid backup type: ${BACKUP_TYPE}. Use 'full' or 'incremental'"
fi

# Compress backup
log "Compressing backup"
tar -czf "${BACKUP_FILE}.tar.gz" -C "$(dirname ${BACKUP_FILE})" "$(basename ${BACKUP_FILE})"
rm -rf "${BACKUP_FILE}"

BACKUP_ARCHIVE="${BACKUP_FILE}.tar.gz"
BACKUP_SIZE=$(du -h "${BACKUP_ARCHIVE}" | cut -f1)

log "Backup compressed: ${BACKUP_ARCHIVE} (${BACKUP_SIZE})"

# Upload to S3
log "Uploading backup to S3"

aws s3 cp "${BACKUP_ARCHIVE}" \
    "s3://${S3_BUCKET}/${S3_PREFIX}/$(basename ${BACKUP_ARCHIVE})" \
    --storage-class STANDARD_IA \
    --metadata "backup-type=${BACKUP_TYPE},database=${DATABASE},timestamp=${TIMESTAMP}" \
    || error "S3 upload failed"

log "Backup uploaded to S3: s3://${S3_BUCKET}/${S3_PREFIX}/$(basename ${BACKUP_ARCHIVE})"

# Verify upload
log "Verifying S3 upload"
aws s3 ls "s3://${S3_BUCKET}/${S3_PREFIX}/$(basename ${BACKUP_ARCHIVE})" > /dev/null \
    || error "S3 verification failed"

log "S3 upload verified"

# Clean up old local backups (keep last 7 days)
log "Cleaning up old local backups"
find "${BACKUP_DIR}" -name "*.tar.gz" -type f -mtime +7 -delete
log "Local cleanup completed"

# Clean up old S3 backups
log "Cleaning up old S3 backups (retention: ${RETENTION_DAYS} days)"

CUTOFF_DATE=$(date -d "${RETENTION_DAYS} days ago" +%Y%m%d)

aws s3 ls "s3://${S3_BUCKET}/${S3_PREFIX}/" | while read -r line; do
    BACKUP_FILE=$(echo "$line" | awk '{print $4}')
    if [[ ${BACKUP_FILE} =~ neo4j_(full|incremental)_([0-9]{8}) ]]; then
        BACKUP_DATE="${BASH_REMATCH[2]}"
        if [ "${BACKUP_DATE}" -lt "${CUTOFF_DATE}" ]; then
            log "Deleting old backup: ${BACKUP_FILE}"
            aws s3 rm "s3://${S3_BUCKET}/${S3_PREFIX}/${BACKUP_FILE}"
        fi
    fi
done

log "S3 cleanup completed"

# Send metrics to Prometheus Pushgateway
if [ -n "${PROMETHEUS_PUSHGATEWAY:-}" ]; then
    cat <<EOF | curl --data-binary @- "${PROMETHEUS_PUSHGATEWAY}/metrics/job/neo4j_backup"
# HELP backup_duration_seconds Time taken for backup
# TYPE backup_duration_seconds gauge
backup_duration_seconds{database="${DATABASE}",type="${BACKUP_TYPE}"} ${SECONDS}

# HELP backup_size_bytes Size of backup in bytes
# TYPE backup_size_bytes gauge
backup_size_bytes{database="${DATABASE}",type="${BACKUP_TYPE}"} $(stat -f%z "${BACKUP_ARCHIVE}")

# HELP backup_timestamp_seconds Timestamp of backup
# TYPE backup_timestamp_seconds gauge
backup_timestamp_seconds{database="${DATABASE}",type="${BACKUP_TYPE}"} $(date +%s)
EOF
fi

log "Backup completed successfully"
log "Backup file: ${BACKUP_ARCHIVE}"
log "Backup size: ${BACKUP_SIZE}"
log "S3 location: s3://${S3_BUCKET}/${S3_PREFIX}/$(basename ${BACKUP_ARCHIVE})"

# Send success notification
if [ -n "${SLACK_WEBHOOK_URL:-}" ]; then
    curl -X POST "${SLACK_WEBHOOK_URL}" \
        -H 'Content-Type: application/json' \
        -d "{\"text\":\"✅ Neo4j ${BACKUP_TYPE} backup completed successfully\n• Database: ${DATABASE}\n• Size: ${BACKUP_SIZE}\n• Location: s3://${S3_BUCKET}/${S3_PREFIX}/$(basename ${BACKUP_ARCHIVE})\"}"
fi

exit 0
