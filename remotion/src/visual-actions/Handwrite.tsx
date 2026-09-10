import React from 'react';

import type {Rect} from '../utils/layout';

export const Handwrite: React.FC<{
  rect: Rect;
  text: string;
  progress: number;
  color: string;
}> = ({rect, text, progress, color}) => (
  <div
    style={{
      position: 'absolute',
      left: rect.x,
      top: rect.y,
      width: rect.w,
      height: rect.h,
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      fontFamily: "'Segoe Script', 'Comic Sans MS', cursive",
      fontSize: 34,
      fontWeight: 700,
      color,
      clipPath: `inset(0 ${100 - progress * 100}% 0 0)`,
      pointerEvents: 'none',
    }}
  >
    {text}
  </div>
);
