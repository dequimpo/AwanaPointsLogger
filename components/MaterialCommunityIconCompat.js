import React from 'react';
import { MaterialCommunityIcons } from '@expo/vector-icons';

export const materialCommunityIconFont = MaterialCommunityIcons.font || {};

const ICON_NAME_MAP = {
  scoreboard: 'scoreboard-outline',
  cross: 'crosshairs',
};

export default function MaterialCommunityIconCompat(props) {
  const mappedName = ICON_NAME_MAP[props.name] || props.name || 'help-circle-outline';
  return <MaterialCommunityIcons {...props} name={mappedName} />;
}
