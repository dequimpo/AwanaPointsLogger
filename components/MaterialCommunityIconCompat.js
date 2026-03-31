import React from 'react';
import { SvgXml } from 'react-native-svg';

// Font loading is not required for SVG-based icons.
export const materialCommunityIconFont = {};

function iconSvg(name, color, strokeWidth) {
  const c = color;
  const w = strokeWidth;

  const icons = {
    microsoft: `<rect x="2" y="2" width="9" height="9" fill="${c}"/><rect x="13" y="2" width="9" height="9" fill="${c}"/><rect x="2" y="13" width="9" height="9" fill="${c}"/><rect x="13" y="13" width="9" height="9" fill="${c}"/>`,
    'shield-check': `<path d="M12 2l7 3v6c0 5-3.5 8.5-7 10-3.5-1.5-7-5-7-10V5l7-3z" fill="none" stroke="${c}" stroke-width="${w}" stroke-linecap="round" stroke-linejoin="round"/><path d="M8 12l2.5 2.5L16 9" fill="none" stroke="${c}" stroke-width="${w}" stroke-linecap="round" stroke-linejoin="round"/>`,
    'cloud-sync': `<path d="M7 18a4 4 0 1 1 .8-7.9A5 5 0 0 1 17.5 9a3.5 3.5 0 1 1 .5 7H7z" fill="none" stroke="${c}" stroke-width="${w}" stroke-linecap="round" stroke-linejoin="round"/><path d="M9 14a3 3 0 0 1 5-2" fill="none" stroke="${c}" stroke-width="${w}" stroke-linecap="round"/><path d="M14 10v2h-2" fill="none" stroke="${c}" stroke-width="${w}" stroke-linecap="round"/><path d="M15 14a3 3 0 0 1-5 2" fill="none" stroke="${c}" stroke-width="${w}" stroke-linecap="round"/><path d="M10 18v-2h2" fill="none" stroke="${c}" stroke-width="${w}" stroke-linecap="round"/>`,
    lock: `<rect x="5" y="11" width="14" height="10" rx="2" fill="none" stroke="${c}" stroke-width="${w}"/><path d="M8 11V8a4 4 0 1 1 8 0v3" fill="none" stroke="${c}" stroke-width="${w}" stroke-linecap="round"/>`,
    'alert-circle': `<circle cx="12" cy="12" r="9" fill="none" stroke="${c}" stroke-width="${w}"/><path d="M12 7v6" fill="none" stroke="${c}" stroke-width="${w}" stroke-linecap="round"/><circle cx="12" cy="16.5" r="0.9" fill="${c}"/>`,
    'help-circle-outline': `<circle cx="12" cy="12" r="9" fill="none" stroke="${c}" stroke-width="${w}"/><path d="M9.7 9.2a2.8 2.8 0 1 1 4.6 2.2c-.8.7-1.6 1.2-1.6 2.1" fill="none" stroke="${c}" stroke-width="${w}" stroke-linecap="round"/><circle cx="12" cy="17" r="0.9" fill="${c}"/>`,
    scoreboard: `<rect x="3" y="5" width="18" height="14" rx="2" fill="none" stroke="${c}" stroke-width="${w}"/><path d="M7 15v-3M12 15V9M17 15v-5" fill="none" stroke="${c}" stroke-width="${w}" stroke-linecap="round"/>`,
    logout: `<path d="M10 4H6a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h4" fill="none" stroke="${c}" stroke-width="${w}" stroke-linecap="round"/><path d="M14 8l4 4-4 4" fill="none" stroke="${c}" stroke-width="${w}" stroke-linecap="round" stroke-linejoin="round"/><path d="M18 12H9" fill="none" stroke="${c}" stroke-width="${w}" stroke-linecap="round"/>`,
    'arrow-left': `<path d="M15 6l-6 6 6 6" fill="none" stroke="${c}" stroke-width="${w}" stroke-linecap="round" stroke-linejoin="round"/>`,
    'arrow-right': `<path d="M9 6l6 6-6 6" fill="none" stroke="${c}" stroke-width="${w}" stroke-linecap="round" stroke-linejoin="round"/>`,
    calendar: `<rect x="3" y="5" width="18" height="16" rx="2" fill="none" stroke="${c}" stroke-width="${w}"/><path d="M8 3v4M16 3v4M3 9h18" fill="none" stroke="${c}" stroke-width="${w}" stroke-linecap="round"/>`,
    'chart-box': `<rect x="3" y="3" width="18" height="18" rx="2" fill="none" stroke="${c}" stroke-width="${w}"/><path d="M7 16v-4M12 16V8M17 16v-6" fill="none" stroke="${c}" stroke-width="${w}" stroke-linecap="round"/>`,
    'inbox-multiple': `<rect x="4" y="5" width="16" height="12" rx="2" fill="none" stroke="${c}" stroke-width="${w}"/><path d="M4 12h5l2 3h2l2-3h5" fill="none" stroke="${c}" stroke-width="${w}" stroke-linecap="round" stroke-linejoin="round"/>`,
    'heart-outline': `<path d="M12 20s-7-4.4-7-10a4 4 0 0 1 7-2 4 4 0 0 1 7 2c0 5.6-7 10-7 10z" fill="none" stroke="${c}" stroke-width="${w}" stroke-linecap="round" stroke-linejoin="round"/>`,
    'human-male': `<circle cx="12" cy="8" r="3" fill="none" stroke="${c}" stroke-width="${w}"/><path d="M8 21v-5a4 4 0 0 1 8 0v5" fill="none" stroke="${c}" stroke-width="${w}" stroke-linecap="round"/>`,
    'human-female': `<circle cx="12" cy="8" r="3" fill="none" stroke="${c}" stroke-width="${w}"/><path d="M8 21v-5a4 4 0 0 1 8 0v5" fill="none" stroke="${c}" stroke-width="${w}" stroke-linecap="round"/>`,
    hiking: `<circle cx="14" cy="5" r="2" fill="none" stroke="${c}" stroke-width="${w}"/><path d="M8 13l4-3 2 2 3 1" fill="none" stroke="${c}" stroke-width="${w}" stroke-linecap="round"/><path d="M10 12l-2 8M14 12l2 8M6 21h4M16 21h4" fill="none" stroke="${c}" stroke-width="${w}" stroke-linecap="round"/>`,
    'book-open-variant': `<path d="M4 6a3 3 0 0 1 3-3h5v16H7a3 3 0 0 0-3 3z" fill="none" stroke="${c}" stroke-width="${w}"/><path d="M20 6a3 3 0 0 0-3-3h-5v16h5a3 3 0 0 1 3 3z" fill="none" stroke="${c}" stroke-width="${w}"/>`,
    paw: `<circle cx="8" cy="9" r="2" fill="none" stroke="${c}" stroke-width="${w}"/><circle cx="12" cy="7" r="2" fill="none" stroke="${c}" stroke-width="${w}"/><circle cx="16" cy="9" r="2" fill="none" stroke="${c}" stroke-width="${w}"/><path d="M8 16c0-2.5 2-4 4-4s4 1.5 4 4-2 3-4 3-4-.5-4-3z" fill="none" stroke="${c}" stroke-width="${w}"/>`,
    'cloud-check': `<path d="M7 18a4 4 0 1 1 .8-7.9A5 5 0 0 1 17.5 9a3.5 3.5 0 1 1 .5 7H7z" fill="none" stroke="${c}" stroke-width="${w}"/><path d="M9 14l2 2 4-4" fill="none" stroke="${c}" stroke-width="${w}" stroke-linecap="round" stroke-linejoin="round"/>`,
    'cloud-alert': `<path d="M7 18a4 4 0 1 1 .8-7.9A5 5 0 0 1 17.5 9a3.5 3.5 0 1 1 .5 7H7z" fill="none" stroke="${c}" stroke-width="${w}"/><path d="M12 10v4" fill="none" stroke="${c}" stroke-width="${w}" stroke-linecap="round"/><circle cx="12" cy="16.2" r="0.9" fill="${c}"/>`,
    'cloud-question': `<path d="M7 18a4 4 0 1 1 .8-7.9A5 5 0 0 1 17.5 9a3.5 3.5 0 1 1 .5 7H7z" fill="none" stroke="${c}" stroke-width="${w}"/><path d="M10.5 12a1.5 1.5 0 1 1 2.8.8c-.6.5-1.1.8-1.1 1.6" fill="none" stroke="${c}" stroke-width="${w}" stroke-linecap="round"/><circle cx="12" cy="16.3" r="0.8" fill="${c}"/>`,
  };

  return icons[name] || `<circle cx="12" cy="12" r="8" fill="none" stroke="${c}" stroke-width="${w}"/>`;
}

export default function MaterialCommunityIconCompat({
  name,
  size = 24,
  color = '#000',
  style,
}) {
  const strokeWidth = Math.max(1.6, Math.round(size / 12));
  const xml = `
    <svg xmlns="http://www.w3.org/2000/svg" width="${size}" height="${size}" viewBox="0 0 24 24">
      ${iconSvg(name, color, strokeWidth)}
    </svg>
  `;

  return <SvgXml xml={xml} width={size} height={size} style={style} />;
}
