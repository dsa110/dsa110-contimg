/**
 * Jupyter Integration API
 *
 * Provides hooks for:
 * - Managing Jupyter notebooks
 * - Managing Jupyter kernels
 * - Launching notebooks for sources/images
 * - Kernel status monitoring
 */

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import apiClient from "./client";

// Types
export interface JupyterKernel {
  id: string;
  name: string;
  display_name: string;
  language: string;
  status: "idle" | "busy" | "starting" | "error" | "dead";
  last_activity: string;
  execution_count: number;
  connections: number;
}

export interface JupyterNotebook {
  id: string;
  name: string;
  path: string;
  type: "notebook" | "file" | "directory";
  created: string;
  last_modified: string;
  size?: number;
  kernel_id?: string;
  content_type?: string;
}

export interface JupyterSession {
  id: string;
  notebook: {
    name: string;
    path: string;
  };
  kernel: JupyterKernel;
  created: string;
}

export interface NotebookTemplate {
  id: string;
  name: string;
  description: string;
  category:
    | "source_analysis"
    | "image_inspection"
    | "data_exploration"
    | "custom";
  parameters: Array<{
    name: string;
    type: "string" | "number" | "boolean" | "source_id" | "image_id";
    required: boolean;
    description: string;
  }>;
}

export interface LaunchNotebookRequest {
  template_id: string;
  name: string;
  parameters: Record<string, string | number | boolean>;
  kernel_name?: string;
}

export interface JupyterStats {
  total_notebooks: number;
  active_kernels: number;
  total_sessions: number;
  kernel_usage: {
    python3: number;
    julia?: number;
    r?: number;
  };
  disk_usage_mb: number;
  max_disk_mb: number;
}

// Query keys
const jupyterKeys = {
  all: ["jupyter"] as const,
  kernels: () => [...jupyterKeys.all, "kernels"] as const,
  kernel: (id: string) => [...jupyterKeys.kernels(), id] as const,
  notebooks: () => [...jupyterKeys.all, "notebooks"] as const,
  notebook: (id: string) => [...jupyterKeys.notebooks(), id] as const,
  sessions: () => [...jupyterKeys.all, "sessions"] as const,
  session: (id: string) => [...jupyterKeys.sessions(), id] as const,
  templates: () => [...jupyterKeys.all, "templates"] as const,
  stats: () => [...jupyterKeys.all, "stats"] as const,
};

// Kernels API
export function useKernels() {
  return useQuery({
    queryKey: jupyterKeys.kernels(),
    queryFn: async (): Promise<JupyterKernel[]> => {
      const response = await apiClient.get("/jupyter/kernels");
      return response.data;
    },
  });
}

export function useKernel(id: string) {
  return useQuery({
    queryKey: jupyterKeys.kernel(id),
    queryFn: async (): Promise<JupyterKernel> => {
      const response = await apiClient.get(`/jupyter/kernels/${id}`);
      return response.data;
    },
    enabled: !!id,
    refetchInterval: 5000, // Poll for status updates
  });
}

export function useStartKernel() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (kernelName: string): Promise<JupyterKernel> => {
      const response = await apiClient.post("/jupyter/kernels", {
        name: kernelName,
      });
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: jupyterKeys.kernels() });
      queryClient.invalidateQueries({ queryKey: jupyterKeys.stats() });
    },
  });
}

export function useRestartKernel() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (kernelId: string): Promise<void> => {
      await apiClient.post(`/jupyter/kernels/${kernelId}/restart`);
    },
    onSuccess: (_data, kernelId) => {
      queryClient.invalidateQueries({ queryKey: jupyterKeys.kernel(kernelId) });
      queryClient.invalidateQueries({ queryKey: jupyterKeys.kernels() });
    },
  });
}

export function useInterruptKernel() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (kernelId: string): Promise<void> => {
      await apiClient.post(`/jupyter/kernels/${kernelId}/interrupt`);
    },
    onSuccess: (_data, kernelId) => {
      queryClient.invalidateQueries({ queryKey: jupyterKeys.kernel(kernelId) });
    },
  });
}

export function useShutdownKernel() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (kernelId: string): Promise<void> => {
      await apiClient.delete(`/jupyter/kernels/${kernelId}`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: jupyterKeys.kernels() });
      queryClient.invalidateQueries({ queryKey: jupyterKeys.sessions() });
      queryClient.invalidateQueries({ queryKey: jupyterKeys.stats() });
    },
  });
}

// Notebooks API
export function useNotebooks(path?: string) {
  return useQuery({
    queryKey: [...jupyterKeys.notebooks(), path || "root"],
    queryFn: async (): Promise<JupyterNotebook[]> => {
      const params = path ? { path } : {};
      const response = await apiClient.get("/jupyter/notebooks", { params });
      return response.data;
    },
  });
}

export function useNotebook(id: string) {
  return useQuery({
    queryKey: jupyterKeys.notebook(id),
    queryFn: async (): Promise<JupyterNotebook> => {
      const response = await apiClient.get(`/jupyter/notebooks/${id}`);
      return response.data;
    },
    enabled: !!id,
  });
}

export function useDeleteNotebook() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (notebookId: string): Promise<void> => {
      await apiClient.delete(`/jupyter/notebooks/${notebookId}`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: jupyterKeys.notebooks() });
      queryClient.invalidateQueries({ queryKey: jupyterKeys.stats() });
    },
  });
}

// Sessions API
export function useSessions() {
  return useQuery({
    queryKey: jupyterKeys.sessions(),
    queryFn: async (): Promise<JupyterSession[]> => {
      const response = await apiClient.get("/jupyter/sessions");
      return response.data;
    },
    refetchInterval: 10000,
  });
}

export function useCreateSession() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (notebookPath: string): Promise<JupyterSession> => {
      const response = await apiClient.post("/jupyter/sessions", {
        notebook_path: notebookPath,
      });
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: jupyterKeys.sessions() });
      queryClient.invalidateQueries({ queryKey: jupyterKeys.kernels() });
      queryClient.invalidateQueries({ queryKey: jupyterKeys.stats() });
    },
  });
}

export function useDeleteSession() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (sessionId: string): Promise<void> => {
      await apiClient.delete(`/jupyter/sessions/${sessionId}`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: jupyterKeys.sessions() });
      queryClient.invalidateQueries({ queryKey: jupyterKeys.kernels() });
      queryClient.invalidateQueries({ queryKey: jupyterKeys.stats() });
    },
  });
}

// Templates API
export function useNotebookTemplates() {
  return useQuery({
    queryKey: jupyterKeys.templates(),
    queryFn: async (): Promise<NotebookTemplate[]> => {
      const response = await apiClient.get("/jupyter/templates");
      return response.data;
    },
  });
}

export function useLaunchNotebook() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (
      request: LaunchNotebookRequest
    ): Promise<{ notebook: JupyterNotebook; session: JupyterSession }> => {
      const response = await apiClient.post("/jupyter/launch", request);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: jupyterKeys.notebooks() });
      queryClient.invalidateQueries({ queryKey: jupyterKeys.sessions() });
      queryClient.invalidateQueries({ queryKey: jupyterKeys.kernels() });
      queryClient.invalidateQueries({ queryKey: jupyterKeys.stats() });
    },
  });
}

// Stats API
export function useJupyterStats() {
  return useQuery({
    queryKey: jupyterKeys.stats(),
    queryFn: async (): Promise<JupyterStats> => {
      const response = await apiClient.get("/jupyter/stats");
      return response.data;
    },
    refetchInterval: 30000,
  });
}

// Jupyter server URL for opening notebooks
export function useJupyterUrl(notebookPath?: string) {
  return useQuery({
    queryKey: [...jupyterKeys.all, "url", notebookPath],
    queryFn: async (): Promise<string> => {
      const response = await apiClient.get("/jupyter/url", {
        params: notebookPath ? { path: notebookPath } : {},
      });
      return response.data.url;
    },
  });
}
