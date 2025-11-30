import React, { useState, useCallback, useRef } from "react";
import {
  fetchWithRetry,
  parseExternalServiceError,
  DEFAULT_EXTERNAL_RETRY_CONFIG,
} from "../../utils/fetchWithRetry";

export interface SesameResolverProps {
  /** Callback when coordinates are resolved */
  onResolved: (ra: number, dec: number, objectName: string) => void;
  /** Custom class name */
  className?: string;
}

type SesameService = "all" | "simbad" | "ned" | "vizier";

interface ResolveResult {
  ra: number;
  dec: number;
  objectName: string;
  service: string;
}

// Simple in-memory cache for resolved objects
const resolveCache = new Map<string, ResolveResult>();

/**
 * Sesame name resolver component.
 * Resolves astronomical object names to coordinates using CDS Sesame service.
 */
const SesameResolver: React.FC<SesameResolverProps> = ({ onResolved, className = "" }) => {
  const [objectName, setObjectName] = useState("");
  const [service, setService] = useState<SesameService>("all");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<ResolveResult | null>(null);

  // AbortController for request cancellation
  const abortControllerRef = useRef<AbortController | null>(null);

  const resolveObject = useCallback(async () => {
    const trimmedName = objectName.trim();
    if (!trimmedName) {
      setError("Please enter an object name");
      return;
    }

    // Check cache first
    const cacheKey = `${service}:${trimmedName.toLowerCase()}`;
    const cached = resolveCache.get(cacheKey);
    if (cached) {
      setResult(cached);
      setError(null);
      onResolved(cached.ra, cached.dec, cached.objectName);
      return;
    }

    // Cancel any pending request
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
    abortControllerRef.current = new AbortController();

    setIsLoading(true);
    setError(null);
    setResult(null);

    try {
      // Use CDS Sesame service via their API
      // Format: https://cdsweb.u-strasbg.fr/cgi-bin/nph-sesame/-oI/A?object_name
      const serviceCode = service === "all" ? "A" : service.charAt(0).toUpperCase();
      const url = `https://cdsweb.u-strasbg.fr/cgi-bin/nph-sesame/-oI/${serviceCode}?${encodeURIComponent(
        trimmedName
      )}`;

      const response = await fetch(url, {
        signal: abortControllerRef.current.signal,
      });

      if (!response.ok) {
        throw new Error(`HTTP error: ${response.status}`);
      }

      const text = await response.text();

      // Parse the Sesame response
      // Format includes lines like:
      // %J 83.63308 +22.01450 = 05 34 31.94 +22 00 52.2
      const jLine = text.split("\n").find((line) => line.startsWith("%J"));

      if (!jLine) {
        throw new Error("Could not resolve object. Please check the name and try again.");
      }

      const match = jLine.match(/%J\s+([\d.+-]+)\s+([\d.+-]+)/);
      if (!match) {
        throw new Error("Failed to parse coordinates from response.");
      }

      const ra = parseFloat(match[1]);
      const dec = parseFloat(match[2]);

      const resolved: ResolveResult = {
        ra,
        dec,
        objectName: trimmedName,
        service,
      };

      // Cache the result
      resolveCache.set(cacheKey, resolved);

      setResult(resolved);
      onResolved(ra, dec, trimmedName);
    } catch (err) {
      // Don't show error for aborted requests
      if (err instanceof Error && err.name === "AbortError") {
        return;
      }
      const message = err instanceof Error ? err.message : "Resolution failed";
      // Distinguish network errors
      if (message.includes("fetch") || message.includes("network")) {
        setError("Network error. CORS may be blocking the request. Try using a backend proxy.");
      } else {
        setError(message);
      }
    } finally {
      setIsLoading(false);
    }
  }, [objectName, service, onResolved]);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter") {
      resolveObject();
    }
  };

  return (
    <div className={`space-y-3 ${className}`}>
      <div className="flex gap-2">
        <input
          type="text"
          value={objectName}
          onChange={(e) => setObjectName(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Object name (e.g., M31, Crab Nebula, PSR J0534+2200)"
          className="form-control flex-1"
        />
        <button
          onClick={resolveObject}
          disabled={isLoading || !objectName.trim()}
          className="btn btn-primary"
        >
          {isLoading ? (
            <span className="flex items-center gap-1">
              <span className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
              Resolving...
            </span>
          ) : (
            "Resolve"
          )}
        </button>
      </div>

      {/* Service selection */}
      <div className="flex items-center gap-4 text-sm">
        <span className="text-gray-600">Service:</span>
        {(["all", "simbad", "ned", "vizier"] as SesameService[]).map((svc) => (
          <label key={svc} className="flex items-center gap-1 cursor-pointer">
            <input
              type="radio"
              name="sesame-service"
              value={svc}
              checked={service === svc}
              onChange={() => setService(svc)}
              className="w-4 h-4 text-vast-green"
            />
            <span className="capitalize">{svc === "all" ? "All" : svc.toUpperCase()}</span>
          </label>
        ))}
      </div>

      {/* Error display */}
      {error && (
        <div className="text-red-600 text-sm flex items-center gap-1">
          <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
            <path
              fillRule="evenodd"
              d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z"
              clipRule="evenodd"
            />
          </svg>
          {error}
        </div>
      )}

      {/* Success display */}
      {result && (
        <div className="text-green-600 text-sm flex items-center gap-1">
          <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
            <path
              fillRule="evenodd"
              d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z"
              clipRule="evenodd"
            />
          </svg>
          <span>
            Resolved: RA={result.ra.toFixed(6)}°, Dec={result.dec.toFixed(6)}°
          </span>
        </div>
      )}
    </div>
  );
};

export default SesameResolver;
