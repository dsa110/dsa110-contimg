import React, { useMemo } from "react";
import { useParams, useSearchParams } from "react-router-dom";
import LogViewer from "../components/logs/LogViewer";
import type { LogLevel, LogQueryParams } from "@/types/logs";

function parseSearchParams(
  params: URLSearchParams,
  runIdParam?: string
): LogQueryParams {
  const query: LogQueryParams = {};
  const q = params.get("q");
  if (q) query.q = q;

  const level = params.get("level");
  if (level) {
    const parts = level.split(",").map((p) => p.trim()).filter(Boolean) as LogLevel[];
    query.level = parts.length > 1 ? parts : parts[0];
  }

  const labels: Record<string, string> = {};
  const service = params.get("service");
  if (service) labels.service = service;

  const runId = params.get("run_id") ?? runIdParam;
  if (runId) labels.run_id = runId;
  if (Object.keys(labels).length) query.labels = labels;

  const start = params.get("start");
  const end = params.get("end");
  if (start || end) {
    query.range = {
      start: start ?? "",
      end: end ?? undefined,
    };
  }

  return query;
}

function serializeQuery(query: LogQueryParams): URLSearchParams {
  const params = new URLSearchParams();
  if (query.q) params.set("q", query.q);
  if (query.level) {
    const levels = Array.isArray(query.level) ? query.level.join(",") : query.level;
    params.set("level", levels);
  }
  if (query.labels) {
    if (query.labels.service) params.set("service", String(query.labels.service));
    if (query.labels.run_id) params.set("run_id", String(query.labels.run_id));
  }
  if (query.range?.start) params.set("start", String(query.range.start));
  if (query.range?.end) params.set("end", String(query.range.end));
  return params;
}

export default function LogsPage() {
  const { runId } = useParams<{ runId?: string }>();
  const [searchParams, setSearchParams] = useSearchParams();

  const initialQuery = useMemo(
    () => parseSearchParams(searchParams, runId),
    [runId, searchParams]
  );

  return (
    <LogViewer
      initialQuery={initialQuery}
      onQueryChange={(next) => setSearchParams(serializeQuery(next), { replace: true })}
      storageKey="log-viewer-saved-searches"
    />
  );
}
