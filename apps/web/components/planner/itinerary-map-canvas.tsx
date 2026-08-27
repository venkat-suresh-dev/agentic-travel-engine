"use client";

import { useEffect, useMemo } from "react";
import { MapContainer, Marker, Polyline, Popup, TileLayer, useMap } from "react-leaflet";
import L from "leaflet";

import type { MapLeg, MapMarker } from "@/components/planner/itinerary-map";

import "leaflet/dist/leaflet.css";

const CATEGORY_COLORS: Record<string, string> = {
  restaurant: "#c45c26",
  attraction: "#2d6a4f",
  hotel: "#3d5a80",
  flight: "#5c4d7d",
  transport: "#6c757d",
  free_time: "#8d99ae",
  other: "#457b9d",
};

function createMarkerIcon(category: string, selected: boolean) {
  const color = selected ? "#0d5c63" : (CATEGORY_COLORS[category] ?? CATEGORY_COLORS.other);
  const size = selected ? 18 : 12;
  return L.divIcon({
    className: "",
    html: `<span style="display:block;width:${size}px;height:${size}px;border-radius:9999px;background:${color};border:2px solid white;box-shadow:0 1px 4px rgba(13,92,99,.35)"></span>`,
    iconSize: [size, size],
    iconAnchor: [size / 2, size / 2],
  });
}

function FitBounds({
  markers,
}: {
  markers: MapMarker[];
}) {
  const map = useMap();
  const bounds = useMemo(() => {
    const dayMarkers = markers.filter((marker) => marker.category !== "hotel");
    const fitMarkers = dayMarkers.length > 0 ? dayMarkers : markers;
    if (fitMarkers.length === 0) {
      return null;
    }
    return L.latLngBounds(fitMarkers.map((marker) => [marker.latitude, marker.longitude]));
  }, [markers]);

  useEffect(() => {
    if (!bounds) {
      return;
    }
    if (markers.length === 1) {
      map.setView([markers[0]!.latitude, markers[0]!.longitude], 14);
      return;
    }
    map.fitBounds(bounds, { padding: [28, 28], maxZoom: 14 });
  }, [bounds, map, markers]);

  return null;
}

interface ItineraryMapCanvasProps {
  markers: MapMarker[];
  legs?: MapLeg[];
  selectedItemId?: string | null;
  onSelectItem?: (itemId: string) => void;
}

export function ItineraryMapCanvas({
  markers,
  legs = [],
  selectedItemId,
  onSelectItem,
}: ItineraryMapCanvasProps) {
  const center = markers[0]
    ? ([markers[0].latitude, markers[0].longitude] as [number, number])
    : ([25.2048, 55.2708] as [number, number]);

  return (
    <MapContainer
      center={center}
      zoom={14}
      className="h-full w-full"
      scrollWheelZoom={false}
      attributionControl={false}
    >
      <TileLayer url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />
      <FitBounds markers={markers} />
      {legs.map((leg) => (
        <Polyline
          key={leg.id}
          positions={[leg.from, leg.to]}
          pathOptions={{
            color: "#0d5c63",
            weight: 2.5,
            opacity: 0.7,
            dashArray: "5 6",
          }}
        />
      ))}
      {markers.map((marker) => (
        <Marker
          key={marker.id}
          position={[marker.latitude, marker.longitude]}
          icon={createMarkerIcon(
            marker.category,
            marker.itemId === selectedItemId,
          )}
          eventHandlers={{
            click: () => onSelectItem?.(marker.itemId),
          }}
        >
          <Popup>
            <div className="text-xs">
              <p className="font-medium">{marker.title}</p>
              <p className="text-[var(--foreground-muted)]">
                Day {marker.dayNumber}
              </p>
            </div>
          </Popup>
        </Marker>
      ))}
    </MapContainer>
  );
}
