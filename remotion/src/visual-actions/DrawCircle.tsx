import React from 'react';

import {drawStrokeProps} from '../utils/animation';
import type {Rect} from '../utils/layout';

export const DrawCircle: React.FC<{
  rect: Rect;
  progress: number;
  color: string;
}> = ({rect, progress, color}) => {
  const cx = rect.w / 2;
  const cy = rect.h / 2;
  const rx = rect.w / 2 + 18;
  const ry = rect.h / 2 + 18;
  return (
    <svg
      width={rect.w + 52}
      height={rect.h + 52}
      style={{position: 'absolute', left: rect.x - 26, top: rect.y - 26, pointerEvents: 'none'}}
    >
      <ellipse
        cx={cx + 26}
        cy={cy + 26}
        rx={rx}
        ry={ry}
        fill="none"
        stroke={color}
        strokeWidth={7}
        {...drawStrokeProps(progress)}
      />
    </svg>
  );
};
