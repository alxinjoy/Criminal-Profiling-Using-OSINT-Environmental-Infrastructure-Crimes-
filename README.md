# 🌍 EcoProfiler  
### **Criminal Forensic Profiling Using OSINT for Environmental & Infrastructure Crimes**

<p align="center">
  <img src="https://img.shields.io/badge/Built%20With-FastAPI-blue?style=for-the-badge"/>
  <img src="https://img.shields.io/badge/Frontend-React%20%2B%20Vite-green?style=for-the-badge"/>
  <img src="https://img.shields.io/badge/Status-Production%20Ready-success?style=for-the-badge"/>
  <img src="https://img.shields.io/badge/Domain-OSINT%20%7C%20Environmental%20Forensics-purple?style=for-the-badge"/>
</p>

---

# 📌 Overview  

**EcoProfiler** is a full-stack forensic OSINT intelligence system engineered to detect, analyze, and correlate **environmental crimes**, **industrial misconduct**, and **illegal land-use activities** using **global satellite data + open-source intelligence platforms**.

The platform builds **Forensic Dossiers** that combine:

- 🌲 Forest loss (Hansen GFC)  
- 🔥 Fire anomalies (NASA FIRMS)  
- 🛰️ GLAD & RADD alerts (Global Forest Watch)  
- 🎨 Sentinel Hub imagery (NDVI, NBR, Burn Index, TrueColor)  
- 🏭 Industrial proximity detection (OSM Overpass)  
- 🏢 Corporate identity (GLEIF LEI data)  
- 📰 News sentiment (Google CSE + GDELT)  
- 🧵 Community sentiment (Reddit API)  
- 🔗 Evidence correlation engine  
- 📝 Confidence scoring (0–100)  

The end result is an **automatic global crime profiler for environmental violations**, visualized through a **modern investigative dashboard**.

---

# ⚡ Key Features  

## 🔎 **Backend — FastAPI (OSINT Intelligence Core)**  
✔ Cross-validated forensic dossiers  
✔ Automated satellite evidence extraction  
✔ Industrial infrastructure detection  
✔ Corporate entity enrichment (LEI)  
✔ Fire–Loss–Factory correlation engine  
✔ Sentiment aggregation (Google, GDELT, Reddit)  
✔ Dataset coverage awareness  
✔ Structured `source_errors` & `coverage_notes`  
✔ Raw payload archiving for reproducibility  
✔ Full diagnostic `/health` endpoint  

---

## 📊 **Frontend — React + Tailwind + Leaflet**  
✔ Global interactive investigative map  
✔ TrueColor, NDVI, NBR overlays  
✔ Fire, loss, GLAD/RADD layers  
✔ Factory markers + suspect profiles  
✔ Impact analysis charts  
✔ Sentinel preview viewer  
✔ Error boundaries + UI fallbacks  
✔ Data source status widget  
✔ One-click *Export Dossier JSON*  

---

# 🧱 Project Architecture  

```
┌───────────────────────────────────────────────────────────────┐
│                           FRONTEND                            │
│   React + Vite + Tailwind + Leaflet + Recharts                │
│   • Investigative Map                                          │
│   • Evidence Dashboard                                          │
│   • Suspect Profiles                                            │
│   • Data Source Health Monitor                                  │
└───────────────▲───────────────────────────────────────────────┘
                │ REST API
                ▼
┌───────────────────────────────────────────────────────────────┐
│                             BACKEND                            │
│                      FastAPI OSINT Engine                      │
│  - Satellite Intel     - Social Sentiment                      │
│  - Overpass Infra      - Corporate Profiling                   │
│  - Evidence Fusion     - Confidence Scoring                    │
└───────────────▲───────────────────────────────────────────────┘
                │ External Providers
                ▼
      GEE • GFW • SentinelHub • Overpass • GLEIF • GDELT • Reddit
```

---

# 🛰️ Data Sources (Coverage Included)

| Source | Description | Coverage |
|--------|-------------|----------|
| Hansen GFC | Annual forest loss | Global |
| NASA FIRMS | Active fire detections | Global |
| GFW GLAD | Optical loss alerts | Tropical belt |
| GFW RADD | Radar loss alerts | Humid tropics |
| Sentinel Hub | TrueColor, NDVI, NBR | Global (quota required) |
| OSM Overpass | Factories/industry | Global (varies by region) |
| GLEIF | Corporate identity | Global |
| Google CSE | News sentiment | Global |
| GDELT | Global Knowledge Graph | Global |
| Reddit API | Community sentiment | Global (rate-limited) |

---

# 🧩 Backend Setup

## 📁 Install dependencies
```bash
cd backend
python -m venv venv
venv\Scriptsctivate
pip install -r requirements.txt
```

## 🔐 Create `secrets/` folder
```
backend/secrets/gee.json
```

## ⚙️ Environment setup
```
cp .env.example .env
```

Fill in:
- GEE credentials  
- SentinelHub client ID/secret  
- GFW API key  
- Google CSE  
- Reddit credentials  

## ▶️ Run backend
```
uvicorn app.main_api:app --reload --port 8000
```

---

# 🎨 Frontend Setup

```bash
cd frontend
npm install
cp .env.example .env
npm run dev
```

`VITE_API_BASE_URL=http://localhost:8000`

---

# 🐳 Docker Deployment  

From project root:
```bash
docker compose up --build
```

Frontend → port **3000**  
Backend → port **8000**

---

# 🚨 Dossier Evidence Logic

A suspect is linked when:

1. Industrial site within **≤5 km** of an event  
2. Event occurred within **±14 days**  
3. Sentinel indices show NDVI/NBR drop  
4. News + community sentiment is negative  

Outputs:

```json
{
  "confidence_score": 87,
  "evidence_chain": [
    "Factory X detected 3.2 km from fire event at T-2 days",
    "NDVI dropped 0.28 indicating vegetation loss",
    "Google/GDELT sentiment: strongly negative"
  ]
}
```

---

# 🌐 Future-Proof Notes  

APIs that may change:

### Google Earth Engine
- May require new service accounts  
- Dataset names may change  

### Sentinel Hub
- Tokens expire  
- Process API may update  

### Reddit
- API access is restricted since 2023  

### GFW
- Endpoints may change names  

The README encourages maintainers to check official docs.

---

# 🚀 Roadmap

- AI anomaly detection  
- PostGIS + geospatial DB  
- PDF dossier generator  
- Cloud-native deployment (K8s)  
- Offline inference mode  
- Pushshift v2 integration  

---

# 🙏 Credits

Powered by modern OSINT, satellite analytics, and investigative intelligence tooling.  
Architected with advanced LLM guidance to ensure industry-level structure & clarity.

---

# 📎 END OF FILE
