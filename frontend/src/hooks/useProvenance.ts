import { useCallback, useEffect, useState } from "react";
import { fetchProvenanceData } from "../api/client";
import { ProvenanceStripProps } from "../types/provenance";

interface UseProvenanceOptions {
  /** Skip fetching if data is already available */
  skip?: boolean;
}

interface UseProvenanceResult {
  provenance: ProvenanceStripProps | null;
  loading: boolean;
  error: string | null;
  refetch: () => void;
}

/**
 * Hook to fetch provenance data for a pipeline run.
 *
 * @param runId - The pipeline run/job ID to fetch provenance for
 * @param options - Optional configuration
 * @returns Provenance data, loading state, error, and refetch function
 *
 * @example
 * // Basic usage
 * const { provenance, loading, error } = useProvenance(runId);
 *
 * @example
 * // Skip fetching if you already have the data
 * const { provenance } = useProvenance(runId, { skip: !runId });
 */
const useProvenance = (runId?: string, options: UseProvenanceOptions = {}): UseProvenanceResult => {
  const { skip = false } = options;
  const [provenance, setProvenance] = useState<ProvenanceStripProps | null>(null);
  const [loading, setLoading] = useState<boolean>(!skip && !!runId);
  const [error, setError] = useState<string | null>(null);

  const fetchData = useCallback(async () => {
    if (!runId) {
      setError("Run ID is required to fetch provenance data.");
      setLoading(false);
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const data = await fetchProvenanceData(runId);
      setProvenance(data);
    } catch (err) {
      const message = err instanceof Error ? err.message : "Failed to fetch provenance data.";
      setError(message);
    } finally {
      setLoading(false);
    }
  }, [runId]);

  useEffect(() => {
    if (skip || !runId) {
      setLoading(false);
      return;
    }

    fetchData();
  }, [runId, skip, fetchData]);

  const refetch = () => {
    if (runId && !skip) {
      fetchData();
    }
  };

  return { provenance, loading, error, refetch };
};

export default useProvenance;
