import React from 'react';

import {drawStrokeProps} from '../utils/animation';
import type {Rect} from '../utils/layout';

export const Underline: React.FC<{
  rect: Rect;
  progress: number;
  color: string;
}> = ({rect, progress, color}) => (
  <svg
    width={rect.w + 24}
    height={rect.h + 24}
    style={{position: 'absolute', left: rect.x - 12, top: rect.y - 12, pointerEvents: 'none'}}
  >
    <path
      d={`M 4 ${rect.h + 6} Q ${rect.w / 2} ${rect.h + 14}, ${rect.w + 16} ${rect.h + 6}`}
      fill="none"
      stroke={color}
      strokeWidth={7}
      strokeLinecap="round"
      {...drawStrokeProps(progress)}
    />
  </svg>
);
