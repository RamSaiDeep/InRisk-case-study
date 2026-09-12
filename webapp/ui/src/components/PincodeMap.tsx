import type { LocationResponse } from "../types";

// A locator sketch, not a basemap: the pincode's own boundary, the centroid
// taken from it, and the ERA5-Land cell that centroid falls into. Drawing the
// cell to scale is the point - it shows at a glance how much larger than the
// pincode the settlement area is.

const W = 460;
const H = 300;
const PAD = 34;

export function PincodeMap({ location }: { location: LocationResponse }) {
  const { outline, centroid, pixel, cell_deg } = location;
  if (!outline?.length) return null;

  const half = cell_deg / 2;
  const cell = {
    west: pixel.lon - half,
    east: pixel.lon + half,
    south: pixel.lat - half,
    north: pixel.lat + half,
  };

  // The view has to hold both the pincode and the whole cell, or the cell
  // would be cropped and read as smaller than it is.
  const lons = [...outline.map((p) => p[0]), cell.west, cell.east];
  const lats = [...outline.map((p) => p[1]), cell.south, cell.north];
  const west = Math.min(...lons);
  const east = Math.max(...lons);
  const south = Math.min(...lats);
  const north = Math.max(...lats);

  // One scale for both axes, so shapes are not stretched. Latitude degrees are
  // longer than longitude degrees at this latitude; correcting by cos(lat)
  // keeps the cell square on screen, as it is on the ground.
  const cosLat = Math.cos((centroid.lat * Math.PI) / 180);
  const spanX = (east - west) * cosLat;
  const spanY = north - south;
  const scale = Math.min((W - 2 * PAD) / spanX, (H - 2 * PAD) / spanY);
  const offsetX = (W - spanX * scale) / 2;
  const offsetY = (H - spanY * scale) / 2;
  const x = (lon: number) => offsetX + (lon - west) * cosLat * scale;
  const y = (lat: number) => H - offsetY - (lat - south) * scale;

  const ring = outline.map(([lon, lat]) => `${x(lon).toFixed(1)},${y(lat).toFixed(1)}`).join(" ");
  const kmPerDegree = 111.32;
  const cellKm = cell_deg * kmPerDegree;

  return (
    <figure className="map">
      <svg viewBox={`0 0 ${W} ${H}`} width="100%" role="img"
        aria-label={`Pincode ${location.pincode} with its centroid and the ERA5-Land cell used for settlement`}>
        <rect
          x={x(cell.west)}
          y={y(cell.north)}
          width={(cell.east - cell.west) * cosLat * scale}
          height={(cell.north - cell.south) * scale}
          fill="var(--accent)"
          fillOpacity={0.07}
          stroke="var(--accent)"
          strokeOpacity={0.5}
          strokeWidth={1.5}
          rx={2}
        />
        <polygon
          points={ring}
          fill="var(--ink-secondary)"
          fillOpacity={0.14}
          stroke="var(--ink-secondary)"
          strokeWidth={1.5}
          strokeLinejoin="round"
        />
        {/* Centroid: the point the snap was taken from. */}
        <g stroke="var(--ink-primary)" strokeWidth={1.8}>
          <line x1={x(centroid.lon) - 5} y1={y(centroid.lat) - 5} x2={x(centroid.lon) + 5} y2={y(centroid.lat) + 5} />
          <line x1={x(centroid.lon) - 5} y1={y(centroid.lat) + 5} x2={x(centroid.lon) + 5} y2={y(centroid.lat) - 5} />
        </g>
        {/* The cell centre, which is what the data is actually read at. */}
        <circle
          cx={x(pixel.lon)}
          cy={y(pixel.lat)}
          r={5}
          fill="var(--accent)"
          stroke="var(--surface-1)"
          strokeWidth={2}
        />
        <text
          x={x(cell.west) + 5}
          y={y(cell.north) + 13}
          fontSize={10.5}
          fill="var(--accent)"
        >
          ERA5-Land cell · {cellKm.toFixed(0)} km
        </text>
      </svg>
      <figcaption className="legend">
        <span className="legend-item">
          <svg width={12} height={12} aria-hidden>
            <g stroke="var(--ink-primary)" strokeWidth={1.6}>
              <line x1={2} y1={2} x2={10} y2={10} />
              <line x1={2} y1={10} x2={10} y2={2} />
            </g>
          </svg>
          Pincode centroid
        </span>
        <span className="legend-item">
          <svg width={12} height={12} aria-hidden>
            <circle cx={6} cy={6} r={4} fill="var(--accent)" />
          </svg>
          Cell centre · readings taken here
        </span>
        <span className="legend-item">
          <span className="swatch" style={{ background: "var(--ink-secondary)", opacity: 0.35 }} />
          Pincode {location.pincode}
        </span>
      </figcaption>
    </figure>
  );
}
