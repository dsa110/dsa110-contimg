import React, { useEffect, useRef, useMemo, useState } from "react";
import { loadEcharts } from "../../lib/loadEcharts";

export interface RatingStat {
  label: string;
  trueCount: number;
  falseCount: number;
  unsureCount: number;
  total?: number;
}

export interface RatingDistribution {
  tag: string;
  count: number;
  percentage: number;
}

export interface StatsDashboardProps {
  /** Ratings statistics grouped by user */
  byUser: RatingStat[];
  /** Ratings statistics grouped by tag */
  byTag: RatingStat[];
  /** Tag distribution data */
  tagDistribution: RatingDistribution[];
  /** Total number of candidates */
  totalCandidates: number;
  /** Number of rated candidates */
  ratedCandidates: number;
  /** Loading state */
  isLoading?: boolean;
  /** Custom class name */
  className?: string;
}

/**
 * Statistics dashboard showing rating distributions using ECharts.
 * Displays bar charts for ratings by user and by tag, plus overall stats.
 */
const StatsDashboard: React.FC<StatsDashboardProps> = ({
  byUser,
  byTag,
  tagDistribution,
  totalCandidates,
  ratedCandidates,
  isLoading = false,
  className = "",
}) => {
  const userChartRef = useRef<HTMLDivElement>(null);
  const tagChartRef = useRef<HTMLDivElement>(null);
  const pieChartRef = useRef<HTMLDivElement>(null);
  const [chartsReady, setChartsReady] = useState(false);

  // Render User Stats Chart
  useEffect(() => {
    if (!chartsReady || !userChartRef.current || byUser.length === 0) return;

    let disposed = false;
    const init = async () => {
      const echarts = await loadEcharts();
      if (!userChartRef.current || disposed) return;

      const chart = echarts.init(userChartRef.current);

      chart.setOption({
        title: {
          text: "Ratings by User",
          left: "center",
          textStyle: { fontSize: 14 },
        },
        tooltip: {
          trigger: "axis",
          axisPointer: { type: "shadow" },
        },
        legend: {
          data: ["True", "False", "Unsure"],
          bottom: 0,
        },
        grid: {
          left: "3%",
          right: "4%",
          bottom: "15%",
          top: "15%",
          containLabel: true,
        },
        xAxis: {
          type: "category",
          data: byUser.map((s) => s.label),
          axisLabel: { rotate: 45 },
        },
        yAxis: { type: "value" },
        series: [
          {
            name: "True",
            type: "bar",
            stack: "total",
            data: byUser.map((s) => s.trueCount),
            itemStyle: { color: "#22c55e" },
          },
          {
            name: "False",
            type: "bar",
            stack: "total",
            data: byUser.map((s) => s.falseCount),
            itemStyle: { color: "#ef4444" },
          },
          {
            name: "Unsure",
            type: "bar",
            stack: "total",
            data: byUser.map((s) => s.unsureCount),
            itemStyle: { color: "#f59e0b" },
          },
        ],
      });

      const handleResize = () => chart.resize();
      window.addEventListener("resize", handleResize);

      return () => {
        window.removeEventListener("resize", handleResize);
        chart.dispose();
        disposed = true;
      };
    };

    init();
  }, [byUser, chartsReady]);

  // Render Tag Stats Chart
  useEffect(() => {
    if (!chartsReady || !tagChartRef.current || byTag.length === 0) return;

    let disposed = false;
    const init = async () => {
      const echarts = await loadEcharts();
      if (!tagChartRef.current || disposed) return;

      const chart = echarts.init(tagChartRef.current);

      chart.setOption({
        title: {
          text: "Ratings by Tag",
          left: "center",
          textStyle: { fontSize: 14 },
        },
        tooltip: {
          trigger: "axis",
          axisPointer: { type: "shadow" },
        },
        legend: {
          data: ["True", "False", "Unsure"],
          bottom: 0,
        },
        grid: {
          left: "3%",
          right: "4%",
          bottom: "15%",
          top: "15%",
          containLabel: true,
        },
        xAxis: {
          type: "category",
          data: byTag.map((s) => s.label),
          axisLabel: { rotate: 45 },
        },
        yAxis: { type: "value" },
        series: [
          {
            name: "True",
            type: "bar",
            stack: "total",
            data: byTag.map((s) => s.trueCount),
            itemStyle: { color: "#22c55e" },
          },
          {
            name: "False",
            type: "bar",
            stack: "total",
            data: byTag.map((s) => s.falseCount),
            itemStyle: { color: "#ef4444" },
          },
          {
            name: "Unsure",
            type: "bar",
            stack: "total",
            data: byTag.map((s) => s.unsureCount),
            itemStyle: { color: "#f59e0b" },
          },
        ],
      });

      const handleResize = () => chart.resize();
      window.addEventListener("resize", handleResize);

      return () => {
        window.removeEventListener("resize", handleResize);
        chart.dispose();
        disposed = true;
      };
    };

    init();
  }, [byTag, chartsReady]);

  // Render Pie Chart
  useEffect(() => {
    if (!chartsReady || !pieChartRef.current || tagDistribution.length === 0)
      return;

    let disposed = false;
    const init = async () => {
      const echarts = await loadEcharts();
      if (!pieChartRef.current || disposed) return;

      const chart = echarts.init(pieChartRef.current);

      chart.setOption({
        title: {
          text: "Tag Distribution",
          left: "center",
          textStyle: { fontSize: 14 },
        },
        tooltip: {
          trigger: "item",
          formatter: "{b}: {c} ({d}%)",
        },
        series: [
          {
            type: "pie",
            radius: ["40%", "70%"],
            avoidLabelOverlap: false,
            itemStyle: {
              borderRadius: 4,
              borderColor: "#fff",
              borderWidth: 2,
            },
            label: {
              show: true,
              formatter: "{b}",
            },
            data: tagDistribution.map((d) => ({
              name: d.tag,
              value: d.count,
            })),
          },
        ],
      });

      const handleResize = () => chart.resize();
      window.addEventListener("resize", handleResize);

      return () => {
        window.removeEventListener("resize", handleResize);
        chart.dispose();
        disposed = true;
      };
    };

    init();
  }, [tagDistribution, chartsReady]);

  // Calculate overall stats
  const stats = useMemo(() => {
    const totalTrue = byTag.reduce((sum, t) => sum + t.trueCount, 0);
    const totalFalse = byTag.reduce((sum, t) => sum + t.falseCount, 0);
    const totalUnsure = byTag.reduce((sum, t) => sum + t.unsureCount, 0);
    const totalRated = totalTrue + totalFalse + totalUnsure;
    const unrated = totalCandidates - ratedCandidates;
    const progressPercent =
      totalCandidates > 0
        ? Math.round((ratedCandidates / totalCandidates) * 100)
        : 0;

    return {
      totalTrue,
      totalFalse,
      totalUnsure,
      totalRated,
      unrated,
      progressPercent,
    };
  }, [byTag, totalCandidates, ratedCandidates]);

  if (isLoading) {
    return (
      <div className={`flex items-center justify-center h-64 ${className}`}>
        <div className="w-8 h-8 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
        <span className="ml-2 text-gray-500">Loading statistics...</span>
      </div>
    );
  }

  if (!chartsReady) {
    return (
      <div className={`flex items-center justify-center h-64 ${className}`}>
        <div className="flex flex-col items-center gap-3 text-gray-600">
          <p className="text-sm text-center">
            Charts are deferred to avoid loading heavy libraries automatically.
          </p>
          <button
            type="button"
            className="btn btn-primary btn-sm"
            onClick={() => setChartsReady(true)}
            aria-label="Load charts"
          >
            Load charts
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className={`space-y-6 ${className}`}>
      {/* Summary Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="card p-4 text-center">
          <p className="text-3xl font-bold text-vast-blue">{totalCandidates}</p>
          <p className="stat-label">Total Candidates</p>
        </div>
        <div className="card p-4 text-center">
          <p className="text-3xl font-bold text-vast-green">
            {ratedCandidates}
          </p>
          <p className="stat-label">Rated</p>
        </div>
        <div className="card p-4 text-center">
          <p className="text-3xl font-bold text-gray-400">{stats.unrated}</p>
          <p className="stat-label">Unrated</p>
        </div>
        <div className="card p-4 text-center">
          <p className="text-3xl font-bold text-blue-500">
            {stats.progressPercent}%
          </p>
          <p className="stat-label">Progress</p>
        </div>
      </div>

      {/* Progress Bar */}
      <div className="card p-4">
        <div className="flex justify-between mb-2 text-sm">
          <span>Rating Progress</span>
          <span>
            {ratedCandidates} / {totalCandidates}
          </span>
        </div>
        <div className="h-4 bg-gray-200 rounded-full overflow-hidden">
          <div
            className="h-full bg-vast-green transition-all duration-300"
            style={{ width: `${stats.progressPercent}%` }}
          />
        </div>
      </div>

      {/* Rating Breakdown */}
      <div className="grid grid-cols-3 gap-4">
        <div className="card p-4 text-center border-l-4 border-green-500">
          <p className="text-2xl font-bold text-green-600">{stats.totalTrue}</p>
          <p className="stat-label">True</p>
        </div>
        <div className="card p-4 text-center border-l-4 border-red-500">
          <p className="text-2xl font-bold text-red-600">{stats.totalFalse}</p>
          <p className="stat-label">False</p>
        </div>
        <div className="card p-4 text-center border-l-4 border-yellow-500">
          <p className="text-2xl font-bold text-yellow-600">
            {stats.totalUnsure}
          </p>
          <p className="stat-label">Unsure</p>
        </div>
      </div>

      {/* Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="card p-4">
          <div ref={userChartRef} style={{ height: 300 }} />
        </div>
        <div className="card p-4">
          <div ref={tagChartRef} style={{ height: 300 }} />
        </div>
      </div>

      {/* Pie Chart */}
      <div className="card p-4">
        <div ref={pieChartRef} style={{ height: 300 }} />
      </div>
    </div>
  );
};

export default StatsDashboard;
