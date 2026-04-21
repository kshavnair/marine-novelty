'use client';

import { useState, useEffect } from 'react';
import dynamic from 'next/dynamic';
import { motion } from "framer-motion";
import { Search, MapPin, Loader2, AlertCircle, Info } from "lucide-react";
import Navigation from "@/components/Navigation";

// Dynamically import map components to avoid SSR issues
const MapContainer = dynamic(() => import('react-leaflet').then(mod => mod.MapContainer), {
  ssr: false,
  loading: () => (
    <div className="w-full h-full flex items-center justify-center bg-gray-100 rounded-2xl">
      <div className="text-center">
        <Loader2 className="w-8 h-8 animate-spin mx-auto mb-2 text-blue-500" />
        <p className="text-gray-600">Loading map...</p>
      </div>
    </div>
  )
});
const TileLayer = dynamic(() => import('react-leaflet').then(mod => mod.TileLayer), { ssr: false });
const Marker = dynamic(() => import('react-leaflet').then(mod => mod.Marker), { ssr: false });
const Popup = dynamic(() => import('react-leaflet').then(mod => mod.Popup), { ssr: false });
const Circle = dynamic(() => import('react-leaflet').then(mod => mod.Circle), { ssr: false });

interface SpeciesResult {
  scientific_name: string;
  common_names: string[];
  description: string;
  concentration: string;
  family: string;
  latitude: number;
  longitude: number;
}

export default function MapPage() {
  const [searchTerm, setSearchTerm] = useState('');
  const [speciesResults, setSpeciesResults] = useState<SpeciesResult[]>([]);
  const [selectedSpecies, setSelectedSpecies] = useState<SpeciesResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  // Configure Leaflet icons on client side only
  useEffect(() => {
    if (typeof window !== 'undefined') {
      const L = require('leaflet');
      delete (L.Icon.Default.prototype as any)._getIconUrl;
      L.Icon.Default.mergeOptions({
        iconRetinaUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon-2x.png',
        iconUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon.png',
        shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-shadow.png',
      });
    }
  }, []);

  const searchSpecies = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!searchTerm.trim()) return;

    setLoading(true);
    setError('');
    try {
      const response = await fetch(
        `http://localhost:8000/search?query=${encodeURIComponent(searchTerm)}`
      );
      
      if (!response.ok) {
        throw new Error('Failed to search species');
      }
      
      const data = await response.json();
      setSpeciesResults(data.results);
      
      if (data.results.length === 0) {
        setError('No species found. Try searching for: dolphin, tuna, salmon, octopus, or oyster');
      } else if (data.results.length === 1) {
        setSelectedSpecies(data.results[0]);
      }
    } catch (err) {
      setError('Failed to search species. Make sure backend is running on port 8000.');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-cyan-50">
      <Navigation currentPage="map" />

      <div className="container mx-auto px-4 py-8">
        <motion.div
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          className="text-center mb-8"
        >
          <h1 className="text-4xl md:text-5xl font-bold text-gray-800 mb-4">
            Marine Species <span className="text-blue-600">Location Map</span>
          </h1>
          <p className="text-lg text-gray-600 max-w-2xl mx-auto">
            Search for marine species to see their concentration areas and habitat distribution worldwide
          </p>
        </motion.div>

        {/* Search Section */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="bg-white rounded-2xl shadow-xl p-6 mb-8"
        >
          <form onSubmit={searchSpecies} className="flex gap-2">
            <div className="flex-1 relative">
              <input
                type="text"
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                placeholder="Search by common name: dolphin, tuna, salmon, octopus, oyster..."
                className="w-full px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
            <button
              type="submit"
              disabled={loading}
              className="bg-blue-600 hover:bg-blue-700 disabled:bg-gray-400 text-white px-6 py-3 rounded-xl font-semibold flex items-center gap-2 transition-colors"
            >
              {loading ? <Loader2 className="w-5 h-5 animate-spin" /> : <Search className="w-5 h-5" />}
              Search
            </button>
          </form>
        </motion.div>

        {/* Search Results */}
        {speciesResults.length > 1 && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="bg-white rounded-2xl shadow-xl p-6 mb-8"
          >
            <h3 className="text-xl font-semibold mb-4">Found {speciesResults.length} species:</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {speciesResults.map((species) => (
                <button
                  key={species.scientific_name}
                  onClick={() => setSelectedSpecies(species)}
                  className="p-4 border-2 border-gray-200 rounded-lg hover:border-blue-500 hover:bg-blue-50 transition-all text-left"
                >
                  <p className="font-semibold text-blue-600">{species.description}</p>
                  <p className="text-sm text-gray-600">{species.scientific_name}</p>
                </button>
              ))}
            </div>
          </motion.div>
        )}

        {/* Error Message */}
        {error && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="bg-red-50 border-l-4 border-red-500 p-4 mb-8 rounded-lg flex gap-3"
          >
            <AlertCircle className="w-5 h-5 text-red-500 flex-shrink-0" />
            <p className="text-red-700">{error}</p>
          </motion.div>
        )}

        {/* Species Info & Map */}
        {selectedSpecies && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="grid grid-cols-1 lg:grid-cols-3 gap-8"
          >
            {/* Species Information Panel */}
            <motion.div
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              className="lg:col-span-1 bg-white rounded-2xl shadow-xl p-6 h-fit"
            >
              <div className="flex items-start gap-3 mb-4">
                <div className="w-12 h-12 bg-blue-100 rounded-full flex items-center justify-center">
                  <Info className="w-6 h-6 text-blue-600" />
                </div>
                <div className="flex-1">
                  <h2 className="text-2xl font-bold text-gray-800">{selectedSpecies.description}</h2>
                  <p className="text-sm text-gray-500 italic">{selectedSpecies.scientific_name}</p>
                </div>
              </div>

              <div className="space-y-4">
                <div>
                  <h3 className="font-semibold text-gray-700 mb-2">Common Names</h3>
                  <div className="flex flex-wrap gap-2">
                    {selectedSpecies.common_names.map((name) => (
                      <span key={name} className="bg-blue-100 text-blue-700 px-3 py-1 rounded-full text-sm">
                        {name}
                      </span>
                    ))}
                  </div>
                </div>

                <div>
                  <h3 className="font-semibold text-gray-700 mb-2 flex items-center gap-2">
                    <MapPin className="w-4 h-4 text-red-500" />
                    Concentration Area
                  </h3>
                  <p className="text-gray-600 bg-amber-50 p-3 rounded-lg">
                    {selectedSpecies.concentration}
                  </p>
                </div>

                <div>
                  <h3 className="font-semibold text-gray-700 mb-2">Family</h3>
                  <p className="text-gray-600">{selectedSpecies.family}</p>
                </div>

                <div>
                  <h3 className="font-semibold text-gray-700 mb-2">Coordinates</h3>
                  <p className="text-sm text-gray-600">
                    Lat: {selectedSpecies.latitude.toFixed(2)}°<br />
                    Lon: {selectedSpecies.longitude.toFixed(2)}°
                  </p>
                </div>
              </div>
            </motion.div>

            {/* Map */}
            <motion.div
              initial={{ opacity: 0, x: 20 }}
              animate={{ opacity: 1, x: 0 }}
              className="lg:col-span-2 bg-white rounded-2xl shadow-xl overflow-hidden"
            >
              <MapContainer center={[selectedSpecies.latitude, selectedSpecies.longitude]} zoom={4} style={{ height: '500px' }}>
                <TileLayer
                  url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
                  attribution='&copy; OpenStreetMap contributors'
                />
                {/* Main marker */}
                <Marker position={[selectedSpecies.latitude, selectedSpecies.longitude]}>
                  <Popup>
                    <div className="text-sm">
                      <p className="font-semibold">{selectedSpecies.description}</p>
                      <p className="text-xs text-gray-600">{selectedSpecies.scientific_name}</p>
                      <p className="text-xs mt-1">Primary concentration area</p>
                    </div>
                  </Popup>
                </Marker>
                {/* Concentration zone */}
                <Circle
                  center={[selectedSpecies.latitude, selectedSpecies.longitude]}
                  radius={500000}
                  pathOptions={{ color: 'blue', fillOpacity: 0.1 }}
                />
              </MapContainer>
            </motion.div>
          </motion.div>
        )}
      </div>
    </div>
  );
}