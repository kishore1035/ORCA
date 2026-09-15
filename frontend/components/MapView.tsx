// frontend/components/MapView.tsx
"use client";
import { MapContainer, TileLayer, Marker, Popup } from "react-leaflet";
import "leaflet/dist/leaflet.css";

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
