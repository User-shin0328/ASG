FROM postgres:17.11-alpine
COPY scripts/create_gateway_role.sh /docker-entrypoint-initdb.d/10-create-gateway-role.sh
RUN chmod 0555 /docker-entrypoint-initdb.d/10-create-gateway-role.sh
