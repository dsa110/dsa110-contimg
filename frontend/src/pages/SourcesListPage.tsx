import React from "react";
import { Link } from "react-router-dom";
import { useSources } from "../hooks/useQueries";

/**
 * List page showing all detected sources.
 */
const SourcesListPage: React.FC = () => {
  const { data: sources, isLoading, error } = useSources();

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="text-gray-500">Loading sources...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg">
        Failed to load sources: {error.message}
      </div>
    );
  }

  return (
    <div className="max-w-6xl mx-auto">
      <h1 className="text-2xl font-bold text-gray-900 mb-6">Sources</h1>

      {sources && sources.length > 0 ? (
        <div className="card overflow-hidden">
          <table className="table">
            <thead>
              <tr>
                <th>ID</th>
                <th>Name</th>
                <th className="text-right">RA (deg)</th>
                <th className="text-right">Dec (deg)</th>
                <th className="text-center">Images</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200">
              {sources.map((source) => (
                <tr key={source.id}>
                  <td>
                    <Link
                      to={`/sources/${source.id}`}
                      className="text-blue-600 hover:text-blue-800 font-medium"
                    >
                      {source.id}
                    </Link>
                  </td>
                  <td>{source.name || "—"}</td>
                  <td className="text-right font-mono">{source.ra_deg?.toFixed(4)}</td>
                  <td className="text-right font-mono">{source.dec_deg?.toFixed(4)}</td>
                  <td className="text-center">{source.num_images ?? "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <p className="text-gray-500">No sources found.</p>
      )}
    </div>
  );
};

export default SourcesListPage;
