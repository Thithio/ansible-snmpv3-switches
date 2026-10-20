#!/usr/bin/env bash
# Chamado pelo cron (ver examples/cron.d-snmpv3-switches).
# Uso manual: rodar_snmpv3.sh <homolog|production> [HOST_OU_IP_PARA_LIMITAR]
set -uo pipefail

AMBIENTE="${1:-production}"
LIMIT="${2:-}"
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
INVENTORY="$DIR/inventories/$AMBIENTE/inventory_switches.ini"
LOG_DIR="$DIR/playbooks/logs"
LOG_FILE="$LOG_DIR/snmpv3-$(date +%Y%m%d-%H%M%S).log"
VAULT_PASS_FILE="${VAULT_PASS_FILE:-$DIR/.vault_pass}"
mkdir -p "$LOG_DIR"
cd "$DIR"   # o ansible.cfg (roles_path) só é lido a partir do diretório atual

if [[ ! -r "$VAULT_PASS_FILE" ]]; then
  echo "ERRO: arquivo de senha do vault não encontrado: $VAULT_PASS_FILE" | tee -a "$LOG_FILE"
  exit 2
fi

EXTRA_ARGS=()
if [[ -n "$LIMIT" ]]; then
  # localhost precisa entrar no limite, senão o play do resumo/e-mail não roda.
  EXTRA_ARGS+=(--limit "$LIMIT,localhost")
fi

# Evita duas execuções ao mesmo tempo (ex.: cron + execução manual).
exec 9>/var/lock/snmpv3-switches.lock
if ! flock -n 9; then
  echo "Outra execução em andamento, saindo." | tee -a "$LOG_FILE"
  exit 0
fi

# O resumo no fim (e no e-mail) basta; verbosidade alta enche o log com cada IP.
export ANSIBLE_VERBOSITY="${ANSIBLE_VERBOSITY:-0}"

echo "== SNMPv3/trap ($AMBIENTE${LIMIT:+, limitado a $LIMIT}) $(date '+%F %T') ==" | tee -a "$LOG_FILE"
ansible-playbook "$DIR/playbooks/snmpv3-switches.yml" \
  -i "$INVENTORY" --forks 20 \
  --vault-password-file "$VAULT_PASS_FILE" \
  -e "snmpv3_ambiente=$AMBIENTE snmpv3_log_file=$LOG_FILE" \
  "${EXTRA_ARGS[@]}" \
  2>&1 | tee -a "$LOG_FILE"
RC=${PIPESTATUS[0]}

# Guarda 30 dias de log.
find "$LOG_DIR" -name 'snmpv3-*.log' -mtime +30 -delete

echo "Log completo em: $LOG_FILE (rc=$RC)"
exit "$RC"
