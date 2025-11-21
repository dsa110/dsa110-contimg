import React, { useState, useEffect } from "react";
import ServiceStatus from "./ServiceStatus";

const Dashboard = () => {
  const [error, setError] = useState(null);

  useEffect(() => {
    // ...existing code...
  }, []);

  return (
    <div className="dashboard">
      <ServiceStatus />
      {error && (
        <div className="error-banner">
          <strong>Error:</strong> {error}
          <button onClick={() => setError(null)}>✕</button>
        </div>
      )}
      {/* ...existing code... */}
    </div>
  );
};

export default Dashboard;
