# AutoClip AI v1.0

Sistem AI Auto Clip berbasis pipeline untuk memproses video mentah menjadi klip video pendek berkualitas tinggi.

## Arsitektur

- **Backend**: FastAPI (Python 3.11) + Celery + PostgreSQL + Redis
- **Frontend**: Next.js 14 + TailwindCSS
- **AI/ML**: faster-whisper, PySceneDetect, OpenRouter API
- **Storage**: MinIO (S3-compatible)
- **Infrastructure**: Docker Compose

## Quick Start

### 1. Setup Environment

```bash
cp .env.example .env
# Edit .env dan isi OPENROUTER_API_KEY
```

### 2. Jalankan dengan Docker Compose

**Pertama kali (Build & Run):**
```bash
docker compose up --build -d
```

**Sudah pernah build (Langsung start tanpa build ulang):**
```bash
docker compose up -d
```

**Seed database (buat user admin & editor):**
```bash
docker compose exec -w /app backend bash -c "PYTHONPATH=/app python scripts/seed.py"
```

### 3. Cek Status Container

```bash
docker compose ps
```

### 4. Akses Aplikasi

| Service | URL |
|:---|:---|
| **Frontend Dashboard** | http://localhost:3000 |
| **Backend API** | http://localhost:8000 |
| **API Docs (Swagger)** | http://localhost:8000/docs |
| **MinIO Console** | http://localhost:9001 |

### 5. Login Credential (Setelah Seed)

| Role | Email | Password |
|:---|:---|:---|
| Admin | `admin@autoclip.ai` | `admin123` |
| Editor | `editor@autoclip.ai` | `editor123` |

### 6. Stop Aplikasi

```bash
# Stop semua service (data tetap tersimpan)
docker compose down

# Stop dan hapus semua data (HATI-HATI)
docker compose down -v
```

## Pipeline (10 Tahap)

1. **Ingest** - Validasi & upload ke storage
2. **Audio Extract** - Ekstraksi WAV 16kHz mono
3. **Transcription** - Whisper ASR
4. **Scene Detection** - PySceneDetect
5. **Energy Scoring** - Audio amplitude + optical flow
6. **LLM Scoring** - OpenRouter (Nemotron)
7. **Clip Ranking** - Agregasi & deduplikasi
8. **Clip Export** - FFmpeg multi-format
9. **Subtitle Embed** - SRT generation
10. **Delivery** - Presigned URLs

## Fitur

- Upload video (MP4/MOV, max 4GB)
- Deteksi otomatis scene & transkripsi
- Skoring AI berbasis 5 dimensi
- Review & approve/reject klip
- Multi-format output (9:16, 16:9, 1:1)
- Autentikasi JWT + RBAC

## Dokumentasi API

Lihat OpenAPI docs di `/docs` setelah menjalankan backend.

## Lisensi

Internal Use Only - Nortis AI Academy
