import { useEffect, useState } from "react";
import { fetchProvenanceData } from "../api/client";
import { ProvenanceStripProps } from "../types/provenance";

const useProvenance = (runId?: string) => {
  const [provenance, setProvenance] = useState<ProvenanceStripProps | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const getProvenanceData = async () => {
      if (!runId) {
        setError("Run ID is required to fetch provenance data.");
        setLoading(false);
        return;
      }

      try {
        const data = await fetchProvenanceData(runId);
        setProvenance(data);
      } catch (err) {
        setError("Failed to fetch provenance data.");
      } finally {
        setLoading(false);
      }
    };

    getProvenanceData();
  }, [runId]);

  return { provenance, loading, error };
};

export default useProvenance;
