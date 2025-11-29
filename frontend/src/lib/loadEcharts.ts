let echartsPromise: Promise<typeof import("echarts")> | null = null;

/**
 * Dynamically load ECharts to keep it out of the main bundle.
 */
export const loadEcharts = async (): Promise<typeof import("echarts")> => {
  if (!echartsPromise) {
    echartsPromise = import("echarts");
  }
  return echartsPromise;
};
