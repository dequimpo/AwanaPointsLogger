import React from 'react';
import { Text } from 'react-native';

// Font-free fallback icons to avoid web font loading issues on iPhone Safari.
export const materialCommunityIconFont = {};

const ICON_SYMBOLS = {
  microsoft: 'M',
  'shield-check': 'S',
  'cloud-sync': 'C',
  lock: 'L',
  'alert-circle': '!',
  'help-circle-outline': '?',
  scoreboard: '#',
  logout: '<',
  'arrow-left': '<',
  'arrow-right': '>',
  calendar: 'D',
  'chart-box': 'B',
  'inbox-multiple': 'I',
  'heart-outline': 'H',
  'human-male': 'M',
  'human-female': 'F',
  hiking: 'T',
  'book-open-variant': 'K',
  paw: 'P',
  'cloud-check': 'OK',
  'cloud-alert': '!',
  'cloud-question': '?',
  'information-outline': 'i',
  'numeric-1-circle': '1',
  'numeric-2-circle': '2',
  'numeric-3-circle': '3',
  'checkbox-marked-outline': 'V',
  'cloud-check-outline': 'OK',
  'lightbulb-outline': '*',
  cross: '+',
  account: 'U',
};

export default function MaterialCommunityIconCompat({
  name,
  size = 24,
  color = '#000',
  style,
}) {
  const symbol = ICON_SYMBOLS[name] || '?';

  return (
    <Text
      style={[
        {
          fontSize: size,
          lineHeight: size,
          color,
          fontWeight: '700',
          textAlign: 'center',
        },
        style,
      ]}
      accessibilityRole="image"
      accessible
    >
      {symbol}
    </Text>
  );
}
