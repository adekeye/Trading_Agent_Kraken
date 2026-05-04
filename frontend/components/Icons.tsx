/**
 * Lightweight inline SVG icons. Stroke-only, currentColor, lucide-style.
 * Kept here so we don't add a runtime dep.
 */
import type { SVGProps } from "react";

type IconProps = SVGProps<SVGSVGElement> & { size?: number };

function I({ size = 14, className, ...rest }: IconProps) {
  return {
    width: size,
    height: size,
    className: ["icon", className].filter(Boolean).join(" "),
    viewBox: "0 0 24 24",
    fill: "none",
    stroke: "currentColor",
    strokeWidth: 1.5,
    strokeLinecap: "round" as const,
    strokeLinejoin: "round" as const,
    ...rest,
  };
}

export const TerminalIcon = (p: IconProps) => (
  <svg {...I(p)}><polyline points="4 17 10 11 4 5" /><line x1="12" y1="19" x2="20" y2="19" /></svg>
);
export const WalletIcon = (p: IconProps) => (
  <svg {...I(p)}><path d="M21 12V7H5a2 2 0 0 1 0-4h14v4" /><path d="M3 5v14a2 2 0 0 0 2 2h16v-5" /><circle cx="17" cy="14" r="1.5" /></svg>
);
export const ListIcon = (p: IconProps) => (
  <svg {...I(p)}><line x1="8" y1="6" x2="21" y2="6" /><line x1="8" y1="12" x2="21" y2="12" /><line x1="8" y1="18" x2="21" y2="18" /><circle cx="4" cy="6" r="1" /><circle cx="4" cy="12" r="1" /><circle cx="4" cy="18" r="1" /></svg>
);
export const ClockIcon = (p: IconProps) => (
  <svg {...I(p)}><circle cx="12" cy="12" r="9" /><polyline points="12 7 12 12 15 14" /></svg>
);
export const ShieldIcon = (p: IconProps) => (
  <svg {...I(p)}><path d="M12 3l8 3v6c0 5-3.5 8.5-8 9-4.5-.5-8-4-8-9V6l8-3z" /></svg>
);
export const SettingsIcon = (p: IconProps) => (
  <svg {...I(p)}><circle cx="12" cy="12" r="3" /><path d="M19.4 15a1.7 1.7 0 0 0 .3 1.8l.1.1a2 2 0 1 1-2.8 2.8l-.1-.1a1.7 1.7 0 0 0-1.8-.3 1.7 1.7 0 0 0-1 1.5V21a2 2 0 0 1-4 0v-.1a1.7 1.7 0 0 0-1.1-1.5 1.7 1.7 0 0 0-1.8.3l-.1.1A2 2 0 1 1 4.3 17l.1-.1a1.7 1.7 0 0 0 .3-1.8 1.7 1.7 0 0 0-1.5-1H3a2 2 0 0 1 0-4h.1a1.7 1.7 0 0 0 1.5-1.1 1.7 1.7 0 0 0-.3-1.8l-.1-.1A2 2 0 1 1 7 4.3l.1.1a1.7 1.7 0 0 0 1.8.3H9a1.7 1.7 0 0 0 1-1.5V3a2 2 0 0 1 4 0v.1a1.7 1.7 0 0 0 1 1.5 1.7 1.7 0 0 0 1.8-.3l.1-.1A2 2 0 1 1 19.7 7l-.1.1a1.7 1.7 0 0 0-.3 1.8V9a1.7 1.7 0 0 0 1.5 1H21a2 2 0 0 1 0 4h-.1a1.7 1.7 0 0 0-1.5 1z" /></svg>
);
export const KeyIcon = (p: IconProps) => (
  <svg {...I(p)}><circle cx="8" cy="15" r="3" /><line x1="10.1" y1="12.9" x2="20" y2="3" /><line x1="17" y1="6" x2="20" y2="9" /><line x1="14" y1="9" x2="17" y2="12" /></svg>
);
export const PlayIcon = (p: IconProps) => (
  <svg {...I(p)}><polygon points="6 4 20 12 6 20 6 4" /></svg>
);
export const RefreshIcon = (p: IconProps) => (
  <svg {...I(p)}><path d="M21 12a9 9 0 0 0-15.3-6.4L3 8" /><polyline points="3 3 3 8 8 8" /><path d="M3 12a9 9 0 0 0 15.3 6.4L21 16" /><polyline points="21 21 21 16 16 16" /></svg>
);
export const XIcon = (p: IconProps) => (
  <svg {...I(p)}><line x1="6" y1="6" x2="18" y2="18" /><line x1="6" y1="18" x2="18" y2="6" /></svg>
);
export const AlertIcon = (p: IconProps) => (
  <svg {...I(p)}><path d="M10.3 3.9 1.8 18a2 2 0 0 0 1.7 3h17a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0z" /><line x1="12" y1="9" x2="12" y2="13" /><line x1="12" y1="17" x2="12" y2="17" /></svg>
);
export const CheckIcon = (p: IconProps) => (
  <svg {...I(p)}><polyline points="20 6 9 17 4 12" /></svg>
);
export const InboxIcon = (p: IconProps) => (
  <svg {...I(p)}><polyline points="22 12 16 12 14 15 10 15 8 12 2 12" /><path d="M5.4 5.4 2 12v6a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2v-6l-3.4-6.6A2 2 0 0 0 16.8 4H7.2a2 2 0 0 0-1.8 1.4z" /></svg>
);
export const HistoryIcon = (p: IconProps) => (
  <svg {...I(p)}><path d="M3 12a9 9 0 1 0 3-6.7L3 8" /><polyline points="3 3 3 8 8 8" /><polyline points="12 7 12 12 15 14" /></svg>
);
export const LogOutIcon = (p: IconProps) => (
  <svg {...I(p)}><path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" /><polyline points="16 17 21 12 16 7" /><line x1="21" y1="12" x2="9" y2="12" /></svg>
);
export const UserIcon = (p: IconProps) => (
  <svg {...I(p)}><circle cx="12" cy="8" r="4" /><path d="M4 21a8 8 0 0 1 16 0" /></svg>
);
export const PowerIcon = (p: IconProps) => (
  <svg {...I(p)}><path d="M18.4 6.6a9 9 0 1 1-12.8 0" /><line x1="12" y1="2" x2="12" y2="12" /></svg>
);
