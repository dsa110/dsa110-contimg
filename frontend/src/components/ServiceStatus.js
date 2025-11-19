import React, { useState, useEffect } from "react";
import "./ServiceStatus.css";

const ServiceStatus = () => {
  const [services, setServices] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    checkServices();
    const interval = setInterval(checkServices, 30000); // Check every 30s
    return () => clearInterval(interval);
  }, []);

  const checkServices = async () => {
    try {
      const response = await fetch("/api/health/services");
      const data = await response.json();
      setServices(data);
    } catch (error) {
      console.error("Failed to check services:", error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) return null;

  return (
    <div className="service-status">
      {services &&
        Object.entries(services).map(([name, service]) => (
          <div key={name} className={`service-indicator ${service.status}`}>
            <span className="service-name">{name}</span>
            <span className={`status-dot ${service.status}`}></span>
            {service.error && (
              <span className="service-error" title={service.error}>
                ⚠
              </span>
            )}
          </div>
        ))}
    </div>
  );
};

export default ServiceStatus;
