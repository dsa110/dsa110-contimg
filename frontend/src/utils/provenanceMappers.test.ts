import {
  mapProvenanceFromImageDetail,
  mapProvenanceFromMSDetail,
  mapProvenanceFromSourceDetail,
  ImageDetailResponse,
  MSDetailResponse,
  SourceDetailResponse,
} from "./provenanceMappers";

describe("provenanceMappers", () => {
  describe("mapProvenanceFromImageDetail", () => {
    it("maps all fields correctly", () => {
      const image: ImageDetailResponse = {
        id: "img-123",
        path: "/data/images/img-123.fits",
        ms_path: "/data/ms/test.ms",
        cal_table: "/data/cal/cal_table.tbl",
        pointing_ra_deg: 123.456,
        pointing_dec_deg: -45.678,
        qa_grade: "good",
        qa_summary: "RMS 0.35 mJy, DR 1200",
        run_id: "job-456",
        created_at: "2025-01-15T10:30:00Z",
      };

      const result = mapProvenanceFromImageDetail(image);

      expect(result.runId).toBe("job-456");
      expect(result.msPath).toBe("/data/ms/test.ms");
      expect(result.calTable).toBe("/data/cal/cal_table.tbl");
      expect(result.pointingRaDeg).toBe(123.456);
      expect(result.pointingDecDeg).toBe(-45.678);
      expect(result.qaGrade).toBe("good");
      expect(result.qaSummary).toBe("RMS 0.35 mJy, DR 1200");
      expect(result.logsUrl).toBe("/logs/job-456");
      expect(result.qaUrl).toBe("/qa/image/img-123");
      expect(result.msUrl).toBe("/ms/%2Fdata%2Fms%2Ftest.ms");
      expect(result.imageUrl).toBe("/images/img-123");
      expect(result.createdAt).toBe("2025-01-15T10:30:00Z");
    });

    it("handles missing optional fields gracefully", () => {
      const image: ImageDetailResponse = {
        id: "img-minimal",
        path: "/data/images/minimal.fits",
      };

      const result = mapProvenanceFromImageDetail(image);

      expect(result.runId).toBeUndefined();
      expect(result.msPath).toBeUndefined();
      expect(result.calTable).toBeUndefined();
      expect(result.logsUrl).toBeUndefined();
      expect(result.msUrl).toBeUndefined();
      expect(result.imageUrl).toBe("/images/img-minimal");
    });
  });

  describe("mapProvenanceFromMSDetail", () => {
    it("maps all fields and extracts first calibrator", () => {
      const ms: MSDetailResponse = {
        path: "/data/ms/test.ms",
        pointing_ra_deg: 100.0,
        pointing_dec_deg: 30.0,
        calibrator_matches: [
          { cal_table: "/data/cal/primary.tbl", type: "flux" },
          { cal_table: "/data/cal/phase.tbl", type: "phase" },
        ],
        qa_grade: "warn",
        qa_summary: "High RFI",
        run_id: "job-789",
        created_at: "2025-01-16T08:00:00Z",
      };

      const result = mapProvenanceFromMSDetail(ms);

      expect(result.msPath).toBe("/data/ms/test.ms");
      expect(result.calTable).toBe("/data/cal/primary.tbl");
      expect(result.pointingRaDeg).toBe(100.0);
      expect(result.pointingDecDeg).toBe(30.0);
      expect(result.qaGrade).toBe("warn");
      expect(result.logsUrl).toBe("/logs/job-789");
    });

    it("handles missing calibrator_matches", () => {
      const ms: MSDetailResponse = {
        path: "/data/ms/nocal.ms",
      };

      const result = mapProvenanceFromMSDetail(ms);

      expect(result.calTable).toBeUndefined();
    });
  });

  describe("mapProvenanceFromSourceDetail", () => {
    it("uses first contributing image by default", () => {
      const source: SourceDetailResponse = {
        id: "src-001",
        name: "Test Source",
        ra_deg: 180.0,
        dec_deg: -30.0,
        contributing_images: [
          {
            image_id: "img-a",
            path: "/data/images/a.fits",
            ms_path: "/data/ms/a.ms",
            qa_grade: "good",
            created_at: "2025-01-17T12:00:00Z",
          },
          {
            image_id: "img-b",
            path: "/data/images/b.fits",
            qa_grade: "fail",
          },
        ],
      };

      const result = mapProvenanceFromSourceDetail(source);

      expect(result).not.toBeNull();
      expect(result!.imageUrl).toBe("/images/img-a");
      expect(result!.msPath).toBe("/data/ms/a.ms");
      expect(result!.qaGrade).toBe("good");
    });

    it("uses selected image when provided", () => {
      const source: SourceDetailResponse = {
        id: "src-001",
        ra_deg: 180.0,
        dec_deg: -30.0,
        contributing_images: [
          { image_id: "img-a", path: "/a.fits", qa_grade: "good" },
          { image_id: "img-b", path: "/b.fits", qa_grade: "fail" },
        ],
      };

      const result = mapProvenanceFromSourceDetail(source, "img-b");

      expect(result).not.toBeNull();
      expect(result!.imageUrl).toBe("/images/img-b");
      expect(result!.qaGrade).toBe("fail");
    });

    it("returns null when no contributing images", () => {
      const source: SourceDetailResponse = {
        id: "src-empty",
        ra_deg: 0,
        dec_deg: 0,
        contributing_images: [],
      };

      const result = mapProvenanceFromSourceDetail(source);

      expect(result).toBeNull();
    });
  });
});
