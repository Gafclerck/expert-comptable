import type { SVGProps } from 'react';

export type IconName = 'grid' | 'shield' | 'package' | 'car' | 'arrows' | 'circle' | 'repeat' | 'wallet' | 'clock' | 'users' | 'bell' | 'sparkles' | 'chart' | 'file' | 'user-plus' | 'list' | 'settings' | 'chevron-left' | 'chevron-right' | 'search' | 'menu' | 'x' | 'chevron-down' | 'arrow-up-right';

interface IconProps extends SVGProps<SVGSVGElement> { name: IconName; size?: number; }

const paths: Record<IconName, React.ReactNode> = {
  grid: <><rect x="3" y="3" width="7" height="7" rx="1" /><rect x="14" y="3" width="7" height="7" rx="1" /><rect x="3" y="14" width="7" height="7" rx="1" /><rect x="14" y="14" width="7" height="7" rx="1" /></>,
  shield: <path d="M12 3 4.8 6.2v5c0 4.6 3 7.7 7.2 9.8 4.2-2.1 7.2-5.2 7.2-9.8v-5L12 3Z" />,
  package: <><path d="m3.5 7.5 8.5-4 8.5 4-8.5 4-8.5-4Z" /><path d="M3.5 7.5V17l8.5 4.5 8.5-4.5V7.5M12 11.5V21" /></>,
  car: <><path d="m5 16-1 0v-4.5l2-5h12l2 5V16h-1" /><path d="M6 16h12M7 16v2M17 16v2M4 12h16M7 6.5l1 5M17 6.5l-1 5" /></>,
  arrows: <><path d="M7 3v14M3.5 6.5 7 3l3.5 3.5M17 21V7M13.5 17.5 17 21l3.5-3.5" /></>,
  circle: <circle cx="12" cy="12" r="8.5" />,
  repeat: <><path d="M17 3.5 20.5 7 17 10.5" /><path d="M3.5 7h17M7 20.5 3.5 17 7 13.5" /><path d="M20.5 17h-17" /></>,
  wallet: <><path d="M4 6.5A2.5 2.5 0 0 1 6.5 4H19v16H6.5A2.5 2.5 0 0 1 4 17.5v-11Z" /><path d="M4 7h15M15 13h4" /></>,
  clock: <><circle cx="12" cy="12" r="8.5" /><path d="M12 7v5l3.5 2" /></>,
  users: <><path d="M16.5 20v-1.5a4.5 4.5 0 0 0-4.5-4.5h-4a4.5 4.5 0 0 0-4.5 4.5V20" /><circle cx="10" cy="7.5" r="3.5" /><path d="M17 10a3 3 0 0 0 0-5.5M20.5 20v-1.5a4.5 4.5 0 0 0-2.5-4" /></>,
  bell: <><path d="M18 9a6 6 0 0 0-12 0c0 7-3 8-3 8h18s-3-1-3-8M10 21h4" /></>,
  sparkles: <><path d="m12 3 1.2 4.2L17.5 8.5l-4.3 1.3L12 14l-1.2-4.2-4.3-1.3 4.3-1.3L12 3ZM19 15l.6 2.4L22 18l-2.4.6L19 21l-.6-2.4L16 18l2.4-.6L19 15Z" /></>,
  chart: <><path d="M4 20V10M10 20V4M16 20v-7M22 20H2" /></>,
  file: <><path d="M6 3h8l4 4v14H6z" /><path d="M14 3v5h5M9 13h6M9 17h6" /></>,
  'user-plus': <><circle cx="9" cy="8" r="3.5" /><path d="M2.5 20v-1.5A4.5 4.5 0 0 1 7 14h4a4.5 4.5 0 0 1 4.5 4.5V20M18 8v6M15 11h6" /></>,
  list: <><path d="M8 6h12M8 12h12M8 18h12" /><path d="M4 6h.01M4 12h.01M4 18h.01" /></>,
  settings: <><circle cx="12" cy="12" r="3" /><path d="M19.4 15a1.7 1.7 0 0 0 .34 1.88l.05.05-2.1 2.1-.05-.05a1.7 1.7 0 0 0-1.88-.34 1.7 1.7 0 0 0-1.03 1.56v.08h-3v-.08a1.7 1.7 0 0 0-1.03-1.56 1.7 1.7 0 0 0-1.88.34l-.05.05-2.1-2.1.05-.05A1.7 1.7 0 0 0 7.02 15 1.7 1.7 0 0 0 5.46 14H5.4v-3h.07a1.7 1.7 0 0 0 1.55-1.03 1.7 1.7 0 0 0-.34-1.88l-.05-.05 2.1-2.1.05.05a1.7 1.7 0 0 0 1.88.34A1.7 1.7 0 0 0 11.7 4.8v-.08h3v.08a1.7 1.7 0 0 0 1.03 1.56 1.7 1.7 0 0 0 1.88-.34l.05-.05 2.1 2.1-.05.05a1.7 1.7 0 0 0-.34 1.88A1.7 1.7 0 0 0 20.94 11H21v3h-.07A1.7 1.7 0 0 0 19.4 15Z" /></>,
  'chevron-left': <path d="m14.5 5-7 7 7 7" />, 'chevron-right': <path d="m9.5 5 7 7-7 7" />, search: <><circle cx="10.8" cy="10.8" r="6.3" /><path d="m16 16 4.5 4.5" /></>, menu: <path d="M4 7h16M4 12h16M4 17h16" />, x: <path d="m6 6 12 12M18 6 6 18" />, 'chevron-down': <path d="m6 9 6 6 6-6" />, 'arrow-up-right': <><path d="M7 17 17 7M9 7h8v8" /></>,
};

export default function Icon({ name, size = 18, ...props }: IconProps) { return <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" {...props}>{paths[name]}</svg>; }
