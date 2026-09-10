import React from 'react';

import {drawStrokeProps} from '../utils/animation';
import type {Rect} from '../utils/layout';

export const DrawBox: React.FC<{
  rect: Rect;
  progress: number;
  color: string;
}> = ({rect, progress, color}) => (
  <svg
    width={rect.w + 36}
    height={rect.h + 36}
    style={{position: 'absolute', left: rect.x - 18, top: rect.y - 18, pointerEvents: 'none'}}
  >
    <rect
      x={18}
      y={18}
      width={rect.w}
      height={rect.h}
      rx={18}
      fill="none"
      stroke={color}
      strokeWidth={7}
      {...drawStrokeProps(progress)}
    />
  </svg>
);
