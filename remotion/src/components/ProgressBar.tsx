import React from 'react';

import type {Theme} from '../theme';

export const ProgressBar: React.FC<{
  frame: number;
  totalFrames: number;
  theme: Theme;
}> = ({frame, totalFrames, theme}) => {
  const progress = totalFrames > 0 ? Math.min(1, frame / totalFrames) : 0;
  return (
    <div
      style={{
        position: 'absolute',
        bottom: 0,
        left: 0,
        right: 0,
        height: 8,
        backgroundColor: 'rgba(17,17,17,0.08)',
      }}
    >
      <div
        style={{
          height: '100%',
          width: `${progress * 100}%`,
          backgroundColor: theme.accent,
        }}
      />
    </div>
  );
};
