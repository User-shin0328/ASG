#!/bin/sh
set -eu

gateway_password="$(tr -d '\r\n' < /run/secrets/gateway_db_password)"
if [ "${#gateway_password}" -lt 32 ]; then
  echo "Gateway database secret is missing or too short" >&2
  exit 1
fi

psql --set ON_ERROR_STOP=1 --set gateway_password="$gateway_password" \
  --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<'SQL'
CREATE ROLE gateway_app LOGIN PASSWORD :'gateway_password';
GRANT CONNECT ON DATABASE gateway TO gateway_app;
SQL

unset gateway_password
