# AutoClip AI - Docker Compose Commands

Dokumen ini berisi command-command Docker Compose yang sering digunakan untuk mengelola AutoClip AI.

## 📊 Monitoring & Status

```bash
# Cek status semua container
docker compose ps

# Cek status container tertentu
docker compose ps backend
docker compose ps celery-worker

# Cek resource usage (CPU, RAM)
docker stats

# Cek health check detail
docker compose ps --format "table {{.Name}}\t{{.Status}}\t{{.Health}}"
```

## 📜 Logs

```bash
# Cek log backend (real-time)
docker compose logs -f backend

# Cek log celery worker (real-time)
docker compose logs -f celery-worker

# Cek log frontend
docker compose logs -f frontend

# Cek log semua service
docker compose logs -f

# Cek log 50 baris terakhir
docker compose logs --tail 50 backend

# Cek log dengan timestamp
docker compose logs -t backend

# Cek log database
docker compose logs -f postgres

# Cek log redis
docker compose logs -f redis

# Cek log MinIO storage
docker compose logs -f minio
```

## 🔄 Restart Service

```bash
# Restart service tertentu
docker compose restart backend
docker compose restart celery-worker
docker compose restart frontend

# Restart semua service
docker compose restart

# Restart dan rebuild (jika ada perubahan kode)
docker compose up --build -d backend
docker compose up --build -d celery-worker
```

## 🚀 Start/Stop Service

```bash
# Jalankan semua service
docker compose up -d

# Jalankan service tertentu
docker compose up -d backend
docker compose up -d celery-worker

# Jalankan dengan rebuild
docker compose up --build -d

# Hentikan semua service
docker compose down

# Hentikan service tertentu
docker compose stop backend
docker compose stop celery-worker

# Hentikan dan hapus data (HATI-HATI - ini akan hapus database!)
docker compose down -v

# Hentikan dan hapus image juga
docker compose down --rmi all
```

## 🔧 Debug & Troubleshooting

```bash
# Masuk ke container backend (bash shell)
docker compose exec backend bash

# Masuk ke container backend dengan Python path yang benar
docker compose exec -w /app backend bash -c "PYTHONPATH=/app python"

# Jalankan seed database
docker compose exec -w /app backend bash -c "PYTHONPATH=/app python scripts/seed.py"

# Jalankan test
docker compose exec -w /app backend bash -c "PYTHONPATH=/app pytest tests/ -v"

# Cek Python version di container
docker compose exec backend python --version

# Cek disk usage container
docker system df -v

# Hapus container yang tidak digunakan
docker system prune -f

# Cek koneksi database dari backend
docker compose exec backend python -c "import asyncio; from app.database import init_db; asyncio.run(init_db()); print('DB OK')"
```

## 📦 Build & Deploy

```bash
# Build semua image
docker compose build

# Build service tertentu
docker compose build backend
docker compose build frontend

# Build tanpa cache
docker compose build --no-cache backend

# Pull image terbaru
docker compose pull
```

## 🗄️ Database

```bash
# Backup database
docker compose exec postgres pg_dump -U postgres autoclip > backup.sql

# Restore database
docker compose exec -T postgres psql -U postgres autoclip < backup.sql

# Masuk ke PostgreSQL shell
docker compose exec postgres psql -U postgres -d autoclip

# Cek tabel di database
\dt

# Cek data users
SELECT * FROM users;
```

## 💾 Storage (MinIO)

```bash
# Cek file di MinIO
docker compose exec backend python -c "from app.services.s3_service import s3_service; print(s3_service.client.list_buckets())"

# Akses MinIO Console
# Buka browser: http://localhost:9001
# Login: minioadmin / minioadmin
```

## 🔐 Celery Tasks

```bash
# Cek status Celery worker
docker compose exec celery-worker celery -A app.workers.celery_app inspect active

# Cek queue Celery
docker compose exec celery-worker celery -A app.workers.celery_app inspect scheduled

# Purge queue (HATI-HATI - hapus semua pending tasks)
docker compose exec celery-worker celery -A app.workers.celery_app purge

# Cek worker statistics
docker compose exec celery-worker celery -A app.workers.celery_app inspect stats
```

## ⚡ Quick Commands

```bash
# Full reset (stop, hapus volume, rebuild, start)
docker compose down -v && docker compose up --build -d

# Restart cepat backend + celery
docker compose restart backend celery-worker

# Cek semua log dalam satu command
docker compose logs -f --tail 20

# Update environment dan restart
docker compose up -d --force-recreate backend celery-worker
```

---

## 📝 Catatan Penting

- Gunakan `-f` untuk follow logs secara real-time
- Gunakan `--tail N` untuk melihat N baris terakhir
- Gunakan `-v` (hati-hati) untuk menghapus volumes/persistent data
- Semua command dijalankan dari folder `C:\Adn\Code\AutoClip-AI`

---

**Butuh bantuan lebih lanjut?** Cek log dengan:
```bash
docker compose logs -f backend
docker compose logs -f celery-worker
```
