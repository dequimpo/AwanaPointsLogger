import React from 'react';
import { MaterialCommunityIcons } from '@expo/vector-icons';

// Export the actual font map so App.js can preload it via useFonts.
// This ensures the icon font is fully loaded before any icons render.
export const materialCommunityIconFont = MaterialCommunityIcons.font;

// Some icon names are unavailable in the bundled glyph map; remap them.
const ICON_NAME_MAP = {
  scoreboard: 'scoreboard-outline',
  cross: 'crosshairs',
};

// Guaranteed-present safe fallback icon name.
const SAFE_FALLBACK = 'help-circle-outline';
const glyphMap = MaterialCommunityIcons.glyphMap || {};

export default function MaterialCommunityIconCompat({ name, ...rest }) {
  const mapped = ICON_NAME_MAP[name] || name;
  const safeName = glyphMap[mapped] ? mapped : SAFE_FALLBACK;
  return <MaterialCommunityIcons name={safeName} {...rest} />;
}
