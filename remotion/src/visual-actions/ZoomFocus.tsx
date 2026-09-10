import React from 'react';

import type {Rect} from '../utils/layout';

export const ZoomFocus: React.FC<{
  rect: Rect;
  progress: number;
}> = ({rect, progress}) => {
  const cx = rect.x + rect.w / 2;
  const cy = rect.y + rect.h / 2;
  const radius = Math.max(320, rect.w) * (1.25 - 0.2 * progress);
  return (
    <div
      style={{
        position: 'absolute',
        inset: 0,
        background: `radial-gradient(circle at ${cx}px ${cy}px, transparent ${radius}px, rgba(17,17,17,0.42) ${radius + 90}px)`,
        pointerEvents: 'none',
      }}
    />
  );
};
