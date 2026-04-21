'use client';

import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from "framer-motion";
import { Dna, Upload, Loader2, CheckCircle, AlertCircle, Clock, Zap, FlaskConical, RefreshCw } from "lucide-react";

interface Prediction {
  species: string;
  confidence: number;
  description: string;
  database_source?: string;
  scores?: Record<string, number>;
  is_match?: boolean;
  is_novel?: boolean;
  is_uncertain?: boolean;
}

interface ModelStatus {
  status: string;
  ncbi_healthy: boolean;
  ncbi_sequences: number;
  fallback_sequences: number;
  database_sources: Record<string, string>;
  species?: string[];
}

// Normalise scores so the top species = 100% for display purposes
// Converts absolute cosine similarity to relative ranking
function normaliseScores(scores: Record<string, number>): Record<string, number> {
  const values = Object.values(scores);
  const max = Math.max(...values);
  if (max <= 0) return scores;
  return Object.fromEntries(
    Object.entries(scores).map(([k, v]) => [k, Math.round((v / max) * 100)])
  );
}

// Backend may return confidence either as cosine score (0-1) or percentage (0-100).
// Normalize to cosine first, then map to user-facing 0-100 confidence band.
function toDisplayConfidence(raw: number): number {
  const cosine = raw > 1 ? raw / 100 : raw;

  // Map: 0.4 (novel threshold) -> 0%, 0.75 (match threshold) -> 100%
  if (cosine < 0.40) return 0;
  if (cosine >= 0.75) return 100;

  const confidence = ((cosine - 0.40) / (0.75 - 0.40)) * 100;
  return Math.round(Math.max(0, Math.min(100, confidence)));
}

function confidenceLabel(pct: number): { label: string; color: string } {
  // Based on CNN cosine similarity thresholds: 0.75+ (match), 0.55-0.75 (uncertain), <0.40 (novel)
  if (pct >= 85) return { label: 'Very high confidence', color: '#059669' };
  if (pct >= 65) return { label: 'High confidence', color: '#10b981' };
  if (pct >= 45) return { label: 'Moderate confidence', color: '#d97706' };
  if (pct >= 20) return { label: 'Low confidence', color: '#f97316' };
  return { label: 'Very low / Novel', color: '#dc2626' };
}

export default function EDNAPage() {
  const [sequence, setSequence] = useState('');
  const [prediction, setPrediction] = useState<Prediction | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [nextUpdate, setNextUpdate] = useState<string>('Loading...');
  const [modelStatus, setModelStatus] = useState<ModelStatus | null>(null);
  const [submittedSeqLen, setSubmittedSeqLen] = useState<number | null>(null);

  useEffect(() => {
    const fetchStatus = async () => {
      try {
        const response = await fetch('http://localhost:8000/model-status');
        if (!response.ok) throw new Error(`API error: ${response.status}`);
        const status = await response.json();
        setModelStatus(status);
        setNextUpdate(new Date(status.next_update).toLocaleString());
      } catch (err) {
        console.error('Failed to fetch model status:', err);
        setNextUpdate('Unable to load — backend may be starting up');
      }
    };
    fetchStatus();
    const interval = setInterval(fetchStatus, 5000);
    return () => clearInterval(interval);
  }, []);

  const identifySpecies = async () => {
    const trimmed = sequence.trim();
    if (!trimmed) return;

    // ── FIX 1: Always clear previous result before a new request ──────────
    setPrediction(null);
    setError('');
    setLoading(true);
    setSubmittedSeqLen(trimmed.replace(/[^ATCGatcg]/g, '').length);

    try {
      const response = await fetch('http://localhost:8000/predict', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        // ── FIX 2: Always send the current textarea value, trimmed ─────────
        body: JSON.stringify({ sequence: trimmed }),
      });

      if (!response.ok) {
        const detail = await response.json().catch(() => ({}));
        throw new Error(detail?.detail ?? `HTTP ${response.status}`);
      }

      const result: Prediction = await response.json();
      setPrediction(result);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err);
      setError(`Failed to identify species: ${msg}`);
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleFileUpload = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;
    // ── FIX 3: Reset result when a new file is loaded ─────────────────────
    setPrediction(null);
    setError('');
    const reader = new FileReader();
    reader.onload = (e) => {
      const content = e.target?.result as string;
      setSequence(content);
    };
    reader.readAsText(file);
  };

  const handleReset = () => {
    setSequence('');
    setPrediction(null);
    setError('');
    setSubmittedSeqLen(null);
  };

  // ── Derived display values ────────────────────────────────────────────────
  const normScores = prediction?.scores ? normaliseScores(prediction.scores) : null;
  const displayConf = prediction ? toDisplayConfidence(prediction.confidence) : 0;
  const confMeta = confidenceLabel(displayConf);

  const resultBg = prediction?.is_novel
    ? 'from-purple-50 to-violet-50 border-purple-200'
    : prediction?.is_uncertain
    ? 'from-amber-50 to-yellow-50 border-amber-200'
    : 'from-emerald-50 to-teal-50 border-emerald-200';

  const resultIcon = prediction?.is_novel
    ? <FlaskConical className="w-7 h-7 text-purple-500" />
    : prediction?.is_uncertain
    ? <AlertCircle className="w-7 h-7 text-amber-500" />
    : <CheckCircle className="w-7 h-7 text-emerald-500" />;

  const resultHeading = prediction?.is_novel
    ? 'Novel / Unrecognised Sequence'
    : prediction?.is_uncertain
    ? 'Uncertain Match'
    : 'Species Identified';

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50 to-cyan-50 py-10">
      <div className="container mx-auto px-4 max-w-3xl">

        {/* ── Header ───────────────────────────────────────────────────── */}
        <motion.div
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          className="text-center mb-10"
        >
          <div className="flex items-center justify-center gap-3 mb-3">
            <Dna className="w-9 h-9 text-blue-600" />
            <h1 className="text-4xl font-bold text-gray-800">
              eDNA <span className="text-blue-600">Identifier</span>
            </h1>
          </div>
          <p className="text-gray-500 max-w-xl mx-auto">
            Paste or upload a COI barcode sequence to identify marine species against our NCBI reference database.
          </p>
        </motion.div>

        {/* ── Input card ───────────────────────────────────────────────── */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="bg-white rounded-2xl shadow-lg p-7 mb-6"
        >
          <h2 className="text-lg font-semibold mb-3 flex items-center gap-2 text-gray-700">
            <Upload className="w-5 h-5 text-blue-500" />
            DNA Sequence Input
          </h2>

          <textarea
            value={sequence}
            onChange={(e) => {
              setSequence(e.target.value);
              // ── FIX 4: Clear stale result whenever user edits the box ──
              if (prediction) setPrediction(null);
              if (error) setError('');
            }}
            placeholder="Paste FASTA or raw nucleotide sequence here (ATCG)…"
            className="w-full h-36 p-4 border border-gray-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-400 resize-none font-mono text-sm bg-gray-50"
          />

          <div className="flex items-center justify-between mt-3">
            <div className="flex items-center gap-3">
              <label className="flex items-center gap-2 px-3 py-1.5 bg-gray-100 hover:bg-gray-200 rounded-lg cursor-pointer text-sm transition-colors">
                <Upload className="w-4 h-4" />
                Upload .fasta / .txt
                <input
                  type="file"
                  accept=".txt,.fasta,.fa"
                  onChange={handleFileUpload}
                  className="hidden"
                />
              </label>
              {sequence && (
                <button
                  onClick={handleReset}
                  className="flex items-center gap-1 text-xs text-gray-400 hover:text-gray-600 transition-colors"
                >
                  <RefreshCw className="w-3 h-3" /> Reset
                </button>
              )}
            </div>
            <span className="text-xs text-gray-400">
              {sequence.replace(/[^ATCGatcg]/g, '').length} bp
            </span>
          </div>

          <button
            onClick={identifySpecies}
            disabled={loading || !sequence.trim()}
            className="mt-5 w-full bg-blue-600 hover:bg-blue-700 disabled:bg-gray-300 text-white py-3.5 rounded-xl font-semibold text-base transition-colors flex items-center justify-center gap-2"
          >
            {loading ? (
              <><Loader2 className="w-5 h-5 animate-spin" /> Analysing…</>
            ) : (
              <><Zap className="w-5 h-5" /> Identify Species</>
            )}
          </button>
        </motion.div>

        {/* ── Error ────────────────────────────────────────────────────── */}
        <AnimatePresence>
          {error && (
            <motion.div
              key="error"
              initial={{ opacity: 0, y: -8 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0 }}
              className="bg-red-50 border border-red-200 text-red-700 px-5 py-4 rounded-xl flex items-center gap-3 mb-6 text-sm"
            >
              <AlertCircle className="w-5 h-5 flex-shrink-0" />
              {error}
            </motion.div>
          )}
        </AnimatePresence>

        {/* ── Result card ──────────────────────────────────────────────── */}
        <AnimatePresence mode="wait">
          {prediction && (
            <motion.div
              key={prediction.species + prediction.confidence}
              initial={{ opacity: 0, y: 16 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -8 }}
              transition={{ duration: 0.25 }}
              className={`bg-gradient-to-br ${resultBg} border rounded-2xl p-7 mb-6`}
            >
              {/* Heading */}
              <div className="flex items-center gap-2 mb-5">
                {resultIcon}
                <h2 className="text-lg font-bold text-gray-800">{resultHeading}</h2>
                {submittedSeqLen && (
                  <span className="ml-auto text-xs text-gray-400">{submittedSeqLen} bp analysed</span>
                )}
              </div>

              {/* Species + confidence */}
              <div className="grid sm:grid-cols-2 gap-5 mb-5">
                <div className="bg-white/70 rounded-xl p-4">
                  <p className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-1">Species</p>
                  <p className="text-xl font-bold text-blue-800 italic leading-tight">{prediction.species}</p>
                  {prediction.database_source && (
                    <span className={`mt-2 inline-block text-xs px-2 py-0.5 rounded-full font-medium ${
                      prediction.database_source === 'NCBI'
                        ? 'bg-blue-100 text-blue-700'
                        : 'bg-amber-100 text-amber-700'
                    }`}>
                      {prediction.database_source === 'NCBI' ? '🌐 NCBI live' : '📦 Fallback DB'}
                    </span>
                  )}
                </div>

                <div className="bg-white/70 rounded-xl p-4">
                  <p className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-1">Match strength</p>
                  <div className="flex items-center gap-2 mb-2">
                    <span className="text-2xl font-bold" style={{ color: confMeta.color }}>
                      {displayConf}%
                    </span>
                    <span className="text-xs font-medium" style={{ color: confMeta.color }}>
                      {confMeta.label}
                    </span>
                  </div>
                  <div className="w-full bg-gray-200 rounded-full h-2">
                    <motion.div
                      initial={{ width: 0 }}
                      animate={{ width: `${displayConf}%` }}
                      transition={{ duration: 0.6, ease: 'easeOut' }}
                      className="h-2 rounded-full"
                      style={{ backgroundColor: confMeta.color }}
                    />
                  </div>
                  {/* Raw score for transparency */}
                  <p className="text-xs text-gray-400 mt-1.5">
                    Raw similarity score: {(prediction.confidence > 1 ? prediction.confidence / 100 : prediction.confidence).toFixed(4)}
                  </p>
                </div>
              </div>

              {/* Description */}
              <div className="bg-white/60 rounded-xl p-4 mb-5 text-sm text-gray-600 leading-relaxed">
                {prediction.description}
              </div>

              {/* All-species scores — normalised so best = 100% */}
              {normScores && (
                <div>
                  <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-3">
                    All species — relative match (best = 100%)
                  </p>
                  <div className="space-y-2.5">
                    {Object.entries(normScores)
                      .sort(([, a], [, b]) => b - a)
                      .map(([sp, pct]) => {
                        const isTop = sp === prediction.species;
                        return (
                          <div key={sp}>
                            <div className="flex justify-between items-center mb-1">
                              <span className={`text-sm ${isTop ? 'font-bold text-gray-800' : 'text-gray-500'}`}>
                                {isTop && '→ '}{sp}
                              </span>
                              <span className={`text-sm font-semibold ${isTop ? 'text-blue-700' : 'text-gray-400'}`}>
                                {pct}%
                              </span>
                            </div>
                            <div className="w-full bg-gray-100 rounded-full h-1.5">
                              <motion.div
                                initial={{ width: 0 }}
                                animate={{ width: `${pct}%` }}
                                transition={{ duration: 0.5, ease: 'easeOut' }}
                                className="h-1.5 rounded-full"
                                style={{ backgroundColor: isTop ? '#2563eb' : '#9ca3af' }}
                              />
                            </div>
                          </div>
                        );
                      })}
                  </div>
                </div>
              )}
            </motion.div>
          )}
        </AnimatePresence>

        {/* ── DB status ────────────────────────────────────────────────── */}
        {modelStatus && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.3 }}
            className="bg-white rounded-2xl shadow-lg p-7"
          >
            <h2 className="text-lg font-bold mb-5 flex items-center gap-2 text-gray-700">
              <Clock className="w-5 h-5 text-blue-500" />
              Database status
            </h2>
            <div className="grid grid-cols-3 gap-4 mb-5">
              <div className="bg-blue-50 border border-blue-100 rounded-xl p-4 text-center">
                <p className="text-2xl font-bold text-blue-600">{modelStatus.ncbi_sequences}</p>
                <p className="text-xs text-gray-500 mt-1">NCBI live</p>
              </div>
              <div className="bg-amber-50 border border-amber-100 rounded-xl p-4 text-center">
                <p className="text-2xl font-bold text-amber-600">{modelStatus.fallback_sequences}</p>
                <p className="text-xs text-gray-500 mt-1">Fallback</p>
              </div>
              <div className={`border rounded-xl p-4 text-center ${modelStatus.ncbi_healthy ? 'bg-emerald-50 border-emerald-100' : 'bg-yellow-50 border-yellow-100'}`}>
                <p className={`text-sm font-bold ${modelStatus.ncbi_healthy ? 'text-emerald-600' : 'text-yellow-600'}`}>
                  {modelStatus.ncbi_healthy ? '✓ Healthy' : '⚠ Partial'}
                </p>
                <p className="text-xs text-gray-500 mt-1">Status</p>
              </div>
            </div>
            <p className="text-xs text-gray-400">
              Next refresh: <span className="font-medium text-gray-500">{nextUpdate}</span>
            </p>
          </motion.div>
        )}

      </div>
    </div>
  );
}