import React from 'react';

import {drawStrokeProps} from '../utils/animation';
import type {Rect} from '../utils/layout';

export const CrossOut: React.FC<{
  rect: Rect;
  progress: number;
  color: string;
}> = ({rect, progress, color}) => {
  const half = progress / 2;
  return (
    <svg
      width={rect.w + 40}
      height={rect.h + 40}
      style={{position: 'absolute', left: rect.x - 20, top: rect.y - 20, pointerEvents: 'none'}}
    >
      <path
        d={`M 0 0 L ${rect.w + 40} ${rect.h + 40}`}
        fill="none"
        stroke={color}
        strokeWidth={9}
        strokeLinecap="round"
        {...drawStrokeProps(Math.min(1, half * 2))}
      />
      <path
        d={`M ${rect.w + 40} 0 L 0 ${rect.h + 40}`}
        fill="none"
        stroke={color}
        strokeWidth={9}
        strokeLinecap="round"
        {...drawStrokeProps(Math.max(0, half * 2 - 1))}
      />
    </svg>
  );
};
