'use client';

import Link from "next/link";
import { motion } from "framer-motion";
import { MapPin, Dna, Search, Waves, Fish, Globe } from "lucide-react";

export default function Home() {
  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-900 via-blue-800 to-indigo-900 text-white overflow-hidden">
      {/* Animated background */}
      <div className="absolute inset-0">
        {/* Floating particles */}
        <div className="absolute inset-0">
          {[...Array(20)].map((_, i) => (
            <motion.div
              key={i}
              className="absolute w-2 h-2 bg-blue-300 rounded-full opacity-20"
              animate={{
                x: [0, Math.random() * 100 - 50],
                y: [0, Math.random() * 100 - 50],
              }}
              transition={{
                duration: Math.random() * 10 + 10,
                repeat: Infinity,
                repeatType: "reverse",
              }}
              style={{
                left: `${Math.random() * 100}%`,
                top: `${Math.random() * 100}%`,
              }}
            />
          ))}
        </div>

        {/* Ocean waves */}
        <div className="absolute bottom-0 w-full">
          <svg
            className="w-full h-64"
            viewBox="0 0 1200 120"
            preserveAspectRatio="none"
          >
            <motion.path
              d="M0,60 C300,100 600,20 900,60 C1050,80 1200,40 1200,60 L1200,120 L0,120 Z"
              fill="rgba(255,255,255,0.1)"
              animate={{
                d: [
                  "M0,60 C300,100 600,20 900,60 C1050,80 1200,40 1200,60 L1200,120 L0,120 Z",
                  "M0,40 C300,80 600,10 900,50 C1050,70 1200,30 1200,50 L1200,120 L0,120 Z",
                  "M0,60 C300,100 600,20 900,60 C1050,80 1200,40 1200,60 L1200,120 L0,120 Z"
                ]
              }}
              transition={{ duration: 8, repeat: Infinity }}
            />
            <motion.path
              d="M0,80 C250,120 500,40 750,80 C900,100 1050,60 1200,80 L1200,120 L0,120 Z"
              fill="rgba(255,255,255,0.05)"
              animate={{
                d: [
                  "M0,80 C250,120 500,40 750,80 C900,100 1050,60 1200,80 L1200,120 L0,120 Z",
                  "M0,60 C250,100 500,20 750,60 C900,80 1050,40 1200,60 L1200,120 L0,120 Z",
                  "M0,80 C250,120 500,40 750,80 C900,100 1050,60 1200,80 L1200,120 L0,120 Z"
                ]
              }}
              transition={{ duration: 6, repeat: Infinity }}
            />
          </svg>
        </div>
      </div>

      <div className="relative z-10 flex flex-col items-center justify-center min-h-screen px-4">
        <motion.div
          initial={{ opacity: 0, y: 50 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 1 }}
          className="text-center max-w-5xl"
        >
          <motion.div
            initial={{ scale: 0.8 }}
            animate={{ scale: 1 }}
            transition={{ duration: 0.8, delay: 0.2 }}
            className="mb-8"
          >
            <Waves className="w-20 h-20 mx-auto mb-4 text-blue-300" />
            <h1 className="text-6xl md:text-8xl font-bold mb-6 bg-gradient-to-r from-blue-200 to-cyan-200 bg-clip-text text-transparent">
              Ocean Species
            </h1>
            <h2 className="text-3xl md:text-5xl font-light text-blue-100">
              Discovery Platform
            </h2>
          </motion.div>

          <motion.p
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 1, delay: 0.5 }}
            className="text-xl md:text-2xl mb-12 text-blue-200 max-w-3xl mx-auto leading-relaxed"
          >
            Empowering marine researchers with cutting-edge technology to explore, identify, and understand ocean biodiversity through interactive maps and AI-powered species recognition.
          </motion.p>

          <motion.div
            initial={{ opacity: 0, y: 30 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 1, delay: 0.8 }}
            className="flex flex-col sm:flex-row gap-6 justify-center mb-16"
          >
            <Link
              href="/map"
              className="group bg-gradient-to-r from-blue-500 to-cyan-500 hover:from-blue-600 hover:to-cyan-600 px-8 py-4 rounded-2xl font-semibold text-lg transition-all duration-300 transform hover:scale-105 hover:shadow-2xl flex items-center gap-3"
            >
              <Globe className="w-6 h-6" />
              Explore Global Map
              <MapPin className="w-5 h-5 group-hover:translate-x-1 transition-transform" />
            </Link>
            <Link
              href="/edna"
              className="group bg-transparent border-2 border-white hover:bg-white hover:text-blue-900 px-8 py-4 rounded-2xl font-semibold text-lg transition-all duration-300 transform hover:scale-105 hover:shadow-2xl flex items-center gap-3"
            >
              <Dna className="w-6 h-6" />
              Identify eDNA
              <Search className="w-5 h-5 group-hover:translate-x-1 transition-transform" />
            </Link>
          </motion.div>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 50 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 1, delay: 1.2 }}
          className="grid grid-cols-1 md:grid-cols-3 gap-8 max-w-6xl w-full"
        >
          {[
            {
              icon: Globe,
              title: "Interactive Maps",
              description: "Explore species distributions worldwide with real-time data from GBIF and thermal mapping technology.",
              color: "from-blue-400 to-blue-600"
            },
            {
              icon: Search,
              title: "Advanced Search",
              description: "Powerful search tools to discover marine species patterns and ecological insights.",
              color: "from-cyan-400 to-cyan-600"
            },
            {
              icon: Dna,
              title: "AI Species ID",
              description: "Upload environmental DNA sequences for instant species identification using machine learning.",
              color: "from-teal-400 to-teal-600"
            }
          ].map((feature, index) => (
            <motion.div
              key={feature.title}
              initial={{ opacity: 0, y: 30 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.8, delay: 1.4 + index * 0.2 }}
              className={`bg-gradient-to-br ${feature.color} bg-opacity-20 backdrop-blur-lg rounded-2xl p-8 border border-white border-opacity-20 hover:bg-opacity-30 transition-all duration-300 transform hover:scale-105 hover:shadow-2xl`}
            >
              <feature.icon className="w-12 h-12 mb-6 text-white" />
              <h3 className="text-2xl font-bold mb-4">{feature.title}</h3>
              <p className="text-blue-100 leading-relaxed">{feature.description}</p>
            </motion.div>
          ))}
        </motion.div>

        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 1, delay: 2 }}
          className="mt-16 text-center"
        >
          <div className="flex items-center justify-center gap-2 text-blue-300">
            <Fish className="w-5 h-5 animate-bounce" />
            <span className="text-sm">Powered by OBIS • GBIF • NCBI</span>
            <Fish className="w-5 h-5 animate-bounce" style={{ animationDelay: '0.5s' }} />
          </div>
        </motion.div>
      </div>
    </div>
  );
}
