import React from "react";

interface ProvenanceLinkProps {
  logsUrl?: string;
  qaUrl?: string;
}

const ProvenanceLink: React.FC<ProvenanceLinkProps> = ({ logsUrl, qaUrl }) => {
  return (
    <div>
      {logsUrl && (
        <a href={logsUrl} target="_blank" rel="noopener noreferrer">
          View Logs
        </a>
      )}
      {qaUrl && (
        <a href={qaUrl} target="_blank" rel="noopener noreferrer">
          QA Report
        </a>
      )}
    </div>
  );
};

export default ProvenanceLink;
