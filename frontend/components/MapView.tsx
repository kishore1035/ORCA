// frontend/components/MapView.tsx
"use client";
import { MapContainer, TileLayer, Marker, Popup } from "react-leaflet";
import L from "leaflet";
import "leaflet/dist/leaflet.css";

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
}

export function MapView({ lat, lon, label }: MapViewProps) {
  const center: [number, number] = lat != null && lon != null ? [lat, lon] : [10.0, 76.0];
  return (
    <MapContainer center={center} zoom={lat != null ? 9 : 5} className="h-full w-full">
      <TileLayer
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        attribution="&copy; OpenStreetMap contributors"
      />
      {lat != null && lon != null && (
        <Marker position={[lat, lon]}>{label && <Popup>{label}</Popup>}</Marker>
      )}
    </MapContainer>
  );
}
