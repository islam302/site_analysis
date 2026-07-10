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

# Only the web service should migrate / collect static (set via env), so the
# worker and beat containers don't race the migrations on startup.
if [ "${DJANGO_MIGRATE:-0}" = "1" ]; then
    echo "Applying migrations..."
    python manage.py migrate --noinput
fi

if [ "${DJANGO_COLLECTSTATIC:-0}" = "1" ]; then
    echo "Collecting static files..."
    python manage.py collectstatic --noinput
fi

exec "$@"
