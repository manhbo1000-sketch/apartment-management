#!/bin/sh
set -eu

# The application and exporter use a restricted role. The bootstrap account
# remains inside the data network and is not used by either service.
psql --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" \
  --set=ON_ERROR_STOP=1 \
  --set=app_password="$APARTMENT_DB_PASSWORD" <<'SQL'
CREATE ROLE apartment_app
  LOGIN PASSWORD :'app_password'
  NOSUPERUSER NOCREATEDB NOCREATEROLE;
GRANT CONNECT ON DATABASE apartment TO apartment_app;
REVOKE CREATE ON SCHEMA public FROM PUBLIC;
GRANT USAGE, CREATE ON SCHEMA public TO apartment_app;
GRANT pg_monitor TO apartment_app;
SQL
