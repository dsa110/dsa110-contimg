/**
 * Alert Policy API
 *
 * CRUD operations, dry-run previews, and silences for alert policies.
 */
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import apiClient from "./client";
import type {
  AlertPolicy,
  AlertPolicyDryRunRequest,
  AlertPolicyDryRunResponse,
  AlertPolicyInput,
  AlertPolicyListResponse,
  AlertSilence,
  CreateSilenceInput,
} from "@/types/alerts";

const BASE_PATH = "/alert-policies";

// =============================================================================
// Query Keys
// =============================================================================

export const alertPolicyKeys = {
  all: ["alert-policies"] as const,
  list: (params?: AlertPolicyListQuery) =>
    [...alertPolicyKeys.all, "list", params] as const,
  detail: (id: string) => [...alertPolicyKeys.all, "detail", id] as const,
  silences: (policyId?: string) =>
    [...alertPolicyKeys.all, "silences", policyId ?? "all"] as const,
  dryRun: () => [...alertPolicyKeys.all, "dry-run"] as const,
};

// =============================================================================
// API Types
// =============================================================================

export interface AlertPolicyListQuery {
  severity?: string;
  enabled?: boolean;
  search?: string;
}

// =============================================================================
// API Functions
// =============================================================================

export async function getAlertPolicies(
  params?: AlertPolicyListQuery
): Promise<AlertPolicyListResponse> {
  const response = await apiClient.get<AlertPolicyListResponse>(BASE_PATH, {
    params,
  });
  return response.data;
}

export async function getAlertPolicy(id: string): Promise<AlertPolicy> {
  const response = await apiClient.get<AlertPolicy>(`${BASE_PATH}/${id}`);
  return response.data;
}

export async function createAlertPolicy(
  input: AlertPolicyInput
): Promise<AlertPolicy> {
  const response = await apiClient.post<AlertPolicy>(BASE_PATH, input);
  return response.data;
}

export async function updateAlertPolicy(
  id: string,
  input: AlertPolicyInput
): Promise<AlertPolicy> {
  const response = await apiClient.put<AlertPolicy>(
    `${BASE_PATH}/${id}`,
    input
  );
  return response.data;
}

export async function deleteAlertPolicy(id: string): Promise<void> {
  await apiClient.delete(`${BASE_PATH}/${id}`);
}

export async function toggleAlertPolicy(
  id: string,
  enabled: boolean
): Promise<AlertPolicy> {
  const response = await apiClient.post<AlertPolicy>(
    `${BASE_PATH}/${id}/toggle`,
    { enabled }
  );
  return response.data;
}

export async function dryRunAlertPolicy(
  payload: AlertPolicyDryRunRequest
): Promise<AlertPolicyDryRunResponse> {
  const response = await apiClient.post<AlertPolicyDryRunResponse>(
    `${BASE_PATH}/dry-run`,
    payload
  );
  return response.data;
}

export async function getAlertSilences(
  policyId?: string
): Promise<AlertSilence[]> {
  const url = policyId
    ? `${BASE_PATH}/${policyId}/silences`
    : `${BASE_PATH}/silences`;
  const response = await apiClient.get<AlertSilence[]>(url);
  return response.data;
}

export async function createAlertSilence(
  policyId: string,
  input: CreateSilenceInput
): Promise<AlertSilence> {
  const response = await apiClient.post<AlertSilence>(
    `${BASE_PATH}/${policyId}/silences`,
    input
  );
  return response.data;
}

// =============================================================================
// React Query Hooks
// =============================================================================

export function useAlertPolicies(params?: AlertPolicyListQuery) {
  return useQuery({
    queryKey: alertPolicyKeys.list(params),
    queryFn: () => getAlertPolicies(params),
    staleTime: 15000,
  });
}

export function useAlertPolicy(id?: string) {
  return useQuery({
    queryKey: alertPolicyKeys.detail(id ?? "unknown"),
    queryFn: () =>
      id ? getAlertPolicy(id) : Promise.reject(new Error("Missing ID")),
    enabled: Boolean(id),
  });
}

export function useCreateAlertPolicy() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: createAlertPolicy,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: alertPolicyKeys.all });
    },
  });
}

export function useUpdateAlertPolicy() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, input }: { id: string; input: AlertPolicyInput }) =>
      updateAlertPolicy(id, input),
    onSuccess: (data) => {
      queryClient.invalidateQueries({
        queryKey: alertPolicyKeys.detail(data.id),
      });
      queryClient.invalidateQueries({ queryKey: alertPolicyKeys.all });
    },
  });
}

export function useDeleteAlertPolicy() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: deleteAlertPolicy,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: alertPolicyKeys.all });
    },
  });
}

export function useToggleAlertPolicy() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, enabled }: { id: string; enabled: boolean }) =>
      toggleAlertPolicy(id, enabled),
    onSuccess: (data) => {
      queryClient.invalidateQueries({
        queryKey: alertPolicyKeys.detail(data.id),
      });
      queryClient.invalidateQueries({ queryKey: alertPolicyKeys.all });
    },
  });
}

export function useAlertPolicyDryRun() {
  return useMutation({
    mutationFn: dryRunAlertPolicy,
  });
}

export function useAlertSilences(policyId?: string) {
  return useQuery({
    queryKey: alertPolicyKeys.silences(policyId),
    queryFn: () => getAlertSilences(policyId),
    enabled: true,
    staleTime: 15000,
  });
}

export function useCreateAlertSilence() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      policyId,
      input,
    }: {
      policyId: string;
      input: CreateSilenceInput;
    }) => createAlertSilence(policyId, input),
    onSuccess: (data) => {
      queryClient.invalidateQueries({
        queryKey: alertPolicyKeys.silences(data.policy_id),
      });
      queryClient.invalidateQueries({ queryKey: alertPolicyKeys.all });
    },
  });
}
