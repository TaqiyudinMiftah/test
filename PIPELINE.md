# AutoClip AI - Cara Kerja Pipeline

Dokumen ini menjelaskan secara detail bagaimana pipeline AutoClip AI bekerja dari awal hingga akhir.

---

## 🎯 Gambaran Umum

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│   Upload    │───▶│   Ingest    │───▶│   Audio     │───▶│Transcription│
│   Video     │    │  & Validate │    │   Extract   │    │  (Whisper)  │
└─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘
                                                                │
                                                                ▼
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│   Deliver   │◀───│   Export    │◀───│    Rank     │◀───│   LLM Score │
│   (URLs)    │    │   Clips     │    │    Clips    │    │  (Nemotron) │
└─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘
      ▲                                                        │
      │    ┌─────────────┐    ┌─────────────┐                 │
      └────│   Embed     │◀───│  Energy     │◀────────────────┘
           │  Subtitle   │    │   Score     │
           └─────────────┘    └─────────────┘
                            │
                            ▼
                    ┌─────────────┐
                    │   Scene     │
                    │  Detection  │
                    └─────────────┘
```

---

## 📊 Pipeline Flowchart Detail

```
User Upload Video (MP4/MOV)
         │
         ▼
┌─────────────────────────┐
│      TASK 1: INGEST     │
│  ├─ Validasi format     │
│  ├─ Ekstrak metadata    │
│  │   (durasi, resolusi) │
│  ├─ Upload ke MinIO     │
│  └─ Update status:      │
│      PROCESSING         │
└─────────────────────────┘
         │
         ▼
┌─────────────────────────┐
│   TASK 2: AUDIO EXTRACT │
│  ├─ Download dari MinIO │
│  ├─ FFmpeg: extract     │
│  │   audio → WAV        │
│  ├─ 16kHz, mono         │
│  ├─ Normalisasi volume  │
│  └─ Upload ke MinIO     │
│      temp/audio.wav     │
└─────────────────────────┘
         │
         ▼
┌─────────────────────────┐
│  TASK 3: TRANSCRIBE     │
│  ├─ Download audio.wav  │
│  ├─ faster-whisper      │
│  │   (base model)       │
│  ├─ Generate:           │
│  │   • transcript.json  │
│  │   • subtitle.srt     │
│  ├─ Word-level          │
│  │   timestamps         │
│  └─ Upload ke MinIO     │
└─────────────────────────┘
         │
         ▼
┌─────────────────────────┐
│  TASK 4: SCENE DETECT   │
│  ├─ Download video      │
│  ├─ PySceneDetect       │
│  ├─ ContentDetector     │
│  │   (threshold: 27)    │
│  ├─ Min scene: 3 detik  │
│  ├─ Max scene: 150      │
│  └─ Output: scenes.json │
└─────────────────────────┘
         │
         ▼
┌─────────────────────────┐
│   TASK 5: ENERGY SCORE  │
│  ├─ Download video +    │
│  │   audio              │
│  ├─ Audio RMS per scene │
│  ├─ Optical Flow        │
│  │   (OpenCV) per scene │
│  ├─ Agregasi skor:      │
│  │   50% audio +        │
│  │   50% motion         │
│  ├─ Insert ke DB:       │
│  │   segments table     │
│  └─ Simpan transcript   │
│      per segment        │
└─────────────────────────┘
         │
         ▼
┌─────────────────────────┐
│   TASK 6: LLM SCORE     │
│  ├─ Ambil setiap        │
│  │   segment dari DB    │
│  ├─ OpenRouter API      │
│  │   (Nemotron 120B)    │
│  ├─ 5-dimension scoring:│
│  │   • Completeness 25% │
│  │   • Relevance 25%    │
│  │   • Engagement 20%   │
│  │   • Clarity 20%      │
│  │   • Emotion 10%      │
│  ├─ Retry 3x jika gagal │
│  ├─ Cache di Redis      │
│  └─ Update skor di DB   │
└─────────────────────────┘
         │
         ▼
┌─────────────────────────┐
│   TASK 7: RANK CLIPS    │
│  ├─ Ambil semua         │
│  │   segments dari DB   │
│  ├─ Agregasi skor:      │
│  │   weighted average   │
│  ├─ Deduplikasi:        │
│  │   IoU > 0.8 dihapus  │
│  ├─ Pilih top-10        │
│  ├─ Insert ke DB:       │
│  │   clips table        │
│  │   (status: pending)  │
│  └─ Trigger export      │
└─────────────────────────┘
         │
         ▼
┌─────────────────────────┐
│   TASK 8: EXPORT CLIPS  │
│  ├─ Download video      │
│  ├─ Untuk setiap clip:  │
│  │   • Cut video        │
│  │   • Generate 3       │
│  │     format:          │
│  │     - 9:16 (vertical)│
│  │     - 16:9 (wide)    │
│  │     - 1:1 (square)   │
│  ├─ Encode: H.264       │
│  ├─ CRF 23, preset      │
│  │   medium             │
│  └─ Upload ke MinIO     │
│      output/            │
└─────────────────────────┘
         │
         ▼
┌─────────────────────────┐
│   TASK 9: SUBTITLE      │
│   EMBED                 │
│  ├─ SRT sudah ada dari  │
│  │   task 3             │
│  ├─ Burn-in atau        │
│  │   sertakan terpisah  │
│  └─ (v2.0: burn-in)     │
└─────────────────────────┘
         │
         ▼
┌─────────────────────────┐
│   TASK 10: DELIVER      │
│  ├─ Generate presigned  │
│  │   URLs (15 menit)    │
│  ├─ Update job status:  │
│  │   DONE               │
│  ├─ Update clips:       │
│  │   output_paths_json  │
│  └─ Siap di-download!   │
└─────────────────────────┘
         │
         ▼
    ✅ SELESAI!
```

---

## 🔧 Alur Kerja Teknis

### 1. Upload Video
**File**: `app/api/jobs.py`

```
User ──POST /api/v1/jobs──▶ Backend
                              │
                              ├─ Validasi format (MP4/MOV)
                              ├─ Cek ukuran (< 4GB)
                              ├─ Simpan temporary
                              ├─ Upload ke MinIO (raw/)
                              ├─ Create job di DB
                              └─ Trigger: ingest_task.delay()
```

**Response ke User:**
```json
{
  "id": "uuid",
  "status": "pending",
  "original_filename": "video.mp4"
}
```

---

### 2. Task 1: Ingest
**File**: `app/workers/tasks/ingest.py`

**Input**: Job ID
**Output**: Metadata JSON

```python
async def _ingest_async(job_id):
    # 1. Ambil job dari database
    job = await db.get(job_id)
    
    # 2. Update status ke PROCESSING
    job.status = "processing"
    
    # 3. Download dari MinIO
    await s3_service.download_file(path, local_path)
    
    # 4. Validasi dengan ffprobe
    ffprobe -v error -show_entries format=format_name
    ffprobe -v error -select_streams v:0 -show_entries stream=codec_name
    
    # 5. Ekstrak metadata
    metadata = {
        "duration": 120.5,      # detik
        "width": 1920,          # pixel
        "height": 1080,         # pixel
        "fps": 30,              # frame per second
        "codec": "h264",        # video codec
        "bitrate": 5000000      # bits per second
    }
    
    # 6. Simpan metadata ke DB
    job.metadata_json = metadata
    
    # 7. Trigger task berikutnya
    audio_extract_task.delay(job_id)
```

**Error Handling:**
- Jika codec tidak didukung → FAILED
- Jika file corrupt → FAILED
- Retry 3x dengan interval 60 detik

---

### 3. Task 2: Audio Extract
**File**: `app/workers/tasks/audio_extract.py`

**Input**: Job ID
**Output**: File WAV

```bash
# Command FFmpeg yang dijalankan:
ffmpeg -y -i input.mp4 \
    -vn \                          # No video
    -acodec pcm_s16le \            # 16-bit PCM
    -ar 16000 \                     # Sample rate 16kHz
    -ac 1 \                         # Mono channel
    -af loudnorm \                  # Normalisasi volume
    output.wav
```

**Alur Kerja:**
```
Download video ──▶ FFmpeg extract ──▶ WAV 16kHz mono
                                           │
                                           ▼
                                    Upload ke MinIO
                                    temp/audio.wav
                                           │
                                           ▼
                                    Trigger transcribe_task
```

---

### 4. Task 3: Transcribe
**File**: `app/workers/tasks/transcribe.py`

**Input**: File WAV
**Output**: transcript.json + subtitle.srt

```python
# Model Whisper
model = WhisperModel("base", device="cpu", compute_type="int8")

# Transkripsi
segments, info = model.transcribe(
    audio_path,
    beam_size=5,
    word_timestamps=True  # Timestamp per kata
)

# Output structure:
transcript_data = {
    "language": "id",           # Bahasa terdeteksi
    "language_probability": 0.95,
    "duration": 120.5,
    "segments": [
        {
            "id": 0,
            "start": 0.0,       # detik
            "end": 5.2,
            "text": "Halo semuanya",
            "words": [
                {"word": "Halo", "start": 0.0, "end": 0.8},
                {"word": "semuanya", "start": 0.9, "end": 1.5}
            ]
        }
    ]
}
```

**Subtitle SRT Format:**
```
1
00:00:00,000 --> 00:00:05,200
Halo semuanya

2
00:00:05,200 --> 00:00:10,100
Selamat datang di video ini
```

---

### 5. Task 4: Scene Detection
**File**: `app/workers/tasks/scene_detect.py`

**Input**: Video file
**Output**: scenes.json

```python
# PySceneDetect
video = open_video(local_path)
scene_manager = SceneManager()
scene_manager.add_detector(
    ContentDetector(
        threshold=27.0,           # Sensitivitas deteksi
        min_scene_len=3           # Minimal 3 detik
    )
)

# Deteksi
scene_manager.detect_scenes(video)
scene_list = scene_manager.get_scene_list()

# Output (max 150 scene):
scenes = [
    {"start": 0.0, "end": 5.2, "duration": 5.2},
    {"start": 5.2, "end": 12.1, "duration": 6.9},
    {"start": 12.1, "end": 18.5, "duration": 6.4},
    # ... dst
]
```

**Algoritma:**
- Bandingkan histogram frame demi frame
- Jika perbedaan > threshold → scene baru
- Skip jika durasi < 3 detik
- Batasi max 150 scene

---

### 6. Task 5: Energy Score
**File**: `app/workers/tasks/energy_score.py`

**Input**: Video + Audio + Scenes
**Output**: Energy score per scene

```python
# A. Audio Energy (RMS)
for scene in scenes:
    start_sample = int(scene["start"] * sample_rate)
    end_sample = int(scene["end"] * sample_rate)
    segment_audio = audio_data[start_sample:end_sample]
    rms = np.sqrt(np.mean(segment_audio**2))
    scene["audio_energy"] = rms

# B. Motion Score (Optical Flow)
cap = cv2.VideoCapture(video_path)
for scene in scenes:
    # Ambil 2 detik pertama dari scene
    # Hitung optical flow antar frame
    flow = cv2.calcOpticalFlowFarneback(prev, curr, ...)
    magnitude = np.sqrt(flow[..., 0]**2 + flow[..., 1]**2)
    scene["motion_score"] = np.mean(magnitude)

# C. Agregasi
scene["energy_score"] = (
    scene["audio_energy"] * 0.5 +
    scene["motion_score"] * 0.5
)

# D. Insert ke Database
for scene in scenes:
    segment = Segment(
        job_id=job_id,
        start_time=scene["start"],
        end_time=scene["end"],
        transcript_text=get_transcript_for_scene(scene),
        energy_score=scene["energy_score"]
    )
    db.add(segment)
```

---

### 7. Task 6: LLM Score
**File**: `app/workers/tasks/llm_score.py`

**Input**: Segments dari DB
**Output**: Skor 5 dimensi per segment

```python
# Untuk setiap segment:
for segment in segments:
    if not segment.transcript_text:
        continue
    
    # Kirim ke OpenRouter API
    scores = await llm_scorer.score_segment(
        transcript=segment.transcript_text,
        duration=segment.end_time - segment.start_time,
        video_topic="Video"  # Dari metadata
    )
    
    # Update database
    segment.llm_completeness = scores["completeness"]  # 1-10
    segment.llm_relevance = scores["relevance"]         # 1-10
    segment.llm_engagement = scores["engagement"]       # 1-10
    segment.llm_clarity = scores["clarity"]             # 1-10
    segment.llm_emotion = scores["emotion"]             # 1-10
    
    # Total score (weighted)
    segment.llm_total_score = (
        scores["completeness"] * 0.25 +
        scores["relevance"] * 0.25 +
        scores["engagement"] * 0.20 +
        scores["clarity"] * 0.20 +
        scores["emotion"] * 0.10
    )
```

**Prompt ke LLM:**
```
Kamu adalah AI video editor senior. Tugasmu mengevaluasi segmen video berikut.

SEGmen:
- Transkrip: "{transcript}"
- Durasi: {duration} detik
- Topik Video: {video_topic}

DIMENSI:
1. Completeness (25%): Apakah segmen berisi informasi yang utuh?
2. Relevance (25%): Seberapa relevan dengan topik?
3. Engagement (20%): Seberapa menarik perhatian?
4. Clarity (20%): Dapat dipahami tanpa konteks?
5. Emotion (10%): Ada emosi/kejutan?

OUTPUT JSON:
{
    "completeness": {"score": 8, "reasoning": "..."},
    "relevance": {"score": 9, "reasoning": "..."},
    ...
}
```

**Retry Strategy:**
```python
for attempt in range(3):
    try:
        response = await api_call()
        break
    except:
        if attempt < 2:
            time.sleep(2 ** attempt)  # 2s, 4s, 8s
        else:
            # Fallback: nilai default 5.0
```

---

### 8. Task 7: Rank Clips
**File**: `app/workers/tasks/rank_clips.py`

**Input**: Segments dengan skor
**Output**: Top-10 clips

```python
# 1. Ambil semua segments
segments = await db.execute(
    SELECT * FROM segments 
    WHERE job_id = job_id
    ORDER BY llm_total_score DESC
)

# 2. Deduplikasi dengan IoU
def calculate_iou(seg1, seg2):
    intersection = max(0, min(seg1.end, seg2.end) - max(seg1.start, seg2.start))
    union = (seg1.end - seg1.start) + (seg2.end - seg2.start) - intersection
    return intersection / union

filtered = []
for seg in segments:
    is_duplicate = False
    for selected in filtered:
        if calculate_iou(seg, selected) > 0.8:
            is_duplicate = True
            break
    if not is_duplicate:
        filtered.append(seg)

# 3. Pilih top-10
top_segments = filtered[:10]

# 4. Insert ke clips table
for seg in top_segments:
    clip = Clip(
        job_id=job_id,
        segment_id=seg.id,
        editor_decision="pending",
        start_time=seg.start_time,
        end_time=seg.end_time
    )
    db.add(clip)

# 5. Trigger export
export_clips_task.delay(job_id)
```

---

### 9. Task 8: Export Clips
**File**: `app/workers/tasks/export_clip.py`

**Input**: Clips + Video original
**Output**: MP4 files (3 format)

```bash
# Untuk setiap clip dan setiap format:

# Format 9:16 (Vertical - Shorts/Reels)
ffmpeg -y -i input.mp4 \
    -ss {start_time} \
    -t {duration} \
    -vf "scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2" \
    -c:v libx264 -crf 23 -preset medium \
    -c:a aac -b:a 128k \
    -movflags +faststart \
    clip_9x16.mp4

# Format 16:9 (Wide - YouTube)
ffmpeg -y -i input.mp4 \
    -ss {start_time} \
    -t {duration} \
    -vf "scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2" \
    -c:v libx264 -crf 23 -preset medium \
    clip_16x9.mp4

# Format 1:1 (Square - Feed)
ffmpeg -y -i input.mp4 \
    -ss {start_time} \
    -t {duration} \
    -vf "scale=1080:1080:force_original_aspect_ratio=decrease,pad=1080:1080:(ow-iw)/2:(oh-ih)/2" \
    -c:v libx264 -crf 23 -preset medium \
    clip_1x1.mp4
```

**Output Structure:**
```json
{
  "9:16": "output/job_id/clip_id_9x16.mp4",
  "16:9": "output/job_id/clip_id_16x9.mp4",
  "1:1": "output/job_id/clip_id_1x1.mp4"
}
```

---

### 10. Task 9: Subtitle Embed
**File**: `app/workers/tasks/embed_subtitle.py`

**Input**: SRT file + Clips
**Output**: Video dengan subtitle

```python
# Saat ini (v1.0):
# - SRT sudah di-generate di task 3
# - Sertakan sebagai file terpisah
# - Burn-in subtitle akan di v2.0

# Trigger task berikutnya
deliver_task.delay(job_id)
```

---

### 11. Task 10: Deliver
**File**: `app/workers/tasks/deliver.py`

**Input**: Clips + Output paths
**Output**: Presigned URLs

```python
# Generate presigned URLs (15 menit expiry)
for clip in clips:
    urls = {}
    for fmt, path in clip.output_paths_json.items():
        object_name = s3_service.get_object_name_from_path(path)
        url = await s3_service.get_presigned_url(
            object_name,
            expiry=900  # 15 menit
        )
        urls[fmt] = url
    clip.output_paths_json = urls

# Update job status
job.status = "done"
job.s3_output_prefix = f"output/{job_id}/"

# User sekarang bisa download!
```

---

## 📈 Timeline Processing

| Durasi Video | Estimasi Waktu | Tahapan Paling Lama |
|:---|:---|:---|
| 10 menit | ~25 menit | Transcription + Export |
| 30 menit | ~60 menit | Transcription + Export |
| 1 jam | ~2 jam | Transcription + LLM Score |

**Bottleneck:**
1. **Transcription** (Whisper) - 40% waktu
2. **Export** (FFmpeg) - 30% waktu
3. **LLM Scoring** (OpenRouter) - 20% waktu
4. **Lainnya** - 10% waktu

---

## 🔄 Retry & Error Handling

| Task | Max Retry | Interval | Fallback |
|:---|:---|:---|:---|
| Ingest | 3x | 60 detik | FAILED |
| Audio Extract | 3x | 60 detik | FAILED |
| Transcribe | 3x | 120 detik | FAILED |
| Scene Detect | 3x | 60 detik | FAILED |
| Energy Score | 3x | 60 detik | FAILED |
| LLM Score | 3x | Exponential | Default 5.0 |
| Export | 3x | 60 detik | FAILED |
| Deliver | 3x | 60 detik | FAILED |

---

## 🗄️ Data Flow Database

```
┌─────────────┐
│  video_jobs │
│  id (PK)    │
│  status     │◀── Setiap task update status
│  metadata   │◀── Task 1 (Ingest)
│  error_msg  │◀── Jika error
└──────┬──────┘
       │
       │ 1:N
       ▼
┌─────────────┐
│  segments   │
│  id (PK)    │
│  job_id(FK) │
│  start_time │
│  end_time   │
│  transcript │◀── Task 3
│  energy     │◀── Task 5
│  llm_*      │◀── Task 6
└──────┬──────┘
       │
       │ 1:1
       ▼
┌─────────────┐
│    clips    │
│  id (PK)    │
│  segment_id │
│  decision   │◀── User action
│  output     │◀── Task 8
└─────────────┘
```

---

## 🎯 Sequence Diagram

```
User    Frontend    Backend    Celery    MinIO    OpenRouter
 │         │           │          │         │          │
 │──Upload──▶│         │          │         │          │
 │         │───POST /api/v1/jobs──▶│        │          │
 │         │         │──Save──▶───│        │          │
 │         │         │──Trigger──▶│        │          │
 │         │         │◀──Job ID───│        │          │
 │         │◀──Response───────────│        │          │
 │         │         │          │         │          │
 │         │         │          │──Task1──▶│        │
 │         │         │          │──Task2──▶│        │
 │         │         │          │──Task3──▶│        │
 │         │         │          │──Task4──▶│        │
 │         │         │          │──Task5──▶│        │
 │         │         │          │──Task6──▶│──────▶│
 │         │         │          │──Task7──▶│        │
 │         │         │          │──Task8──▶│        │
 │         │         │          │──Task9──▶│        │
 │         │         │          │──Task10─▶│        │
 │         │         │          │         │          │
 │         │──GET /api/v1/jobs──▶│        │          │
 │         │         │──Query DB──│        │          │
 │         │◀──Status: done───────│        │          │
 │◀──URLs──│         │          │         │          │
 │         │         │          │         │          │
 │──Download──▶│     │          │         │          │
 │         │────GET (presigned)──▶│       │          │
 │◀──Video──│     │          │         │          │
```

---

## 📊 Monitoring Pipeline

```bash
# Cek status job
docker compose exec -w /app backend bash -c "PYTHONPATH=/app python -c \"
import asyncio
from app.database import AsyncSessionLocal
from sqlalchemy import select
from app.models.video_job import VideoJob

async def check():
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(VideoJob).order_by(VideoJob.created_at.desc()).limit(5))
        for job in result.scalars():
            print(f'{job.id}: {job.status} - {job.original_filename}')

asyncio.run(check())
\""
```

**Output:**
```
550e8400-e29b-41d4-a716-446655440000: done - video1.mp4
6ba7b810-9dad-11d1-80b4-00c04fd430c8: processing - video2.mp4
6ba7b811-9dad-11d1-80b4-00c04fd430c8: failed - video3.mp4
```

---

## 🔧 Troubleshooting Pipeline

### Job Stuck di "processing"
```bash
# Cek log celery
docker compose logs -f celery-worker

# Restart celery
docker compose restart celery-worker
```

### Transcription Error
```bash
# Cek apakah model whisper sudah download
docker compose exec backend ls -la /root/.cache/

# Restart task manual (jika perlu)
# (Butuh implementasi manual retry via API)
```

### LLM Score Timeout
```bash
# Cek koneksi OpenRouter
docker compose exec backend curl -I https://openrouter.ai/api/v1

# Cek API key valid
docker compose exec backend python -c "from app.config import settings; print(settings.OPENROUTER_API_KEY[:20])"
```

### Export Gagal
```bash
# Cek apakah FFmpeg berfungsi
docker compose exec backend ffmpeg -version

# Cek disk space
docker compose exec backend df -h
```

---

**Dokumen ini menjelaskan cara kerja lengkap pipeline AutoClip AI. Untuk command operasional, lihat [COMMANDS.md](COMMANDS.md).**
