This is a [Next.js](https://nextjs.org) project bootstrapped with [`create-next-app`](https://nextjs.org/docs/app/api-reference/cli/create-next-app).

## Getting Started

First, run the development server:

```bash
npm run dev
# or
yarn dev
# or
pnpm dev
# or
bun dev
```

Open [http://localhost:3000](http://localhost:3000) with your browser to see the result.

You can start editing the page by modifying `app/page.tsx`. The page auto-updates as you edit the file.

This project uses [`next/font`](https://nextjs.org/docs/app/building-your-application/optimizing/fonts) to automatically optimize and load [Geist](https://vercel.com/font), a new font family for Vercel.

## Learn More

To learn more about Next.js, take a look at the following resources:

- [Next.js Documentation](https://nextjs.org/docs) - learn about Next.js features and API.
- [Learn Next.js](https://nextjs.org/learn) - an interactive Next.js tutorial.

You can check out [the Next.js GitHub repository](https://github.com/vercel/next.js) - your feedback and contributions are welcome!

## Deploy on Vercel

The easiest way to deploy your Next.js app is to use the [Vercel Platform](https://vercel.com/new?utm_medium=default-template&filter=next.js&utm_source=create-next-app&utm_campaign=create-next-app-readme) from the creators of Next.js.

Check out our [Next.js deployment documentation](https://nextjs.org/docs/app/building-your-application/deploying) for more details.

# 🌊 Marine Species eDNA Identification API

## 📌 Overview

The **Marine Species eDNA Identification API** is a bioinformatics-based backend system designed to identify marine species from DNA sequences using **COI (Cytochrome Oxidase I) barcoding**.

The system combines:

* Local sequence alignment (Smith-Waterman)
* K-mer frequency analysis
* Real-time NCBI data fetching

Built using **FastAPI**, this API provides accurate, scalable, and production-ready species classification.

---

## 🚀 Features

* 🔬 **DNA Sequence Classification** using COI barcodes
* 🌐 **NCBI Integration** for real biological data
* 🧠 **Hybrid Scoring System**

  * 70% Alignment-based similarity
  * 30% K-mer cosine similarity
* 🧩 **Open-set Recognition**

  * Detects unknown / novel species
* 🔄 **Automatic Weekly Model Refresh**
* 🛡 **Fallback System** when NCBI is unavailable
* 📊 Detailed confidence scoring and classification

---

## 🧬 Supported Species

| Scientific Name   | Common Name     |
| ----------------- | --------------- |
| Delphinus delphis | Dolphin         |
| Thunnus albacares | Yellowfin Tuna  |
| Salmo salar       | Atlantic Salmon |
| Octopus vulgaris  | Octopus         |
| Crassostrea gigas | Pacific Oyster  |

---

## ⚙️ Installation

### 1. Clone the repository

```bash
git clone https://github.com/your-repo/marine-edna-api.git
cd marine-edna-api
```

### 2. Create virtual environment

```bash
python -m venv venv
source venv/bin/activate   # Linux/Mac
venv\Scripts\activate      # Windows
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

---

## ▶️ Running the Server

```bash
python main.py
```

OR using uvicorn:

```bash
uvicorn main:app --reload
```

Server will run at:

```
http://localhost:8000
```

---

## 📡 API Endpoints

### 🔹 1. Predict Species

**POST** `/predict`

#### Request:

```json
{
  "sequence": "ATGACGACGCTGAC..."
}
```

#### Response:

```json
{
  "species": "Salmo salar",
  "confidence": 92.5,
  "is_match": true,
  "is_uncertain": false,
  "is_novel": false,
  "scores": {...}
}
```

---

### 🔹 2. Model Status

**GET** `/model-status`

Returns:

* Loaded species
* NCBI vs fallback data
* Update timestamps

---

### 🔹 3. Search Species

**GET** `/search?query=salmon`

---

### 🔹 4. Get Species Info

**GET** `/species/{name}`

---

### 🔹 5. All Species

**GET** `/all-species`

---

### 🔹 6. Health Check

**GET** `/health`

---

## 🧠 Methodology

### 1. Sequence Preprocessing

* Removes FASTA headers
* Filters non-ATCG characters

### 2. Feature Extraction

* Generates k-mers (k=6)
* Converts sequences into vectors

### 3. Similarity Computation

#### 🔹 Local Alignment

* Smith-Waterman algorithm
* Position-aware similarity

#### 🔹 K-mer Cosine Similarity

* Frequency-based comparison
* Robust for short sequences

### 4. Final Score

```
Final Score = 0.70 × Alignment + 0.30 × K-mer Similarity
```

---

## 🎯 Classification Logic

| Condition                    | Result           |
| ---------------------------- | ---------------- |
| Score ≥ 0.80 & margin ≥ 0.10 | ✅ Match          |
| 0.70 ≤ Score < 0.80          | ⚠️ Uncertain     |
| Score < 0.70                 | 🧬 Novel Species |

---

## 🔄 Data Source Strategy

* Primary: **NCBI database (live fetch)**
* Backup: Predefined fallback sequences

Ensures:

* Reliability
* High availability

---

## 🛡 Input Constraints

| Condition          | Action         |
| ------------------ | -------------- |
| Length < 30 bp     | Rejected       |
| Length > 2000 bp   | Marked invalid |
| Non-DNA characters | Removed        |

---

## 🧱 Project Structure

```
marine-edna-api/
│
├── main.py                # Main FastAPI application
├── requirements.txt      # Dependencies
├── README.md             # Documentation
└── data/                 # (Optional future datasets)
```

---

## 🔬 Future Improvements

* Add more species (expand database)
* Use ML classifiers (CNN / Transformer on DNA)
* Integrate BLAST API
* Build frontend dashboard
* Support multi-gene analysis

---

## 👨‍💻 Author

Developed as part of an **AI/ML + Bioinformatics project** for marine species identification using environmental DNA (eDNA).

---

## 📜 License

This project is for academic and research purposes.

---

## ⭐ Acknowledgements

* NCBI (National Center for Biotechnology Information)
* COI Barcoding Standards
* Bioinformatics community

---

