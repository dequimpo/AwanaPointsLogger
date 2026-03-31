import React from 'react';
import { Platform, Text } from 'react-native';
import MaterialCommunityIconsActual from '@expo/vector-icons/MaterialCommunityIcons';

export const materialCommunityIconFont = MaterialCommunityIconsActual.font;

const WEB_ICON_FALLBACKS = {
  microsoft: '[M]',
  'shield-check': '[S]',
  'cloud-sync': '[C]',
  lock: '[L]',
  'alert-circle': '[!]',
  'help-circle-outline': '[?]',
  scoreboard: '[#]',
  logout: '[>]',
  'arrow-left': '<',
  'arrow-right': '>',
  calendar: '[D]',
  'chart-box': '[=]',
  'inbox-multiple': '[I]',
  'heart-outline': '[H]',
  'human-male': '[B]',
  'human-female': '[G]',
  hiking: '[T]',
  'book-open-variant': '[R]',
  paw: '[P]',
  'cloud-check': '[OK]',
  'cloud-alert': '[!]',
  'cloud-question': '[?]',
};

export default function MaterialCommunityIconCompat({
  name,
  size = 24,
  color = '#000',
  style,
  ...rest
}) {
  if (Platform.OS === 'web') {
    const fallback = WEB_ICON_FALLBACKS[name] || '[*]';
    return (
      <Text
        accessibilityLabel={typeof name === 'string' ? name : 'icon'}
        style={[
          {
            fontSize: Math.max(10, Math.round(size * 0.6)),
            color,
            lineHeight: size,
            textAlign: 'center',
            fontWeight: '700',
          },
          style,
        ]}
      >
        {fallback}
      </Text>
    );
  }

  return <MaterialCommunityIconsActual name={name} size={size} color={color} style={style} {...rest} />;
}
