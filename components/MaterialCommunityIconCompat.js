import React from 'react';
import { Platform, Text } from 'react-native';
import MaterialIcons from '@expo/vector-icons/MaterialIcons';

export const materialCommunityIconFont = MaterialIcons.font;

const ICON_NAME_MAP = {
  microsoft: 'apps',
  'shield-check': 'verified-user',
  'cloud-sync': 'sync',
  lock: 'lock',
  'alert-circle': 'error-outline',
  'help-circle-outline': 'help-outline',
  scoreboard: 'leaderboard',
  logout: 'logout',
  'arrow-left': 'arrow-back',
  'arrow-right': 'arrow-forward',
  calendar: 'calendar-today',
  'chart-box': 'bar-chart',
  'inbox-multiple': 'inbox',
  'heart-outline': 'favorite-border',
  'human-male': 'person',
  'human-female': 'person',
  hiking: 'terrain',
  'book-open-variant': 'menu-book',
  paw: 'pets',
  'cloud-check': 'cloud-done',
  'cloud-alert': 'cloud-off',
  'cloud-question': 'cloud-queue',
};

let webMaterialFontInjected = false;

function ensureWebMaterialFontLoaded() {
  if (Platform.OS !== 'web' || typeof document === 'undefined' || webMaterialFontInjected) {
    return;
  }

  const existing = document.getElementById('material-icons-webfont');
  if (existing) {
    webMaterialFontInjected = true;
    return;
  }

  const link = document.createElement('link');
  link.id = 'material-icons-webfont';
  link.rel = 'stylesheet';
  link.href = 'https://fonts.googleapis.com/icon?family=Material+Icons';
  document.head.appendChild(link);
  webMaterialFontInjected = true;
}

function resolveIconName(name) {
  if (!name || typeof name !== 'string') {
    return 'help-outline';
  }
  return ICON_NAME_MAP[name] || name;
}

export default function MaterialCommunityIconCompat({
  name,
  size = 24,
  color = '#000',
  style,
  ...rest
}) {
  const resolvedName = resolveIconName(name);

  if (Platform.OS === 'web') {
    ensureWebMaterialFontLoaded();

    // Render Material icon ligatures on web for consistent appearance.
    return (
      <Text
        accessibilityLabel={resolvedName}
        style={[
          {
            fontFamily: 'Material Icons',
            fontSize: size,
            color,
            lineHeight: size,
            textAlign: 'center',
            includeFontPadding: false,
          },
          style,
        ]}
      >
        {resolvedName.replace(/-/g, '_')}
      </Text>
    );
  }

  return <MaterialIcons name={resolvedName} size={size} color={color} style={style} {...rest} />;
}
