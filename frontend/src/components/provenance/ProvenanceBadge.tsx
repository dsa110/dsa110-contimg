import React from "react";

interface ProvenanceBadgeProps {
  qaGrade?: "good" | "warn" | "fail" | null;
  qaSummary?: string;
}

const ProvenanceBadge: React.FC<ProvenanceBadgeProps> = ({ qaGrade, qaSummary }) => {
  const getBadgeClass = () => {
    switch (qaGrade) {
      case "good":
        return "badge badge-success";
      case "warn":
        return "badge badge-warning";
      case "fail":
        return "badge badge-danger";
      default:
        return "badge badge-secondary";
    }
  };

  return (
    <span className={getBadgeClass()} title={qaSummary || "No QA summary available"}>
      {qaGrade ? qaGrade.charAt(0).toUpperCase() + qaGrade.slice(1) : "Unknown"}
    </span>
  );
};

export default ProvenanceBadge;
