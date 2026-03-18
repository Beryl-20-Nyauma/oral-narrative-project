#!/bin/bash
# reset-db.sh - Reset PostgreSQL container with fresh seed data
set -e

echo "⚠️  WARNING: This will delete all data!"
read -p "Continue? (y/N) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Cancelled."
    exit 1
fi

echo "🗑️  Removing volumes..."
docker compose down -v

echo "🔄 Starting fresh..."
docker compose up -d db

echo "⏳ Waiting for PostgreSQL..."
until docker exec oral-narratives-db pg_isready -U narrator -d oral_narratives 2>/dev/null; do
    sleep 1
done

echo "✅ Database reset complete!"
echo ""
echo "📝 Tables will be created and seeded when the API starts."
echo "   Run 'make up' or 'docker compose up' to start everything."
