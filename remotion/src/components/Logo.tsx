import React from 'react';

import type {Theme} from '../theme';

export const Logo: React.FC<{theme: Theme; courseTitle: string}> = ({
  theme,
  courseTitle,
}) => (
  <div
    style={{
      position: 'absolute',
      top: theme.safeMarginY - 24,
      left: theme.safeMarginX,
      display: 'flex',
      alignItems: 'center',
      gap: 14,
    }}
  >
    <div
      style={{
        width: 34,
        height: 34,
        borderRadius: 10,
        backgroundColor: theme.accent,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        color: '#FFFFFF',
        fontWeight: 800,
        fontSize: 18,
      }}
    >
      {'▶'}
    </div>
    <span style={{color: theme.muted, fontSize: 22, fontWeight: 600}}>
      {courseTitle}
    </span>
  </div>
);
