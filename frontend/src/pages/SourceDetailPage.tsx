import React, { useState, useEffect, useMemo } from "react";
import { useParams, Link } from "react-router-dom";
import ProvenanceStrip from "../components/provenance/ProvenanceStrip";
import ErrorDisplay from "../components/errors/ErrorDisplay";
import { WidgetErrorBoundary } from "../components/errors";
import {
  Card,
  CoordinateDisplay,
  PageSkeleton,
  QAMetrics,
} from "../components/common";
import { AladinLiteViewer, LightCurveChart } from "../components/widgets";
import { CatalogOverlayPanel } from "../components/catalogs";
import { NearbyObjectsPanel, NearbyObject } from "../components/crossmatch";
import type { LightCurveDataPoint } from "../components/widgets";
import {
  mapProvenanceFromSourceDetail,
  SourceDetailResponse,
} from "../utils/provenanceMappers";
import { relativeTime } from "../utils/relativeTime";
import { logger } from "../utils/logger";
import type { ErrorResponse } from "../types/errors";
import type { ProvenanceStripProps } from "../types/provenance";
import { useSource } from "../hooks/useQueries";
import { usePreferencesStore } from "../stores/appStore";
import { config } from "../config";

/** SIMBAD external link icon */
const ExternalLinkIcon: React.FC<{ className?: string }> = ({
  className = "w-4 h-4",
}) => (
  <svg
    className={className}
    fill="none"
    stroke="currentColor"
    viewBox="0 0 24 24"
  >
    <path
      strokeLinecap="round"
      strokeLinejoin="round"
      strokeWidth={2}
      d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"
    />
  </svg>
);

/**
 * Detail page for an astronomical source.
 * Displays source info, lightcurve, contributing images, and provenance.
 */
const SourceDetailPage: React.FC = () => {
  const { sourceId } = useParams<{ sourceId: string }>();
  const { data: source, isLoading, error, refetch } = useSource(sourceId);
  const addRecentSource = usePreferencesStore((state) => state.addRecentSource);
  const [selectedImageId, setSelectedImageId] = useState<string | undefined>(
    undefined
  );
  const [showSkyViewer, setShowSkyViewer] = useState(true);
  const encodedSourceId = sourceId ? encodeURIComponent(sourceId) : "";
  const [showNearbyPanel, setShowNearbyPanel] = useState(false);
  const [enabledCatalogs, setEnabledCatalogs] = useState<string[]>([]);

  // Search for nearby objects in external catalogs
  const handleNearbySearch = async (
    raDeg: number,
    decDeg: number,
    radiusArcmin: number
  ): Promise<NearbyObject[]> => {
    const results: NearbyObject[] = [];

    // Query SIMBAD via TAP
    try {
      const simbadQuery = `SELECT TOP 20 main_id, ra, dec, otype_longname
        FROM basic
        WHERE CONTAINS(POINT('ICRS', ra, dec), CIRCLE('ICRS', ${raDeg}, ${decDeg}, ${
        radiusArcmin / 60
      })) = 1`;
      const simbadRes = await fetch(
        `https://simbad.u-strasbg.fr/simbad/sim-tap/sync?REQUEST=doQuery&LANG=ADQL&FORMAT=json&QUERY=${encodeURIComponent(
          simbadQuery
        )}`
      );
      if (simbadRes.ok) {
        const simbadData = await simbadRes.json();
        const rows = simbadData.data || [];
        for (const row of rows) {
          const objRa = parseFloat(row[1]);
          const objDec = parseFloat(row[2]);
          const sep =
            Math.sqrt(
              Math.pow(
                (raDeg - objRa) * Math.cos((decDeg * Math.PI) / 180),
                2
              ) + Math.pow(decDeg - objDec, 2)
            ) * 3600;
          results.push({
            name: row[0],
            ra: objRa.toFixed(6),
            dec: objDec.toFixed(6),
            separation: sep,
            database: "SIMBAD",
            type: row[3] || undefined,
            url: `https://simbad.u-strasbg.fr/simbad/sim-id?Ident=${encodeURIComponent(
              row[0]
            )}`,
          });
        }
      }
    } catch (e) {
      logger.warn("SIMBAD query failed", { error: e });
    }

    return results;
  };

  // Track in recent items when source loads
  useEffect(() => {
    if (source && sourceId) {
      addRecentSource(sourceId);
    }
  }, [source, sourceId, addRecentSource]);

  // Set default selected image when source loads
  useEffect(() => {
    const sourceData = source as SourceDetailResponse | undefined;
    if (sourceData?.contributing_images?.length) {
      setSelectedImageId(sourceData.contributing_images[0].image_id);
    }
  }, [source]);

  // Generate light curve data from contributing images
  const lightCurveData = useMemo((): LightCurveDataPoint[] => {
    const sourceData = source as SourceDetailResponse | undefined;
    if (!sourceData?.contributing_images) return [];

    return sourceData.contributing_images
      .filter((img) => img.flux_jy !== undefined && img.created_at)
      .map((img) => ({
        time: img.created_at!,
        flux: img.flux_jy!,
        fluxError: (img as { flux_error_jy?: number }).flux_error_jy,
        label: img.path?.split("/").pop() || img.image_id,
      }))
      .sort((a, b) => new Date(a.time).getTime() - new Date(b.time).getTime());
  }, [source]);

  if (isLoading) {
    return <PageSkeleton variant="detail" showHeader showSidebar />;
  }

  if (error) {
    return (
      <div className="max-w-4xl mx-auto p-6">
        <ErrorDisplay
          error={error as unknown as ErrorResponse}
          onRetry={() => refetch()}
        />
      </div>
    );
  }

  if (!source) {
    return (
      <div className="max-w-4xl mx-auto p-6">
        <Card>
          <p className="text-gray-500 mb-4">Source not found.</p>
          <Link to="/sources" className="link">
            Back to Sources
          </Link>
        </Card>
      </div>
    );
  }

  // Cast for provenance mapper
  const sourceData = source as unknown as SourceDetailResponse;
  const provenance: ProvenanceStripProps | null = mapProvenanceFromSourceDetail(
    sourceData,
    selectedImageId
  );

  return (
    <div className="max-w-6xl mx-auto p-6">
      {/* Header */}
      <div className="mb-6">
        <Link
          to="/sources"
          className="text-sm text-gray-500 hover:text-gray-700 mb-2 inline-block"
        >
          Back to Sources
        </Link>
        <h1 className="text-2xl font-bold text-gray-900 mb-2">
          {sourceData.name || `Source ${sourceData.id}`}
        </h1>
        {provenance && <ProvenanceStrip {...provenance} />}
      </div>

      {/* Main content grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left column - Coordinates and actions (sticky on desktop) */}
        <div className="lg:col-span-1 sticky-sidebar">
          {/* Coordinates */}
          <Card title="Position">
            <CoordinateDisplay
              raDeg={sourceData.ra_deg}
              decDeg={sourceData.dec_deg}
              showDecimal
              allowFormatToggle
            />
            <div className="mt-4 pt-4 border-t border-gray-100 space-y-2">
              <a
                href={`https://simbad.u-strasbg.fr/simbad/sim-coo?Coord=${sourceData.ra_deg}+${sourceData.dec_deg}&CooFrame=FK5&CooEpoch=2000&CooEqui=2000&Radius=2&Radius.unit=arcmin`}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-1.5 text-sm text-blue-600 hover:text-blue-800 hover:underline"
              >
                <svg
                  className="w-4 h-4"
                  viewBox="0 0 24 24"
                  fill="currentColor"
                >
                  <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-1 17.93c-3.95-.49-7-3.85-7-7.93 0-.62.08-1.21.21-1.79L9 15v1c0 1.1.9 2 2 2v1.93zm6.9-2.54c-.26-.81-1-1.39-1.9-1.39h-1v-3c0-.55-.45-1-1-1H8v-2h2c.55 0 1-.45 1-1V7h2c1.1 0 2-.9 2-2v-.41c2.93 1.19 5 4.06 5 7.41 0 2.08-.8 3.97-2.1 5.39z" />
                </svg>
                Search in SIMBAD
                <ExternalLinkIcon className="w-3 h-3" />
              </a>
              <a
                href={`https://ned.ipac.caltech.edu/conesearch?search_type=Near%20Position%20Search&ra=${sourceData.ra_deg}&dec=${sourceData.dec_deg}&radius=2&in_csys=Equatorial&in_equinox=J2000`}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-1.5 text-sm text-blue-600 hover:text-blue-800 hover:underline"
              >
                <svg
                  className="w-4 h-4"
                  viewBox="0 0 24 24"
                  fill="currentColor"
                >
                  <path d="M12 3L1 9l4 2.18v6L12 21l7-3.82v-6l2-1.09V17h2V9L12 3zm6.82 6L12 12.72 5.18 9 12 5.28 18.82 9zM17 15.99l-5 2.73-5-2.73v-3.72L12 15l5-2.73v3.72z" />
                </svg>
                Search in NED
                <ExternalLinkIcon className="w-3 h-3" />
              </a>
            </div>
          </Card>

          {/* Actions */}
          <Card title="Actions">
            <div className="flex flex-col gap-2">
              <button
                type="button"
                className="btn btn-primary"
                onClick={() =>
                  window.open(
                    `${config.api.baseUrl}/sources/${encodedSourceId}/export`,
                    "_blank",
                    "noopener,noreferrer"
                  )
                }
              >
                View Lightcurve
              </button>
              <button
                type="button"
                className="btn btn-secondary"
                onClick={() =>
                  window.open(
                    `${config.api.baseUrl}/sources/${encodedSourceId}/contributing-images`,
                    "_blank",
                    "noopener,noreferrer"
                  )
                }
              >
                Download Postage Stamps
              </button>
              <button
                type="button"
                className="btn btn-secondary"
                onClick={() =>
                  window.open(
                    `${
                      import.meta.env.VITE_API_URL || "/api"
                    }/sources/${encodedSourceId}/variability`,
                    "_blank",
                    "noopener,noreferrer"
                  )
                }
              >
                Variability Analysis
              </button>
            </div>
          </Card>

          {/* Source metadata */}
          <Card title="Details">
            <dl className="space-y-3">
              <div>
                <dt className="text-xs text-gray-500 uppercase tracking-wide">
                  Source ID
                </dt>
                <dd className="font-mono text-sm text-gray-900">
                  {sourceData.id}
                </dd>
              </div>
              {sourceData.name && (
                <div>
                  <dt className="text-xs text-gray-500 uppercase tracking-wide">
                    Name
                  </dt>
                  <dd className="text-sm text-gray-900">{sourceData.name}</dd>
                </div>
              )}
              <div>
                <dt className="text-xs text-gray-500 uppercase tracking-wide">
                  Detections
                </dt>
                <dd className="text-sm text-gray-900">
                  {sourceData.contributing_images?.length || 0} images
                </dd>
              </div>
            </dl>
          </Card>

          {/* Source Quality Assessment */}
          {sourceData.contributing_images &&
            sourceData.contributing_images.length > 0 &&
            (() => {
              // Compute aggregate QA metrics from contributing images
              const imagesWithQA = sourceData.contributing_images.filter(
                (img) => img.qa_grade
              );
              const goodCount = imagesWithQA.filter(
                (img) => img.qa_grade === "good"
              ).length;
              const warnCount = imagesWithQA.filter(
                (img) => img.qa_grade === "warn"
              ).length;
              const failCount = imagesWithQA.filter(
                (img) => img.qa_grade === "fail"
              ).length;

              // Determine overall grade based on majority
              let overallGrade: "good" | "warn" | "fail" | undefined;
              if (imagesWithQA.length > 0) {
                if (failCount > goodCount && failCount > warnCount)
                  overallGrade = "fail";
                else if (warnCount > goodCount) overallGrade = "warn";
                else if (goodCount > 0) overallGrade = "good";
              }

              return overallGrade ? (
                <Card title="Quality Assessment">
                  <QAMetrics
                    grade={overallGrade}
                    summary={`Based on ${imagesWithQA.length} image${
                      imagesWithQA.length !== 1 ? "s" : ""
                    }: ${goodCount} good, ${warnCount} marginal, ${failCount} failed`}
                    compact={false}
                  />
                </Card>
              ) : null;
            })()}
        </div>

        {/* Right column - Interactive widgets and images */}
        <div className="lg:col-span-2 space-y-6">
          {/* Sky Viewer - Aladin Lite */}
          <Card
            title="Sky View"
            subtitle={
              <button
                type="button"
                onClick={() => setShowSkyViewer(!showSkyViewer)}
                className="text-xs text-blue-600 hover:text-blue-800"
              >
                {showSkyViewer ? "Hide" : "Show"}
              </button>
            }
          >
            {showSkyViewer && (
              <WidgetErrorBoundary widgetName="Sky Viewer" minHeight={300}>
                <AladinLiteViewer
                  raDeg={sourceData.ra_deg}
                  decDeg={sourceData.dec_deg}
                  fov={0.1}
                  height={300}
                  sourceName={sourceData.name || `Source ${sourceData.id}`}
                  className="rounded-lg overflow-hidden"
                />
              </WidgetErrorBoundary>
            )}
          </Card>

          {/* VizieR Catalog Overlays */}
          <Card title="Catalog Crossmatch">
            <WidgetErrorBoundary widgetName="Catalog Overlays" minHeight={200}>
              <CatalogOverlayPanel
                centerRa={sourceData.ra_deg}
                centerDec={sourceData.dec_deg}
                searchRadius={2}
                enabledCatalogs={enabledCatalogs}
                onCatalogChange={setEnabledCatalogs}
              />
            </WidgetErrorBoundary>
          </Card>

          {/* Nearby Objects from SIMBAD/NED */}
          <Card
            title="Nearby Objects"
            subtitle={
              <button
                type="button"
                onClick={() => setShowNearbyPanel(!showNearbyPanel)}
                className="text-xs text-blue-600 hover:text-blue-800"
              >
                {showNearbyPanel ? "Hide" : "Search SIMBAD"}
              </button>
            }
          >
            {showNearbyPanel && (
              <WidgetErrorBoundary widgetName="Nearby Objects" minHeight={150}>
                <NearbyObjectsPanel
                  raDeg={sourceData.ra_deg}
                  decDeg={sourceData.dec_deg}
                  initialRadius={2}
                  maxRadius={30}
                  onSearch={handleNearbySearch}
                />
              </WidgetErrorBoundary>
            )}
            {!showNearbyPanel && (
              <p className="text-sm text-gray-500">
                Click &quot;Search SIMBAD&quot; to find nearby objects in
                external catalogs.
              </p>
            )}
          </Card>

          {/* Light Curve Chart */}
          {lightCurveData.length > 1 && (
            <Card
              title="Light Curve"
              subtitle={`${lightCurveData.length} measurements`}
            >
              <WidgetErrorBoundary
                widgetName="Light Curve Chart"
                minHeight={300}
              >
                <LightCurveChart
                  data={lightCurveData}
                  height={300}
                  yAxisLabel="Flux"
                  xAxisLabel="Observation Date"
                  enableZoom={true}
                  showErrorBars={true}
                  onPointClick={(point) => {
                    // Find the corresponding image and select it
                    const img = sourceData.contributing_images?.find(
                      (i) => i.created_at === point.time
                    );
                    if (img) {
                      setSelectedImageId(img.image_id);
                    }
                  }}
                />
              </WidgetErrorBoundary>
            </Card>
          )}

          {/* Contributing Images */}
          {sourceData.contributing_images &&
            sourceData.contributing_images.length > 0 && (
              <Card
                title="Contributing Images"
                subtitle={`${sourceData.contributing_images.length} detection${
                  sourceData.contributing_images.length !== 1 ? "s" : ""
                }`}
              >
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  {sourceData.contributing_images.map((img) => (
                    <div
                      key={img.image_id}
                      className={`p-3 rounded-lg border-2 cursor-pointer transition-all ${
                        selectedImageId === img.image_id
                          ? "border-blue-500 bg-blue-50"
                          : "border-gray-200 hover:border-gray-300 bg-white"
                      }`}
                      onClick={() => setSelectedImageId(img.image_id)}
                      onKeyDown={(e) => {
                        if (e.key === "Enter" || e.key === " ") {
                          setSelectedImageId(img.image_id);
                        }
                      }}
                      role="button"
                      tabIndex={0}
                    >
                      <div className="flex items-start justify-between">
                        <div className="flex-1 min-w-0">
                          <Link
                            to={`/images/${img.image_id}`}
                            className="font-medium text-gray-900 hover:text-blue-600 truncate block"
                            onClick={(e) => e.stopPropagation()}
                          >
                            {img.path?.split("/").pop() || img.image_id}
                          </Link>
                          {img.ms_path && (
                            <div className="text-xs text-gray-500 truncate mt-0.5">
                              MS: {img.ms_path.split("/").pop()}
                            </div>
                          )}
                        </div>
                        {img.qa_grade && (
                          <span
                            className={`badge ml-2 ${
                              img.qa_grade === "good"
                                ? "badge-success"
                                : img.qa_grade === "warn"
                                ? "badge-warning"
                                : "badge-error"
                            }`}
                          >
                            {img.qa_grade}
                          </span>
                        )}
                      </div>

                      {/* Flux and date info */}
                      <div className="flex items-center gap-3 mt-2 text-xs text-gray-500">
                        {img.flux_jy !== undefined && (
                          <span>
                            <span className="font-medium">Flux:</span>{" "}
                            {img.flux_jy < 0.001
                              ? `${(img.flux_jy * 1e6).toFixed(1)} μJy`
                              : img.flux_jy < 1
                              ? `${(img.flux_jy * 1e3).toFixed(2)} mJy`
                              : `${img.flux_jy.toFixed(3)} Jy`}
                          </span>
                        )}
                        {img.created_at && (
                          <span
                            title={new Date(img.created_at).toLocaleString()}
                          >
                            {relativeTime(img.created_at)}
                          </span>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </Card>
            )}

          {/* Empty state */}
          {(!sourceData.contributing_images ||
            sourceData.contributing_images.length === 0) && (
            <Card>
              <div className="text-center py-8 text-gray-500">
                <svg
                  className="w-12 h-12 mx-auto mb-3 text-gray-300"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z"
                  />
                </svg>
                <p>No contributing images found for this source.</p>
              </div>
            </Card>
          )}
        </div>
      </div>
    </div>
  );
};

export default SourceDetailPage;
