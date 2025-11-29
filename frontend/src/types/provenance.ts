export interface ProvenanceStripProps {
  runId?: string; // job/pipeline execution id
  msPath?: string;
  calTable?: string;
  calUrl?: string; // calibration table detail link
  pointingDecDeg?: number | null;
  pointingRaDeg?: number | null;
  qaGrade?: "good" | "warn" | "fail" | null;
  qaSummary?: string; // e.g., "RMS 0.35 mJy, DR 1200"
  logsUrl?: string; // deep link to job logs
  qaUrl?: string; // QA report link
  msUrl?: string; // MS detail link
  imageUrl?: string; // image detail link
  createdAt?: string; // ISO
}
