import Link from "next/link";
import { ArrowLeft, Home, MapPin, Dna } from "lucide-react";

interface NavigationProps {
  showBack?: boolean;
  currentPage?: 'map' | 'edna';
}

export default function Navigation({ showBack = true, currentPage }: NavigationProps) {
  return (
    <nav className="bg-white/10 backdrop-blur-md border-b border-white/20 sticky top-0 z-50">
      <div className="container mx-auto px-4 py-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            {showBack && (
              <Link
                href="/"
                className="flex items-center gap-2 text-white hover:text-blue-200 transition-colors"
              >
                <ArrowLeft className="w-5 h-5" />
                <span className="hidden sm:inline">Back to Home</span>
              </Link>
            )}
            <Link
              href="/"
              className="flex items-center gap-2 text-white hover:text-blue-200 transition-colors"
            >
              <Home className="w-5 h-5" />
              <span className="font-semibold">Ocean Species Discovery</span>
            </Link>
          </div>

          <div className="flex items-center gap-4">
            <Link
              href="/map"
              className={`flex items-center gap-2 px-3 py-2 rounded-lg transition-colors ${
                currentPage === 'map'
                  ? 'bg-blue-500 text-white'
                  : 'text-white hover:text-blue-200 hover:bg-white/10'
              }`}
            >
              <MapPin className="w-4 h-4" />
              <span className="hidden sm:inline">Map</span>
            </Link>
            <Link
              href="/edna"
              className={`flex items-center gap-2 px-3 py-2 rounded-lg transition-colors ${
                currentPage === 'edna'
                  ? 'bg-blue-500 text-white'
                  : 'text-white hover:text-blue-200 hover:bg-white/10'
              }`}
            >
              <Dna className="w-4 h-4" />
              <span className="hidden sm:inline">eDNA</span>
            </Link>
          </div>
        </div>
      </div>
    </nav>
  );
}