#!/bin/bash
# start-db.sh - Start PostgreSQL container
set -e

echo "🚀 Starting Oral Narratives database..."
docker compose up -d db

echo "⏳ Waiting for PostgreSQL..."
until docker exec oral-narratives-db pg_isready -U narrator -d oral_narratives 2>/dev/null; do
    sleep 1
done

echo "✅ Database is ready!"
echo "   Connection: postgresql://narrator:narrator123@localhost:5432/oral_narratives"
echo ""
echo "📊 Checking seeded data..."
docker exec oral-narratives-db psql -U narrator -d oral_narratives -c "SELECT COUNT(*) as narratives FROM narratives;" 2>/dev/null || echo "   (Database tables will be created and seeded when API starts)"
