/**
 * Retention Policy API helpers.
 *
 * These helpers wrap the backend retention endpoints so the
 * Zustand store and React components can persist policies
 * and trigger simulations/executions against the real service.
 */

import apiClient from "./client";
import type {
  RetentionPolicy,
  RetentionPolicyFormData,
  RetentionSimulation,
  RetentionExecution,
} from "../types/retention";

const BASE_PATH = "/retention";

/**
 * Fetch all retention policies.
 */
export async function listRetentionPolicies(): Promise<RetentionPolicy[]> {
  const response = await apiClient.get<RetentionPolicy[]>(
    `${BASE_PATH}/policies`
  );
  return response.data;
}

/**
 * Create a new retention policy.
 */
export async function createRetentionPolicy(
  payload: RetentionPolicyFormData
): Promise<RetentionPolicy> {
  const response = await apiClient.post<RetentionPolicy>(
    `${BASE_PATH}/policies`,
    payload
  );
  return response.data;
}

/**
 * Update an existing policy.
 */
export async function updateRetentionPolicy(
  policyId: string,
  payload: Partial<RetentionPolicyFormData>
): Promise<RetentionPolicy> {
  const response = await apiClient.put<RetentionPolicy>(
    `${BASE_PATH}/policies/${encodeURIComponent(policyId)}`,
    payload
  );
  return response.data;
}

/**
 * Delete a policy.
 */
export async function deleteRetentionPolicy(policyId: string): Promise<void> {
  await apiClient.delete(`${BASE_PATH}/policies/${encodeURIComponent(policyId)}`);
}

/**
 * Request a simulation for the specified policy.
 */
export async function simulateRetentionPolicy(
  policyId: string
): Promise<RetentionSimulation> {
  const response = await apiClient.post<RetentionSimulation>(
    `${BASE_PATH}/policies/${encodeURIComponent(policyId)}/simulate`
  );
  return response.data;
}

/**
 * Execute the specified policy.
 */
export async function executeRetentionPolicy(
  policyId: string
): Promise<RetentionExecution> {
  const response = await apiClient.post<RetentionExecution>(
    `${BASE_PATH}/policies/${encodeURIComponent(policyId)}/execute`
  );
  return response.data;
}

/**
 * Fetch execution history. When policyId is provided the backend should
 * filter by policy, otherwise it returns the most recent executions overall.
 */
export async function listRetentionExecutions(
  policyId?: string
): Promise<RetentionExecution[]> {
  const response = await apiClient.get<RetentionExecution[]>(
    `${BASE_PATH}/executions`,
    { params: policyId ? { policy_id: policyId } : undefined }
  );
  return response.data;
}
