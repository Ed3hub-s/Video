import React from 'react';
import {interpolate} from 'remotion';

import type {SceneProps} from './common';

export const SectionIntro: React.FC<SceneProps> = ({
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
    [8, 22],
    [0, 1],
    {
      extrapolateLeft: 'clamp',
      extrapolateRight: 'clamp',
    },
  );

  const lineProgress = interpolate(
    frame,
    [14, 28],
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
          maxWidth: 1280,
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          textAlign: 'center',
        }}
      >
        <div
          style={{
            fontSize: 22,
            fontWeight: 800,
            letterSpacing: 5,
            color: theme.accent,
            marginBottom: 28,

            opacity: labelProgress,

            transform: `translateY(${
              (1 - labelProgress) * 10
            }px)`,
          }}
        >
          SECTION
        </div>

        <div
          style={{
            fontSize: Math.min(
              theme.headingSize,
              62,
            ),

            fontWeight: 780,
            color: theme.foreground,
            lineHeight: 1.15,
            letterSpacing: -0.8,

            opacity: titleProgress,

            transform: `translateY(${
              (1 - titleProgress) * 18
            }px)`,
          }}
        >
          {scene.screenText || scene.title}
        </div>

        <div
          style={{
            width: 90 * lineProgress,
            height: 5,
            borderRadius: 999,
            backgroundColor: theme.accent,
            marginTop: 32,

            opacity: lineProgress,
          }}
        />
      </div>
    </div>
  );
};