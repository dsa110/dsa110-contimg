/**
 * Tests for useCalibrationComparison hook
 */

import React from "react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import {
  useCalibrationQA,
  useCalibrationComparison,
  useRecentCalibrations,
  calibrationComparisonKeys,
  calculateComparisonDeltas,
  isCalibrationImproved,
} from "./useCalibrationComparison";
import type { CalibrationQAMetrics } from "../types/calibration";

// Mock the API client
vi.mock("../api/client", () => ({
  default: {
    get: vi.fn(),
  },
}));

import apiClient from "../api/client";

const mockApiClient = vi.mocked(apiClient, true);

// Helper to create a wrapper with QueryClientProvider
const createWrapper = () => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
      },
    },
  });
  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
};

// Mock calibration QA metrics
const mockQAMetrics: CalibrationQAMetrics = {
  cal_set_name: "test_cal_set",
  calibrator_name: "3C286",
  cal_mjd: 60000,
  cal_timestamp: "2023-01-01T00:00:00Z",
  snr: 50,
  flagging_percent: 5,
  phase_rms_deg: 10,
  amp_rms: 0.05,
  quality_grade: "good",
  quality_score: 80,
  issues: [],
  recommendations: [],
};

const mockReferenceMetrics: CalibrationQAMetrics = {
  ...mockQAMetrics,
  cal_set_name: "reference_cal_set",
  snr: 40,
  flagging_percent: 8,
  phase_rms_deg: 15,
  amp_rms: 0.08,
  quality_grade: "acceptable",
  quality_score: 70,
};

describe("useCalibrationComparison", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe("calibrationComparisonKeys", () => {
    it("generates correct query keys", () => {
      expect(calibrationComparisonKeys.all).toEqual(["calibration-comparison"]);
      expect(calibrationComparisonKeys.qa("/path/to/cal")).toEqual([
        "calibration-comparison",
        "qa",
        "/path/to/cal",
      ]);
      expect(calibrationComparisonKeys.compare("/path/a", "/path/b")).toEqual([
        "calibration-comparison",
        "compare",
        "/path/a",
        "/path/b",
      ]);
      expect(calibrationComparisonKeys.recent("3C286", 10)).toEqual([
        "calibration-comparison",
        "recent",
        "3C286",
        { limit: 10 },
      ]);
    });
  });

  describe("useCalibrationQA", () => {
    it("fetches calibration QA metrics", async () => {
      mockApiClient.get.mockResolvedValueOnce({ data: mockQAMetrics });

      const { result } = renderHook(() => useCalibrationQA("/path/to/cal"), {
        wrapper: createWrapper(),
      });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));

      expect(result.current.data).toEqual(mockQAMetrics);
      expect(mockApiClient.get).toHaveBeenCalledWith(
        "/v1/health/calibration/qa/%2Fpath%2Fto%2Fcal"
      );
    });

    it("does not fetch when path is empty", () => {
      renderHook(() => useCalibrationQA(""), {
        wrapper: createWrapper(),
      });

      expect(mockApiClient.get).not.toHaveBeenCalled();
    });

    it("does not fetch when disabled", () => {
      renderHook(() => useCalibrationQA("/path/to/cal", false), {
        wrapper: createWrapper(),
      });

      expect(mockApiClient.get).not.toHaveBeenCalled();
    });
  });

  describe("useCalibrationComparison", () => {
    it("fetches comparison data for two paths", async () => {
      mockApiClient.get.mockResolvedValueOnce({
        data: {
          current: mockQAMetrics,
          reference: mockReferenceMetrics,
        },
      });

      const { result } = renderHook(
        () => useCalibrationComparison("/path/a", "/path/b"),
        { wrapper: createWrapper() }
      );

      await waitFor(() => expect(result.current.isSuccess).toBe(true));

      expect(result.current.data?.current).toEqual(mockQAMetrics);
      expect(result.current.data?.reference).toEqual(mockReferenceMetrics);
      expect(mockApiClient.get).toHaveBeenCalledWith(
        "/v1/health/calibration/compare",
        {
          params: {
            current_path: "/path/a",
            reference_path: "/path/b",
          },
        }
      );
    });

    it("does not fetch when pathA is empty", () => {
      renderHook(() => useCalibrationComparison("", "/path/b"), {
        wrapper: createWrapper(),
      });

      expect(mockApiClient.get).not.toHaveBeenCalled();
    });

    it("does not fetch when pathB is empty", () => {
      renderHook(() => useCalibrationComparison("/path/a", ""), {
        wrapper: createWrapper(),
      });

      expect(mockApiClient.get).not.toHaveBeenCalled();
    });
  });

  describe("useRecentCalibrations", () => {
    it("fetches recent calibrations for a calibrator", async () => {
      const mockRecentList = [mockQAMetrics, mockReferenceMetrics];
      mockApiClient.get.mockResolvedValueOnce({ data: mockRecentList });

      const { result } = renderHook(() => useRecentCalibrations("3C286", 5), {
        wrapper: createWrapper(),
      });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));

      expect(result.current.data).toEqual(mockRecentList);
      expect(mockApiClient.get).toHaveBeenCalledWith(
        "/v1/health/calibration/recent/3C286",
        { params: { limit: 5 } }
      );
    });

    it("does not fetch when calibrator name is empty", () => {
      renderHook(() => useRecentCalibrations(""), {
        wrapper: createWrapper(),
      });

      expect(mockApiClient.get).not.toHaveBeenCalled();
    });
  });

  describe("calculateComparisonDeltas", () => {
    it("calculates positive deltas when current is better", () => {
      const deltas = calculateComparisonDeltas(
        mockQAMetrics,
        mockReferenceMetrics
      );

      expect(deltas).toBeDefined();
      // SNR improved: 50 - 40 = 10
      expect(deltas!.snr).toBe(10);
      // SNR percent: (50-40)/40 * 100 = 25%
      expect(deltas!.snrPercent).toBe(25);
      // Flagging improved (lower): -(5-8) = 3
      expect(deltas!.flagging).toBe(3);
      // Phase RMS improved (lower): -(10-15) = 5
      expect(deltas!.phaseRms).toBe(5);
      // Amp RMS improved (lower): -(0.05-0.08) = 0.03
      expect(deltas!.ampRms).toBeCloseTo(0.03);
      // Quality score improved: 80 - 70 = 10
      expect(deltas!.qualityScore).toBe(10);
    });

    it("calculates negative deltas when reference is better", () => {
      const deltas = calculateComparisonDeltas(
        mockReferenceMetrics,
        mockQAMetrics
      );

      expect(deltas!.snr).toBe(-10);
      expect(deltas!.qualityScore).toBe(-10);
    });

    it("handles zero reference SNR", () => {
      const zeroSnr = { ...mockReferenceMetrics, snr: 0 };
      const deltas = calculateComparisonDeltas(mockQAMetrics, zeroSnr);

      expect(deltas!.snrPercent).toBe(0);
    });
  });

  describe("isCalibrationImproved", () => {
    it("returns true when current has higher quality score", () => {
      expect(isCalibrationImproved(mockQAMetrics, mockReferenceMetrics)).toBe(
        true
      );
    });

    it("returns false when reference has higher quality score", () => {
      expect(isCalibrationImproved(mockReferenceMetrics, mockQAMetrics)).toBe(
        false
      );
    });

    it("returns false when scores are equal", () => {
      const equal = { ...mockReferenceMetrics, quality_score: 80 };
      expect(isCalibrationImproved(mockQAMetrics, equal)).toBe(false);
    });
  });
});
