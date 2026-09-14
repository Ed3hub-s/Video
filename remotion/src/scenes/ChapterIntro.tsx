import React from 'react';
import {interpolate} from 'remotion';

import type {SceneProps} from './common';

export const ChapterIntro: React.FC<SceneProps> = ({
  scene,
  theme,
  frame,
}) => {
  const labelProgress = interpolate(
    frame,
    [0, 10],
    [0, 1],
    {
      extrapolateLeft: 'clamp',
      extrapolateRight: 'clamp',
    },
  );

  const titleProgress = interpolate(
    frame,
    [8, 24],
    [0, 1],
    {
      extrapolateLeft: 'clamp',
      extrapolateRight: 'clamp',
    },
  );

  const lineProgress = interpolate(
    frame,
    [16, 30],
    [0, 1],
    {
      extrapolateLeft: 'clamp',
      extrapolateRight: 'clamp',
    },
  );

  return (
    <div
      style={{
        width: '100%',
        height: '100%',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '0 180px',
        boxSizing: 'border-box',
      }}
    >
      <div
        style={{
          width: '100%',
          maxWidth: 1320,
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          textAlign: 'center',
        }}
      >
        <div
          style={{
            fontSize: 24,
            fontWeight: 800,
            letterSpacing: 6,
            color: theme.accent,
            marginBottom: 30,

            opacity: labelProgress,

            transform: `translateY(${
              (1 - labelProgress) * 12
            }px)`,
          }}
        >
          CHAPTER
        </div>

        <div
          style={{
            fontSize: Math.min(
              theme.titleSize,
              72,
            ),

            fontWeight: 800,
            color: theme.foreground,
            lineHeight: 1.12,
            letterSpacing: -1.2,

            opacity: titleProgress,

            transform: `translateY(${
              (1 - titleProgress) * 22
            }px)`,
          }}
        >
          {scene.screenText || scene.title}
        </div>

        <div
          style={{
            width: 110 * lineProgress,
            height: 6,
            borderRadius: 999,
            backgroundColor: theme.accent,
            marginTop: 38,

            opacity: lineProgress,
          }}
        />
      </div>
    </div>
  );
};