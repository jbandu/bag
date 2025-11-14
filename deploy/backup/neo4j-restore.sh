#!/bin/bash
#
# Neo4j Cluster Restore Script
# Restores Neo4j database from S3 backup
#
# Usage: ./neo4j-restore.sh <backup-file> [--force]
#

set -euo pipefail

# Configuration
BACKUP_FILE="${1:-}"
FORCE="${2:-}"
NEO4J_HOST="${NEO4J_HOST:-neo4j-core1}"
DATABASE="${NEO4J_DATABASE:-baggage_prod}"
RESTORE_DIR="/restore/neo4j"
S3_BUCKET="${BACKUP_S3_BUCKET:-copa-baggage-ai-backups}"
S3_PREFIX="neo4j"

# Logging
log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $*"
}

error() {
    log "ERROR: $*" >&2
    exit 1
}

# Validate arguments
if [ -z "${BACKUP_FILE}" ]; then
    error "Usage: $0 <backup-file> [--force]"
fi

# Safety check
if [ "${FORCE}" != "--force" ]; then
    read -p "WARNING: This will replace the current database '${DATABASE}'. Type 'yes' to continue: " confirmation
    if [ "${confirmation}" != "yes" ]; then
        log "Restore cancelled"
        exit 0
    fi
fi

# Create restore directory
mkdir -p "${RESTORE_DIR}"

log "Starting restore of Neo4j database '${DATABASE}' from backup: ${BACKUP_FILE}"

# Download from S3
if [[ ${BACKUP_FILE} == s3://* ]]; then
    log "Downloading backup from S3"
    aws s3 cp "${BACKUP_FILE}" "${RESTORE_DIR}/" || error "S3 download failed"
    BACKUP_FILE="${RESTORE_DIR}/$(basename ${BACKUP_FILE})"
elif [[ ${BACKUP_FILE} == neo4j_* ]]; then
    # Assume it's a filename in S3
    log "Downloading backup from S3: ${BACKUP_FILE}"
    aws s3 cp "s3://${S3_BUCKET}/${S3_PREFIX}/${BACKUP_FILE}" "${RESTORE_DIR}/" \
        || error "S3 download failed"
    BACKUP_FILE="${RESTORE_DIR}/${BACKUP_FILE}"
fi

log "Backup downloaded: ${BACKUP_FILE}"

# Extract backup
log "Extracting backup"
tar -xzf "${BACKUP_FILE}" -C "${RESTORE_DIR}"
EXTRACTED_DIR=$(tar -tzf "${BACKUP_FILE}" | head -1 | cut -f1 -d"/")
BACKUP_DIR="${RESTORE_DIR}/${EXTRACTED_DIR}"

log "Backup extracted to: ${BACKUP_DIR}"

# Stop Neo4j (if running)
log "Stopping Neo4j database '${DATABASE}'"
cypher-shell -u neo4j -p "${NEO4J_PASSWORD}" \
    "STOP DATABASE ${DATABASE};" \
    || log "Database may already be stopped"

sleep 5

# Restore database
log "Restoring database from backup"

neo4j-admin database restore \
    --from-path="${BACKUP_DIR}" \
    --database="${DATABASE}" \
    --force \
    --verbose \
    || error "Restore failed"

log "Database restored successfully"

# Start Neo4j
log "Starting Neo4j database '${DATABASE}'"
cypher-shell -u neo4j -p "${NEO4J_PASSWORD}" \
    "START DATABASE ${DATABASE};" \
    || error "Failed to start database"

sleep 10

# Verify restore
log "Verifying restore"

NODE_COUNT=$(cypher-shell -u neo4j -p "${NEO4J_PASSWORD}" \
    "MATCH (n) RETURN count(n) AS count;" \
    --format plain | tail -n 1)

log "Node count after restore: ${NODE_COUNT}"

# Run integrity check
log "Running database integrity check"
neo4j-admin database check \
    --database="${DATABASE}" \
    --verbose \
    || log "WARNING: Integrity check found issues"

# Clean up
log "Cleaning up restore directory"
rm -rf "${BACKUP_DIR}"

log "Restore completed successfully"
log "Database: ${DATABASE}"
log "Node count: ${NODE_COUNT}"

# Send notification
if [ -n "${SLACK_WEBHOOK_URL:-}" ]; then
    curl -X POST "${SLACK_WEBHOOK_URL}" \
        -H 'Content-Type: application/json' \
        -d "{\"text\":\"✅ Neo4j restore completed successfully\n• Database: ${DATABASE}\n• Backup: ${BACKUP_FILE}\n• Node count: ${NODE_COUNT}\"}"
fi

exit 0
