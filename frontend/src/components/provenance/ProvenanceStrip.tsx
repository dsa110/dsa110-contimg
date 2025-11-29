import React from "react";
import { formatRA, formatDec } from "../../utils/coordinateFormatter";
import { relativeTime } from "../../utils/relativeTime";
import { ProvenanceStripProps } from "./types";
import ProvenanceBadge from "./ProvenanceBadge";
import ProvenanceLink from "./ProvenanceLink";

const ProvenanceStrip: React.FC<ProvenanceStripProps> = ({
  runId,
  msPath,
  calTable,
  calUrl,
  pointingDecDeg,
  pointingRaDeg,
  qaGrade,
  qaSummary,
  logsUrl,
  qaUrl,
  msUrl,
  imageUrl,
  createdAt,
}) => {
  const renderLink = (label: string, value: string, url?: string) => (
    <span className="provenance-item">
      <strong>{label}</strong>{" "}
      {url ? (
        <a href={url} target="_blank" rel="noreferrer">
          {value}
        </a>
      ) : (
        value
      )}
    </span>
  );

  const safeBasename = (value?: string) => (value ? value.split("/").pop() || value : undefined);

  const hasPointing = pointingRaDeg !== undefined || pointingDecDeg !== undefined;
  const pointingRa =
    pointingRaDeg !== undefined && pointingRaDeg !== null ? formatRA(pointingRaDeg) : "unknown";
  const pointingDec =
    pointingDecDeg !== undefined && pointingDecDeg !== null ? formatDec(pointingDecDeg) : "unknown";

  return (
    <div
      className="provenance-strip"
      style={{
        display: "flex",
        gap: "12px",
        flexWrap: "wrap",
        alignItems: "center",
        fontSize: "0.95rem",
      }}
    >
      {runId && renderLink("Run:", runId, logsUrl)}
      {msPath && renderLink("MS:", safeBasename(msPath) as string, msUrl)}
      {calTable && renderLink("Cal:", safeBasename(calTable) as string, calUrl)}
      {imageUrl && renderLink("Image:", safeBasename(imageUrl) as string, imageUrl)}
      {hasPointing && (
        <span className="provenance-item">
          <strong>Pointing:</strong> RA {pointingRa}, Dec {pointingDec}
        </span>
      )}
      {qaGrade && (
        <span
          className="provenance-item"
          style={{ display: "flex", alignItems: "center", gap: "6px" }}
        >
          <strong>QA:</strong> <ProvenanceBadge qaGrade={qaGrade} qaSummary={qaSummary} />
          {qaSummary && <span style={{ color: "#666" }}>{qaSummary}</span>}
          {qaUrl && <ProvenanceLink qaUrl={qaUrl} />}
        </span>
      )}
      {createdAt && (
        <span className="provenance-item">
          <strong>Created:</strong> {relativeTime(createdAt)}
        </span>
      )}
      {/* Optional logs link if not already shown via runId */}
      {!runId && logsUrl && <ProvenanceLink logsUrl={logsUrl} />}
    </div>
  );
};

export default ProvenanceStrip;
