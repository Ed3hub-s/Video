import React from 'react';

import {drawStrokeProps} from '../utils/animation';
import type {Rect} from '../utils/layout';

export const Connect: React.FC<{
  fromRect: Rect;
  toRect: Rect;
  progress: number;
  color: string;
}> = ({fromRect, toRect, progress, color}) => {
  const from = {x: fromRect.x + fromRect.w / 2, y: fromRect.y + fromRect.h / 2};
  const to = {x: toRect.x + toRect.w / 2, y: toRect.y + toRect.h / 2};
  return (
    <svg
      width={Math.abs(to.x - from.x) + 40}
      height={Math.abs(to.y - from.y) + 40}
      style={{
        position: 'absolute',
        left: Math.min(from.x, to.x) - 20,
        top: Math.min(from.y, to.y) - 20,
        pointerEvents: 'none',
        overflow: 'visible',
      }}
    >
      <line
        x1={from.x - Math.min(from.x, to.x) + 20}
        y1={from.y - Math.min(from.y, to.y) + 20}
        x2={to.x - Math.min(from.x, to.x) + 20}
        y2={to.y - Math.min(from.y, to.y) + 20}
        stroke={color}
        strokeWidth={7}
        strokeLinecap="round"
        {...drawStrokeProps(progress)}
      />
    </svg>
  );
};
