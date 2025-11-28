import axios, { AxiosError } from "axios";
import type { ProvenanceStripProps } from "../types/provenance";
import type { ErrorResponse } from "../types/errors";

const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_URL || "http://127.0.0.1:8000/api",
  timeout: 10000,
});

/**
 * Response interceptor to normalize error responses.
 * Converts axios errors into the standard ErrorResponse shape.
 */
apiClient.interceptors.response.use(
  (response) => response,
  (error: AxiosError<ErrorResponse>) => {
    // Normalize error for downstream handlers
    const normalized: Partial<ErrorResponse> = error.response?.data ?? {
      code: "NETWORK_ERROR",
      http_status: error.response?.status ?? 0,
      user_message: "Unable to reach the server",
      action: "Check your connection and try again",
      ref_id: "",
    };
    return Promise.reject(normalized);
  }
);

/**
 * Fetch provenance data for a given run/job ID.
 * Used by the ProvenanceStrip component to display pipeline context.
 */
export const fetchProvenanceData = async (runId: string): Promise<ProvenanceStripProps> => {
  const response = await apiClient.get<ProvenanceStripProps>(`/jobs/${runId}/provenance`);
  return response.data;
};

export default apiClient;
