export const DASHBOARD_CONFIG = {
  refreshIntervals: {
    pipelineStatus: 10000,
    systemMetrics: 10000,
    healthSummary: 10000,
    recentObservations: 10000,
  },
  thresholds: {
    cpu: { warning: 50, critical: 70 },
    memory: { warning: 60, critical: 80 },
    disk: { warning: 75, critical: 90 },
    load: { warning: 5, critical: 10 },
    queueDepth: { warning: 30, critical: 50 },
  },
};
