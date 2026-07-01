#!/usr/bin/env sh
set -e

# Wait for the database to accept connections before doing anything else.
if [ -n "$DB_HOST" ]; then
    echo "Waiting for database at $DB_HOST:${DB_PORT:-5432}..."
    until python -c "import socket,sys,os; s=socket.socket(); s.settimeout(2); \
sys.exit(0) if not s.connect_ex((os.environ['DB_HOST'], int(os.environ.get('DB_PORT', 5432)))) else sys.exit(1)" 2>/dev/null; do
        sleep 1
    done
    echo "Database is up."
fi

# Apply migrations on container start (safe & idempotent).
python manage.py migrate --noinput

exec "$@"
