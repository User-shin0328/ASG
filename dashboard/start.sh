#!/bin/sh
set -eu

# Resolve only the fixed internal Gateway before enabling the default-deny
# output chain. The dashboard never needs a general outbound connection.
gateway_ip="$(python -c 'import socket; print(socket.gethostbyname("gateway"))')"
case "$gateway_ip" in
  *[!0-9.]*|'') echo "invalid Gateway IPv4 address" >&2; exit 1 ;;
esac

nft -f - <<EOF
table inet dashboard_egress {
  chain output {
    type filter hook output priority filter; policy drop;
    oifname "lo" accept
    ct state established,related accept
    ip daddr 127.0.0.11 udp dport 53 accept
    ip daddr 127.0.0.11 tcp dport 53 accept
    ip daddr $gateway_ip tcp dport 8000 accept
  }
}
EOF

# NET_ADMIN and SETPCAP are needed only to install the filter. Drop the full
# capability bounding set and run the application as its dedicated UID.
exec setpriv \
  --reuid=10003 \
  --regid=10003 \
  --clear-groups \
  --bounding-set=-all \
  --inh-caps=-all \
  --ambient-caps=-all \
  python /app/server.py
