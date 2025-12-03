/**
 * Image-specific API helpers.
 */

import apiClient from "./client";
import type { Region, RegionFormat } from "../types/regions";

export interface SaveImageRegionsRequest {
  format: RegionFormat;
  regions: Region[];
}

export interface SaveImageRegionsResponse {
  saved: number;
  updated_at: string;
}

/**
 * Persist drawn regions for an image.
 */
export async function saveImageRegions(
  imageId: string,
  payload: SaveImageRegionsRequest
): Promise<SaveImageRegionsResponse> {
  const response = await apiClient.post<SaveImageRegionsResponse>(
    `/v1/images/${encodeURIComponent(imageId)}/regions`,
    payload
  );
  return response.data;
}
