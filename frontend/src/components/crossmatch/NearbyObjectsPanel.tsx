import React, { useState, useCallback, useEffect } from "react";

export interface NearbyObject {
  name: string;
  ra: string;
  dec: string;
  separation: number; // arcsec
  database: "SIMBAD" | "NED" | "ATNF" | "Local";
  type?: string;
  url?: string;
}

export interface NearbyObjectsPanelProps {
  /** Right Ascension in degrees */
  raDeg: number;
  /** Declination in degrees */
  decDeg: number;
  /** Initial search radius in arcminutes */
  initialRadius?: number;
  /** Maximum allowed radius */
  maxRadius?: number;
  /** Callback to fetch nearby objects */
  onSearch: (raDeg: number, decDeg: number, radiusArcmin: number) => Promise<NearbyObject[]>;
  /** Custom class name */
  className?: string;
  /** Exclude specific object by ID */
  excludeId?: string;
}

type SortKey = "name" | "database" | "separation";
type SortDir = "asc" | "desc";

/**
 * Panel for displaying nearby astronomical objects from multiple databases.
 * Queries SIMBAD, NED, ATNF Pulsars, and local database.
 */
const NearbyObjectsPanel: React.FC<NearbyObjectsPanelProps> = ({
  raDeg,
  decDeg,
  initialRadius = 2,
  maxRadius = 60,
  onSearch,
  className = "",
  excludeId,
}) => {
  const [radius, setRadius] = useState(initialRadius);
  const [results, setResults] = useState<NearbyObject[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [sortKey, setSortKey] = useState<SortKey>("separation");
  const [sortDir, setSortDir] = useState<SortDir>("asc");

  const performSearch = useCallback(async () => {
    setIsLoading(true);
    setError(null);

    try {
      const objects = await onSearch(raDeg, decDeg, radius);
      setResults(objects);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Search failed");
      setResults([]);
    } finally {
      setIsLoading(false);
    }
  }, [raDeg, decDeg, radius, onSearch]);

  // Auto-search on mount
  useEffect(() => {
    performSearch();
  }, []);

  const handleSort = useCallback((key: SortKey) => {
    setSortKey((prevKey) => {
      if (prevKey === key) {
        setSortDir((prev) => (prev === "asc" ? "desc" : "asc"));
      } else {
        setSortDir("asc");
      }
      return key;
    });
  }, []);

  const sortedResults = [...results].sort((a, b) => {
    let cmp = 0;
    switch (sortKey) {
      case "name":
        cmp = a.name.localeCompare(b.name);
        break;
      case "database":
        cmp = a.database.localeCompare(b.database);
        break;
      case "separation":
        cmp = a.separation - b.separation;
        break;
    }
    return sortDir === "asc" ? cmp : -cmp;
  });

  const getDatabaseColor = (db: NearbyObject["database"]) => {
    switch (db) {
      case "SIMBAD":
        return "badge-info";
      case "NED":
        return "badge-success";
      case "ATNF":
        return "badge-warning";
      case "Local":
        return "badge-secondary";
    }
  };

  const getDatabaseUrl = (obj: NearbyObject) => {
    if (obj.url) return obj.url;

    switch (obj.database) {
      case "SIMBAD":
        return `https://simbad.u-strasbg.fr/simbad/sim-id?Ident=${encodeURIComponent(obj.name)}`;
      case "NED":
        return `https://ned.ipac.caltech.edu/byname?objname=${encodeURIComponent(obj.name)}`;
      case "ATNF":
        return `https://www.atnf.csiro.au/research/pulsar/psrcat/proc_form.php?pulsar_names=${encodeURIComponent(
          obj.name
        )}`;
      default:
        return undefined;
    }
  };

  const SortArrow: React.FC<{ column: SortKey }> = ({ column }) => {
    if (sortKey !== column) return <span className="text-gray-300 ml-1">↕</span>;
    return <span className="ml-1">{sortDir === "asc" ? "↑" : "↓"}</span>;
  };

  return (
    <div className={`card ${className}`}>
      <div className="card-header">
        <h4 className="text-lg font-semibold">Nearby Objects</h4>
      </div>

      <div className="card-body">
        {/* Search Controls */}
        <div className="flex items-center gap-3 mb-4">
          <label className="text-sm text-gray-600 whitespace-nowrap">Search within</label>
          <input
            type="number"
            value={radius}
            onChange={(e) => setRadius(Math.min(Number(e.target.value), maxRadius))}
            min={0.1}
            max={maxRadius}
            step={0.5}
            className="form-control w-20"
          />
          <span className="text-sm text-gray-600">arcmin</span>
          <button onClick={performSearch} disabled={isLoading} className="btn btn-primary btn-sm">
            {isLoading ? (
              <span className="flex items-center gap-1">
                <span className="w-3 h-3 border-2 border-white border-t-transparent rounded-full animate-spin" />
                Searching...
              </span>
            ) : (
              "Search"
            )}
          </button>
        </div>

        {/* Error Display */}
        {error && (
          <div className="alert alert-danger mb-4">
            <p>{error}</p>
          </div>
        )}

        {/* Results Table */}
        {isLoading ? (
          <div className="flex items-center justify-center py-8">
            <div className="w-8 h-8 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
            <span className="ml-2 text-gray-500">Searching databases...</span>
          </div>
        ) : results.length === 0 ? (
          <div className="text-center py-8 text-gray-500">
            <svg
              className="w-12 h-12 mx-auto mb-2 text-gray-300"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
              />
            </svg>
            <p>No nearby objects found within {radius} arcmin</p>
          </div>
        ) : (
          <div className="overflow-x-auto max-h-80 overflow-y-auto">
            <table className="table table-compact">
              <thead className="sticky top-0">
                <tr>
                  <th
                    onClick={() => handleSort("name")}
                    className="cursor-pointer hover:bg-opacity-80"
                  >
                    Name <SortArrow column="name" />
                  </th>
                  <th
                    onClick={() => handleSort("database")}
                    className="cursor-pointer hover:bg-opacity-80"
                  >
                    Database <SortArrow column="database" />
                  </th>
                  <th className="text-center">RA</th>
                  <th className="text-center">Dec</th>
                  <th
                    onClick={() => handleSort("separation")}
                    className="cursor-pointer hover:bg-opacity-80 text-right"
                  >
                    Sep (″) <SortArrow column="separation" />
                  </th>
                </tr>
              </thead>
              <tbody>
                {sortedResults.map((obj, idx) => {
                  const url = getDatabaseUrl(obj);
                  return (
                    <tr key={`${obj.database}-${obj.name}-${idx}`}>
                      <td>
                        {url ? (
                          <a href={url} target="_blank" rel="noreferrer" className="link">
                            {obj.name}
                          </a>
                        ) : (
                          obj.name
                        )}
                        {obj.type && (
                          <span className="text-xs text-gray-500 ml-1">({obj.type})</span>
                        )}
                      </td>
                      <td>
                        <span className={`badge ${getDatabaseColor(obj.database)}`}>
                          {obj.database}
                        </span>
                      </td>
                      <td className="text-center font-mono text-xs">{obj.ra}</td>
                      <td className="text-center font-mono text-xs">{obj.dec}</td>
                      <td className="text-right font-mono">{obj.separation.toFixed(2)}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}

        {/* Results Summary */}
        {results.length > 0 && (
          <div className="mt-3 text-xs text-gray-500 flex justify-between">
            <span>
              {results.length} object{results.length !== 1 ? "s" : ""} found
            </span>
            <span>
              SIMBAD: {results.filter((r) => r.database === "SIMBAD").length} | NED:{" "}
              {results.filter((r) => r.database === "NED").length} | ATNF:{" "}
              {results.filter((r) => r.database === "ATNF").length} | Local:{" "}
              {results.filter((r) => r.database === "Local").length}
            </span>
          </div>
        )}
      </div>
    </div>
  );
};

export default NearbyObjectsPanel;
