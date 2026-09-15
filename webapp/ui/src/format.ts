export const inr = (value: number, digits = 2) =>
  `₹${value.toLocaleString("en-IN", { minimumFractionDigits: digits, maximumFractionDigits: digits })}`;

export const kwh = (value: number) =>
  `${value.toLocaleString("en-IN", { maximumFractionDigits: 0 })} kWh`;

export const count = (value: number) => value.toLocaleString("en-IN");

export const capacity = (kw: number) =>
  kw >= 1000
    ? `${(kw / 1000).toLocaleString("en-IN", { maximumFractionDigits: 1 })} MW`
    : `${kw.toLocaleString("en-IN", { maximumFractionDigits: 0 })} kW`;

export const coords = (lat: number, lon: number, digits = 2) =>
  `${lat.toFixed(digits)}°N ${lon.toFixed(digits)}°E`;
