// frontend/components/MapView.tsx
"use client";

import { useEffect } from "react";
import {
  MapContainer,
  TileLayer,
  Marker,
  Popup,
  Polyline,
  CircleMarker,
  useMap,
} from "react-leaflet";
import { MapPin } from "lucide-react";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import { RouteWaypoint } from "@/lib/types";

// Configure default marker icon for bundled apps
import markerIcon from "leaflet/dist/images/marker-icon.png";
import markerIcon2x from "leaflet/dist/images/marker-icon-2x.png";
import markerShadow from "leaflet/dist/images/marker-shadow.png";

function assetUrl(asset: unknown): string {
  return (asset as { src?: string })?.src ?? (asset as string);
}

L.Icon.Default.mergeOptions({
  iconUrl: assetUrl(markerIcon),
  iconRetinaUrl: assetUrl(markerIcon2x),
  shadowUrl: assetUrl(markerShadow),
});

interface MapViewProps {
  lat: number | null;
  lon: number | null;
  label?: string;
  placeName?: string | null;
  route?: RouteWaypoint[];
  onSelectLocation?: (lat: number, lon: number) => void;
}

/**
 * Controller component that reactively recenters and animates the map
 * whenever the conversation resolves or changes coordinates/routes.
 */
function MapController({
  lat,
  lon,
  route,
}: {
  lat: number | null;
  lon: number | null;
  route?: RouteWaypoint[];
}) {
  const map = useMap();

  useEffect(() => {
    const container = map.getContainer();
    if (!container || typeof ResizeObserver === "undefined") return;
    const observer = new ResizeObserver(() => {
      map.invalidateSize();
    });
    observer.observe(container);
    return () => observer.disconnect();
  }, [map]);

  useEffect(() => {
    if (route && route.length > 0) {
      const bounds = L.latLngBounds(route.map((r) => [r.lat, r.lon]));
      map.fitBounds(bounds, { padding: [35, 35], maxZoom: 12 });
    } else if (lat != null && lon != null) {
      map.flyTo([lat, lon], 10, {
        duration: 1.2,
        easeLinearity: 0.25,
      });
    }
  }, [lat, lon, route, map]);

  return null;
}

export function MapView({
  lat,
  lon,
  label,
  placeName,
  route,
}: MapViewProps) {
  const center: [number, number] =
    route && route.length > 0
      ? [route[0].lat, route[0].lon]
      : lat != null && lon != null
      ? [lat, lon]
      : [13.0, 77.0];

  const defaultZoom = lat != null || route ? 9 : 5;

  return (
    <div className="relative h-full w-full bg-slate-900 overflow-hidden">
      <MapContainer
        center={center}
        zoom={defaultZoom}
        className="h-full w-full"
        zoomControl={true}
      >
        <MapController lat={lat} lon={lon} route={route} />

        <TileLayer
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
        />

        {/* Active Pinned Sector Marker with Pulsing Ring */}
        {lat != null && lon != null && !route && (
          <>
            {/* Visual Halo / Pulse Ring */}
            <CircleMarker
              center={[lat, lon]}
              radius={22}
              pathOptions={{
                color: "#0284c7",
                fillColor: "#38bdf8",
                fillOpacity: 0.2,
                weight: 2,
              }}
            />
            <CircleMarker
              center={[lat, lon]}
              radius={8}
              pathOptions={{
                color: "#ffffff",
                fillColor: "#0284c7",
                fillOpacity: 1,
                weight: 2,
              }}
            />
            <Marker position={[lat, lon]}>
              <Popup autoPan={false}>
                <div className="p-1 space-y-1">
                  <div className="font-bold text-slate-900 text-xs flex items-center gap-1">
                    <MapPin className="w-3 h-3 text-slate-700 inline shrink-0" />
                    <span>{placeName || "Resolved Marine Sector"}</span>
                  </div>
                  <div className="text-[11px] font-mono text-slate-500">
                    {lat.toFixed(4)}°N, {lon.toFixed(4)}°E
                  </div>
                  {label && (
                    <div className="text-[11px] text-slate-700 font-medium pt-1 border-t border-slate-100">
                      {label}
                    </div>
                  )}
                </div>
              </Popup>
            </Marker>
          </>
        )}

        {/* Route Segments */}
        {route &&
          route.slice(0, -1).map((wp, i) => {
            const next = route[i + 1];
            const segmentHazardous = wp.verdict === "unsafe" || next.verdict === "unsafe";
            return (
              <Polyline
                key={`segment-${i}`}
                positions={[
                  [wp.lat, wp.lon],
                  [next.lat, next.lon],
                ]}
                pathOptions={{
                  color: segmentHazardous ? "#dc2626" : "#0284c7",
                  weight: 4,
                  opacity: 0.9,
                  dashArray: segmentHazardous ? "8, 8" : undefined,
                }}
              />
            );
          })}

        {/* Route Waypoints */}
        {route &&
          route.map((wp, i) => (
            <CircleMarker
              key={`waypoint-${i}`}
              center={[wp.lat, wp.lon]}
              radius={7}
              pathOptions={{
                color: "#ffffff",
                fillColor: wp.verdict === "unsafe" ? "#dc2626" : "#16a34a",
                fillOpacity: 0.95,
                weight: 2,
              }}
            >
              <Popup>
                <div className="p-1 space-y-1 text-xs">
                  <div className="font-bold">
                    {wp.rerouted
                      ? "Rerouted around hazard"
                      : wp.verdict === "unsafe"
                      ? "Hazardous Sector"
                      : "Safe Passage Waypoint"}
                  </div>
                  <div className="text-slate-600 font-mono text-[11px]">
                    {wp.lat.toFixed(4)}°N, {wp.lon.toFixed(4)}°E
                  </div>
                  <div className="text-slate-700">
                    {wp.reasons.join("; ")}
                  </div>
                  {wp.rerouted && wp.original && (
                    <div className="text-[11px] text-amber-700 bg-amber-50 p-1 rounded border border-amber-200 mt-1">
                      Original point unsafe: {wp.original.reasons.join("; ")}
                    </div>
                  )}
                </div>
              </Popup>
            </CircleMarker>
          ))}
      </MapContainer>

      {/* ── FLOATING HUD LOCATION CONFIRMATION CARD (Apple HIG Style) ── */}
      <div className="absolute bottom-3 left-3 z-[1000] pointer-events-auto">
        {lat != null && lon != null ? (
          <div className="px-3.5 py-2.5 rounded-2xl bg-white/95 backdrop-blur-md border border-slate-200/90 shadow-[0_4px_20px_rgba(0,0,0,0.08)] flex items-center gap-3 text-xs max-w-sm">
            <div className="w-7 h-7 rounded-xl bg-sky-50 border border-sky-200 text-sky-700 flex items-center justify-center font-bold text-xs shrink-0 shadow-2xs">
              <MapPin className="w-3.5 h-3.5" />
            </div>
            <div className="min-w-0">
              <div className="font-bold text-slate-900 truncate">
                {placeName || "Resolved Coastal Sector"}
              </div>
              <div className="text-[10px] font-mono text-slate-500">
                {lat.toFixed(4)}°N, {lon.toFixed(4)}°E · Synced to chat
              </div>
            </div>
          </div>
        ) : (
          <div className="px-3 py-2 rounded-2xl bg-white/90 backdrop-blur-md border border-slate-200/80 shadow-xs flex items-center gap-2 text-xs text-slate-600">
            <span className="w-2 h-2 rounded-full bg-slate-400" />
            <span className="font-medium text-[11px]">
              Pan/zoom or ask about any coastal sector
            </span>
          </div>
        )}
      </div>
    </div>
  );
}
