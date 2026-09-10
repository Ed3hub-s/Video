import React from 'react';
import {interpolate} from 'remotion';

import type {Theme} from '../theme';
import type {SubtitleVariant} from '../styles';
import type {SubtitleCue} from '../types';

export const Subtitle: React.FC<{
  cue: SubtitleCue | undefined;
  frame: number;
  fps: number;
  theme: Theme;
  variant?: SubtitleVariant;
}> = ({cue, frame, fps, theme, variant = 'pill'}) => {
  if (!cue) {
    return null;
  }
  const start = cue.start * fps;
  const end = cue.end * fps;
  const fadeFrames = Math.min(8, Math.max(1, (end - start) / 3));
  const opacity = interpolate(
    frame,
    [start, start + fadeFrames, end - fadeFrames, end],
    [0, 1, 1, 0],
    {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
    },
  );
  const bar = variant === 'bar';
  return (
    <div
      style={{
        position: 'absolute',
        bottom: bar ? 96 : 110,
        left: 0,
        right: 0,
        display: 'flex',
        justifyContent: 'center',
        opacity,
        pointerEvents: 'none',
      }}
    >
      <div
        style={{
          backgroundColor: bar ? 'rgba(0,0,0,0.82)' : 'rgba(17,17,17,0.88)',
          color: '#FFFFFF',
          fontSize: theme.subtitleSize,
          lineHeight: 1.3,
          padding: '14px 34px',
          borderRadius: bar ? 0 : 14,
          maxWidth: bar ? '100%' : 1450,
          width: bar ? '100%' : undefined,
          textAlign: 'center',
          borderLeft: bar ? `6px solid ${theme.accent}` : undefined,
        }}
      >
        {cue.text}
      </div>
    </div>
  );
};
