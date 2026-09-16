// frontend/components/MapView.tsx
"use client";
import { MapContainer, TileLayer, Marker, Popup, Polyline, CircleMarker } from "react-leaflet";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import { RouteWaypoint } from "@/lib/types";

// Configure default marker icon for bundled apps
import markerIcon from "leaflet/dist/images/marker-icon.png";
import markerIcon2x from "leaflet/dist/images/marker-icon-2x.png";
import markerShadow from "leaflet/dist/images/marker-shadow.png";

// Bundlers vary: some resolve a static image import to a plain URL string,
// others (e.g. next/image-style loaders) resolve it to a StaticImageData-like
// object with a `.src` property. Handle both so iconUrl never stringifies to
// "[object Object]".
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
  route?: RouteWaypoint[];
}

export function MapView({ lat, lon, label, route }: MapViewProps) {
  const center: [number, number] =
    route && route.length > 0
      ? [route[0].lat, route[0].lon]
      : lat != null && lon != null
        ? [lat, lon]
        : [10.0, 76.0];
  return (
    <MapContainer center={center} zoom={lat != null || route ? 9 : 5} className="h-full w-full">
      <TileLayer
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        attribution="&copy; OpenStreetMap contributors"
      />
      {lat != null && lon != null && !route && (
        <Marker position={[lat, lon]}>{label && <Popup>{label}</Popup>}</Marker>
      )}
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
              pathOptions={{ color: segmentHazardous ? "#dc2626" : "#2563eb", weight: 4 }}
            />
          );
        })}
      {route &&
        route.map((wp, i) => (
          <CircleMarker
            key={`waypoint-${i}`}
            center={[wp.lat, wp.lon]}
            radius={7}
            pathOptions={{
              color: wp.verdict === "unsafe" ? "#dc2626" : "#16a34a",
              fillColor: wp.verdict === "unsafe" ? "#dc2626" : "#16a34a",
              fillOpacity: 0.9,
            }}
          >
            <Popup>
              {wp.rerouted ? "🔀 Rerouted around hazard" : wp.verdict === "unsafe" ? "⚠️ Hazardous" : "✓ Safe"}
              <br />
              {wp.reasons.join("; ")}
              {wp.rerouted && wp.original && (
                <>
                  <br />
                  <em>Original point was unsafe: {wp.original.reasons.join("; ")}</em>
                </>
              )}
            </Popup>
          </CircleMarker>
        ))}
    </MapContainer>
  );
}
