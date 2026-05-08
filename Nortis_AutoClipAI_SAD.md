

**Nortis AI Academy**

*Creative Intelligence · Digital Content Partner*

**SYSTEM ANALYSIS DOCUMENT**

**AutoClip AI — Analisis Sistem & Arsitektur Teknis**

| Versi Dokumen | v1.0 — Initial Release |
| :---- | :---- |
| **Dibuat Oleh** | Tim Teknis Nortis AI Academy |
| **Tanggal** | Mei 2025 |
| **Nomor Dokumen** | NAA-SAD-2025-001 |

# **1\. Tujuan Dokumen**

Dokumen ini menyajikan analisis teknis menyeluruh atas sistem AutoClip AI, mencakup arsitektur sistem, komponen-komponen inti, alur data, spesifikasi infrastruktur, serta pertimbangan keamanan dan skalabilitas. Dokumen ini menjadi acuan bagi tim teknis, AI engineer, dan stakeholder dalam memahami bagaimana sistem bekerja dan bagaimana keputusan arsitektur diambil.

# **2\. Gambaran Umum Sistem**

## **2.1  Deskripsi Sistem**

AutoClip AI adalah sistem pipeline berbasis kecerdasan buatan yang menerima input berupa file video mentah (raw footage), memprosesnya melalui serangkaian modul AI, dan menghasilkan klip video pendek berkualitas tinggi yang siap dipublikasikan. Sistem dirancang sebagai platform asinkronus dengan antrian tugas, memungkinkan pemrosesan beberapa video secara paralel.

## **2.2  Konteks Sistem**

AutoClip AI beroperasi sebagai sistem back-end yang diakses melalui antarmuka web internal. Pada fase v1.0, sistem hanya dapat diakses oleh tim editor internal Nortis AI Academy. Sistem berinteraksi dengan layanan cloud eksternal untuk komputasi AI (GPU cloud), penyimpanan objek (S3), dan model bahasa (Claude API).

## **2.3  Asumsi dan Batasan**

* Input video harus dalam format MP4 atau MOV dengan encoding H.264/H.265

* Ukuran file maksimum 4GB per upload pada versi v1.0

* Bahasa audio yang didukung: Bahasa Indonesia dan English

* Sistem membutuhkan koneksi internet untuk akses GPU cloud dan API eksternal

* Kapasitas concurrent jobs pada v1.0: maksimum 3 video simultan

# **3\. Arsitektur Sistem**

## **3.1  Pola Arsitektur**

AutoClip AI menggunakan pola arsitektur Event-Driven Microservices dengan komponen-komponen yang terhubung melalui message queue. Setiap modul AI berjalan sebagai worker independen yang dapat di-scale secara horizontal. Pendekatan ini dipilih untuk memisahkan beban komputasi, memudahkan debugging per modul, serta memungkinkan penggantian komponen tanpa mempengaruhi sistem keseluruhan.

## **3.2  Layer Arsitektur**

| Layer | Komponen | Teknologi |
| ----- | :---: | :---: |
| Presentation | Web Dashboard Internal | Next.js 14, TailwindCSS, Shadcn/UI |
| API Gateway | REST API, Autentikasi, Rate Limiting | FastAPI (Python), JWT, Nginx |
| Application | Job Orchestration, Business Logic | Python 3.11, Celery 5 |
| AI Processing | Transcription, Scene Detection, Scoring | Whisper large-v3, PySceneDetect, Claude API |
| Video Processing | Clip Extraction, Format Conversion | FFmpeg 6, MoviePy |
| Data | Metadata, Job State, Feedback Log | PostgreSQL 15, Redis 7 |
| Storage | Raw Footage, Output Clips, Assets | AWS S3 / Cloudflare R2 |
| Infrastructure | Container Orchestration, Monitoring | Docker, Docker Compose, Grafana, Sentry |

# **4\. Komponen AI & Pipeline Pemrosesan**

## **4.1  Alur Pipeline Utama**

Setiap video yang diupload melewati pipeline berikut secara berurutan, dengan setiap tahap menghasilkan output yang menjadi input tahap berikutnya:

| \# | Tahap | Proses | Output |
| ----- | :---: | :---: | :---: |
| 1 | Ingest | Upload, validasi format, ekstraksi metadata (resolusi, durasi, codec) | Metadata JSON \+ file di S3 |
| 2 | Audio Extract | Ekstraksi track audio dari video menggunakan FFmpeg, normalisasi volume | File WAV 16kHz mono |
| 3 | Transcription | Whisper large-v3 memproses audio, menghasilkan teks \+ word-level timestamp | File SRT \+ transcript JSON |
| 4 | Scene Detection | PySceneDetect menganalisis perubahan visual frame-by-frame (threshold adaptif) | Daftar timecode scene boundary |
| 5 | Energy Scoring | Analisis amplitudo audio per segmen \+ optical flow motion score | Score numerik per segmen |
| 6 | LLM Scoring | Claude API mengevaluasi relevansi, kelengkapan, dan kualitas narasi setiap segmen | Score \+ reasoning per segmen |
| 7 | Clip Ranking | Agregasi semua skor, penghilangan duplikasi, pemilihan top-N klip terbaik | Ranked clip list JSON |
| 8 | Clip Export | FFmpeg memotong video berdasarkan timecode terpilih, encode ke target format | File MP4 per klip |
| 9 | Subtitle Embed | Burn-in SRT ke video atau sertakan file SRT terpisah | Final video \+ SRT |
| 10 | Delivery | Upload output ke S3, notifikasi ke dashboard, update job status | URL download \+ metadata |

## **4.2  Modul Whisper (Automatic Speech Recognition)**

### **Spesifikasi Teknis**

* Model: openai/whisper-large-v3 (1.5B parameters)

* Runtime: faster-whisper dengan CTranslate2 backend untuk inferensi 4× lebih cepat

* Hardware: GPU dengan min. 10GB VRAM (NVIDIA RTX 3080 atau equivalent cloud GPU)

* Input: WAV 16kHz mono, max 30 menit per chunk (chunking otomatis untuk video lebih panjang)

* Output: Teks lengkap \+ segmen per kalimat \+ word-level timestamps dalam format JSON

* Language detection: otomatis, dengan fallback ke Indonesian jika confidence rendah

* WER target: \<15% untuk audio jernih, \<25% untuk audio dengan noise moderat

## **4.3  Modul Scene Detection**

### **Spesifikasi Teknis**

* Library: PySceneDetect 0.6+ dengan detektor ContentDetector (histogram perbandingan frame)

* Threshold: adaptif (default 27.0, auto-adjusted berdasarkan jenis konten)

* Minimal scene duration: 3 detik (untuk menghindari flash cut yang tidak relevan)

* Maximal scene count: 150 scene per video (mencegah over-segmentation)

* Output: daftar (start\_time, end\_time, confidence\_score) per scene

## **4.4  Modul LLM Scoring (Claude API)**

### **Scoring Rubric**

| Dimensi Scoring | Bobot | Deskripsi |
| ----- | :---: | :---: |
| Completeness | 25% | Apakah segmen mengandung pikiran/informasi yang utuh dan tidak terpotong di tengah kalimat? |
| Relevance | 25% | Seberapa relevan konten segmen dengan topik utama video? Apakah ini informasi penting? |
| Engagement Potential | 20% | Seberapa besar kemungkinan segmen ini menarik perhatian penonton dalam 3 detik pertama? |
| Standalone Clarity | 20% | Apakah segmen dapat dipahami tanpa konteks video lainnya? |
| Energy & Emotion | 10% | Apakah ada emosi, humor, kejutan, atau momen impactful dalam segmen ini? |

# **5\. Model Data**

## **5.1  Entitas Utama**

| Entitas | Field Kunci | Tipe Data | Deskripsi |
| ----- | :---: | :---: | :---: |
| video\_jobs | job\_id (PK) | UUID | Job pemrosesan untuk setiap video yang diupload |
|  | user\_id (FK) | UUID | Referensi ke pengguna yang mengupload |
|  | status | ENUM | pending | processing | done | failed |
|  | s3\_input\_path | TEXT | Path file footage di S3 |
|  | metadata\_json | JSONB | Durasi, resolusi, codec, ukuran file |
| segments | segment\_id (PK) | UUID | Segmen/scene yang terdeteksi dari video |
|  | job\_id (FK) | UUID | Referensi ke video\_jobs |
|  | start\_time / end\_time | FLOAT | Timecode dalam detik |
|  | transcript\_text | TEXT | Transkrip teks segmen tersebut |
|  | scores\_json | JSONB | Semua dimensi skor: completeness, relevance, dst. |
| clips | clip\_id (PK) | UUID | Klip final yang di-approve untuk export |
|  | segment\_id (FK) | UUID | Referensi ke segmen sumber |
|  | editor\_decision | ENUM | pending | approved | rejected | edited |
|  | output\_paths\_json | JSONB | URL S3 untuk setiap format output (9:16, 16:9, 1:1) |
| feedback\_log | log\_id (PK) | UUID | Rekaman keputusan editor untuk training dataset |
|  | clip\_id (FK) | UUID | Referensi ke klip yang dinilai |
|  | action | ENUM | approve | reject | edit | adjust\_trim |
|  | comment\_text | TEXT | Komentar opsional dari editor |

# **6\. Keamanan & Privasi**

## **6.1  Autentikasi & Otorisasi**

* Semua akses dashboard menggunakan JWT (JSON Web Token) dengan expiry 8 jam

* Refresh token disimpan di HTTP-only cookie (mencegah XSS)

* Role-based access: Admin, Editor, Viewer

* API key untuk integrasi eksternal menggunakan format opaque token, disimpan hashed di database

## **6.2  Enkripsi Data**

* Data in-transit: TLS 1.3 untuk semua koneksi (HTTP, S3, database, Redis)

* Data at-rest: S3 server-side encryption (AES-256), PostgreSQL pgcrypto untuk field sensitif

* API key dan secret disimpan menggunakan Vault atau environment variable terenkripsi

## **6.3  Kebijakan Data Klien**

* Raw footage klien tidak digunakan untuk training model tanpa persetujuan tertulis

* Footage dan output dihapus otomatis dari S3 setelah 30 hari (kecuali diatur lain)

* Feedback log dari editor disimpan terpisah dan di-anonymize sebelum digunakan untuk training

* Akses log semua aktivitas disimpan minimal 90 hari untuk audit trail

# **7\. Skalabilitas & Performa**

## **7.1  Bottleneck yang Diidentifikasi**

| Komponen | Bottleneck | Strategi Scale |
| ----- | :---: | :---: |
| Whisper Inference | GPU VRAM & throughput | Scale-out GPU workers di cloud; batching audio chunks |
| FFmpeg Processing | CPU-intensive encoding | Tambah worker CPU; hardware-accelerated encoding (NVENC) |
| S3 I/O | Upload/download bandwidth | CDN untuk download; multipart upload untuk file besar |
| Claude API | Rate limit & latency | Caching response untuk segmen identik; request batching |
| Database | Query complexity pada segment table | Indeks pada job\_id \+ status; partitioning per bulan |

## **7.2  Target Performa v1.0**

* Video 10 menit: processing selesai dalam 25 menit (2.5× durasi)

* Video 30 menit: processing selesai dalam 60 menit (2× durasi)

* Concurrent jobs: 3 video simultan tanpa degradasi performa signifikan

* Dashboard response time: \< 500ms untuk semua operasi UI

* API response time: \< 200ms untuk semua endpoint non-processing

# **8\. Monitoring & Observabilitas**

## **8.1  Metrik yang Dipantau**

| Kategori | Metrik | Tool / Alert |
| ----- | :---: | :---: |
| Infrastructure | CPU, RAM, GPU VRAM, disk usage | Grafana \+ Prometheus; alert jika GPU VRAM \> 90% |
| Application | Job queue length, processing time per tahap | Grafana; alert jika queue \> 10 jobs pending |
| AI Quality | WER per video, approval rate klip AI | Dashboard internal; weekly review oleh team |
| Error Tracking | Exceptions, failed jobs, API errors | Sentry; alert realtime ke Slack |
| Cost | API usage (Whisper \+ Claude), S3 storage, GPU cost | Dashboard AWS/RunPod; alert jika \> threshold bulanan |

# **9\. Estimasi Biaya Infrastruktur (Bulanan)**

| Komponen | Spesifikasi | Estimasi Biaya | Keterangan |
| ----- | :---: | :---: | :---: |
| GPU Cloud (RunPod/Vast.ai) | RTX 3080 / A4000, on-demand | Rp 1.200.000 | \~20 jam/bulan usage |
| Object Storage (S3/R2) | 100GB storage \+ transfer | Rp 150.000 | Tergantung volume footage |
| Server Aplikasi (VPS) | 4 vCPU, 8GB RAM, SSD | Rp 300.000 | DigitalOcean / Linode |
| Database (PostgreSQL managed) | 2 vCPU, 4GB RAM | Rp 200.000 | Neon / Supabase |
| Claude API | \~100 video/bulan x Rp 3.000/video | Rp 300.000 | Input \+ output tokens |
| Redis (managed) | Cache \+ queue | Rp 100.000 | Upstash / Redis Cloud |
| Monitoring (Grafana Cloud) | Free tier \+ alerting | Rp 0 | Upgrade jika diperlukan |
| **TOTAL ESTIMASI / BULAN** |  |  | **Rp 2.250.000** |

*Estimasi di atas berlaku untuk volume \~100 video/bulan pada fase internal. Biaya akan meningkat secara proporsional saat scale ke SaaS. GPU cost dapat ditekan hingga 70% dengan menggunakan Whisper medium model untuk video non-premium.*

# **10\. Roadmap Teknis Lanjutan**

| Versi | Target Q | Pengembangan Teknis Utama |
| ----- | :---: | :---: |
| v1.0 | Q3 2025 | Pipeline dasar: Whisper \+ Scene Detection \+ LLM Scoring \+ Web Dashboard Internal |
| v1.5 | Q4 2025 | Speaker diarization, face tracking, auto color grading (LUT inference), human RLHF loop |
| v2.0 | Q1 2026 | Brand template engine, motion graphics otomatis, REST API publik, webhook system |
| v3.0 | Q2 2026 | Multi-tenant SaaS, billing (Midtrans/Stripe), white-label, fine-tuned scoring model |

*Dokumen ini akan diperbarui setiap awal sprint baru. Perubahan signifikan pada arsitektur memerlukan review dari Tech Lead dan Product Owner.*