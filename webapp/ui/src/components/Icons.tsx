// Line icons in one style: 24px grid, 1.8 stroke, round joins.

import type { ReactNode } from "react";

function Icon({ size = 22, children }: { size?: number; children: ReactNode }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.8"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden
    >
      {children}
    </svg>
  );
}

export const ArrowCircle = ({ size }: { size?: number }) => (
  <Icon size={size}>
    <circle cx="12" cy="12" r="9.5" />
    <path d="M8 12h7.5M12.5 8.8 15.7 12l-3.2 3.2" />
  </Icon>
);

export const Sun = ({ size }: { size?: number }) => (
  <Icon size={size}>
    <circle cx="12" cy="12" r="4" />
    <path d="M12 2.5v2M12 19.5v2M4.6 4.6 6 6M18 18l1.4 1.4M2.5 12h2M19.5 12h2M4.6 19.4 6 18M18 6l1.4-1.4" />
  </Icon>
);

export const MapPin = ({ size }: { size?: number }) => (
  <Icon size={size}>
    <path d="M12 21s-6.5-5.6-6.5-11a6.5 6.5 0 0 1 13 0c0 5.4-6.5 11-6.5 11Z" />
    <circle cx="12" cy="10" r="2.3" />
  </Icon>
);

export const Chart = ({ size }: { size?: number }) => (
  <Icon size={size}>
    <path d="M4 20V4M4 20h16" />
    <path d="M8 16v-4M12 16V8M16 16v-6" />
  </Icon>
);

export const Calculator = ({ size }: { size?: number }) => (
  <Icon size={size}>
    <rect x="5" y="3" width="14" height="18" rx="2.5" />
    <path d="M8.5 7h7M8.5 11.5h.01M12 11.5h.01M15.5 11.5h.01M8.5 15h.01M12 15h.01M15.5 15h.01" />
  </Icon>
);

