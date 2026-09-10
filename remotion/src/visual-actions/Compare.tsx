import React from 'react';

import type {Rect} from '../utils/layout';

export const Compare: React.FC<{
  leftRect: Rect;
  rightRect: Rect;
  leftText: string;
  rightText: string;
  progress: number;
  color: string;
}> = ({leftRect, rightRect, leftText, rightText, progress, color}) => {
  const x = leftRect.x + leftRect.w / 2 + (rightRect.x - leftRect.x) * progress;
  return (
    <div style={{position: 'absolute', inset: 0, pointerEvents: 'none'}}>
      <div
        style={{
          position: 'absolute',
          left: leftRect.x,
          top: leftRect.y,
          width: leftRect.w,
          height: leftRect.h,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          fontSize: 30,
          fontWeight: 800,
          color: 'rgba(17,17,17,0.55)',
          opacity: Math.min(1, progress * 2),
        }}
      >
        {leftText}
      </div>
      <div
        style={{
          position: 'absolute',
          left: rightRect.x,
          top: rightRect.y,
          width: rightRect.w,
          height: rightRect.h,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          fontSize: 30,
          fontWeight: 800,
          color: color,
          opacity: Math.min(1, Math.max(0, (progress - 0.5) * 2)),
        }}
      >
        {rightText}
      </div>
      <div
        style={{
          position: 'absolute',
          left: x,
          top: 0,
          bottom: 0,
          width: 6,
          backgroundColor: color,
          opacity: 0.8,
        }}
      />
    </div>
  );
};
