import React from 'react';

import type {Rect} from '../utils/layout';

export const Highlight: React.FC<{
  rect: Rect;
  progress: number;
  color: string;
}> = ({rect, progress, color}) => {
  const opacity = Math.sin(Math.min(1, Math.max(0, progress)) * Math.PI) * 0.38;
  return (
    <div
      style={{
        position: 'absolute',
        left: rect.x - 10,
        top: rect.y - 6,
        width: rect.w + 20,
        height: rect.h + 12,
        borderRadius: 12,
        backgroundColor: color,
        opacity,
        pointerEvents: 'none',
      }}
    />
  );
};
