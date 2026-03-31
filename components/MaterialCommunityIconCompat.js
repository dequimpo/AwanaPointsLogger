import React from 'react';
import { Text } from 'react-native';

/**
 * Font-free icon component.
 *
 * WHY: @expo/vector-icons on Expo 49 web injects @font-face CSS and reports
 * "loaded" before Safari has actually applied the font, causing squares.
 * This component avoids any webfont dependency by rendering OS-native emoji
 * (for decorative icons) and plain Unicode symbols (for icons that must respond
 * to the `color` prop, e.g. navigation arrows that appear in white on dark
 * buttons). Both emoji and Unicode are rendered by the device's built-in system
 * font — they can never show as squares.
 *
 * ADDING NEW ICONS: add an entry to ICON_MAP below.
 * - Use a plain Unicode character when the `color` prop matters.
 * - Use an emoji when the icon is decorative and an exact color match is not
 *   required (note: emoji do not inherit the `color` prop).
 */

// Empty — no webfont loading needed. useFonts({}) resolves immediately.
export const materialCommunityIconFont = {};

// ─── Color-responsive (plain Unicode) ────────────────────────────────────────
// These are single-codepoint characters rendered by the system body font; they
// faithfully inherit the `color` style passed by the caller.
//
// ─── Decorative (emoji) ───────────────────────────────────────────────────────
// These are color emoji rendered by the OS emoji font; they look great and are
// recognisable, but they do not change color based on the `color` prop.

const ICON_MAP = {
  // Navigation — color-responsive (white arrows on dark buttons, etc.)
  'arrow-left':          '←',   // U+2190
  'arrow-right':         '→',   // U+2192
  'logout':              '↩',   // U+21A9  exit / return

  // Status / inline — color-responsive
  'alert-circle':        '⚠',   // U+26A0
  'information-outline': 'ⓘ',   // U+24D8
  'checkbox-marked-outline': '☑', // U+2611
  'cloud-check-outline': '✓',   // U+2713
  'heart-outline':       '♡',   // U+2661
  'numeric-1-circle':    '①',   // U+2460
  'numeric-2-circle':    '②',   // U+2461
  'numeric-3-circle':    '③',   // U+2463
  'cross':               '✝',   // U+271D  Christian cross (Awana)
  'help-circle-outline': '❓',  // U+2753 (emoji, but also works as fallback)

  // Decorative — emoji (iOS 13+ / all supported devices)
  'calendar':            '📅',
  'chart-box':           '📊',
  'cloud-sync':          '🔄',
  'inbox-multiple':      '📥',
  'lightbulb-outline':   '💡',
  'lock':                '🔒',
  'microsoft':           '🪟',  // Windows / Microsoft (iOS 15+)
  'scoreboard':          '🏆',
  'shield-check':        '✅',
  'human-male':          '👦',
  'human-female':        '👧',
  'hiking':              '⛰️',
  'book-open-variant':   '📘',
  'paw':                 '🐾',
};

export default function MaterialCommunityIconCompat({
  name,
  size = 24,
  color = '#333',
  style,
}) {
  const symbol = ICON_MAP[name] ?? 'ⓘ';
  return (
    <Text
      style={[
        {
          fontSize: size * 0.95,
          lineHeight: size * 1.2,
          color,
          textAlign: 'center',
          includeFontPadding: false,
        },
        style,
      ]}
      selectable={false}
    >
      {symbol}
    </Text>
  );
}
