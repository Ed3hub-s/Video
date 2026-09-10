import React from 'react';

import {drawStrokeProps} from '../utils/animation';
import type {Point, Rect} from '../utils/layout';

const center = (rect: Rect): Point => ({x: rect.x + rect.w / 2, y: rect.y + rect.h / 2});

export const DrawArrow: React.FC<{
  fromRect: Rect;
  toRect: Rect;
  progress: number;
  color: string;
}> = ({fromRect, toRect, progress, color}) => {
  const from = center(fromRect);
  const to = center(toRect);
  const dx = to.x - from.x;
  const dy = to.y - from.y;
  const length = Math.sqrt(dx * dx + dy * dy) || 1;
  const head = 26;
  const angle = Math.atan2(dy, dx);
  const endX = from.x + dx * (0.84 + 0.16 * progress);
  const endY = from.y + dy * (0.84 + 0.16 * progress);
  const tipX = from.x + (length - head) * (dx / length);
  const tipY = from.y + (length - head) * (dy / length);
  return (
    <svg
      width={Math.abs(dx) + 80}
      height={Math.abs(dy) + 80}
      style={{
        position: 'absolute',
        left: Math.min(from.x, to.x) - 40,
        top: Math.min(from.y, to.y) - 40,
        pointerEvents: 'none',
        overflow: 'visible',
      }}
    >
      <line
        x1={from.x - Math.min(from.x, to.x) + 40}
        y1={from.y - Math.min(from.y, to.y) + 40}
        x2={endX - Math.min(from.x, to.x) + 40}
        y2={endY - Math.min(from.y, to.y) + 40}
        stroke={color}
        strokeWidth={8}
        strokeLinecap="round"
        {...drawStrokeProps(progress)}
      />
      <polygon
        points={`${tipX},${tipY} ${tipX - head * Math.cos(angle - 0.45)},${
          tipY - head * Math.sin(angle - 0.45)
        } ${tipX - head * Math.cos(angle + 0.45)},${tipY - head * Math.sin(angle + 0.45)}`}
        fill={color}
        opacity={Math.min(1, Math.max(0, (progress - 0.8) * 5))}
      />
    </svg>
  );
};
