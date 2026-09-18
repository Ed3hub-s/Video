import React from 'react';
import {interpolate} from 'remotion';

import {ConceptStrip} from '../components/ConceptStrip';
import {fitFontSize} from '../utils/layout';
import type {SceneProps} from './common';

export const Explanation: React.FC<SceneProps> = ({
  scene,
  theme,
  frame,
  conceptRects,
  revealMap,
  handwrittenIds,
}) => {
  const fontSize = Math.min(
    fitFontSize(
      scene.screenText,
      1280,
      theme.headingSize,
    ),
    58,
  );

  const entrance = interpolate(
    frame,
    [0, 14],
    [0, 1],
    {
      extrapolateLeft: 'clamp',
      extrapolateRight: 'clamp',
    },
  );

  const translateY =
    (1 - entrance) * 18;

  return (
    <div
      style={{
        width: '100%',
        height: '100%',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '0 170px',
        boxSizing: 'border-box',
      }}
    >
      <div
        style={{
          maxWidth: 1280,
          textAlign: 'center',
          opacity: entrance,
          transform: `translateY(${translateY}px)`,
        }}
      >
        <div
          style={{
            width: 72,
            height: 6,
            borderRadius: 999,
            backgroundColor: theme.accent,
            margin: '0 auto 34px auto',
          }}
        />

        <div
          style={{
            fontSize,
            fontWeight: 750,
            color: theme.foreground,
            lineHeight: 1.22,
            letterSpacing: -0.6,
          }}
        >
          {scene.screenText}
        </div>
      </div>
      {conceptRects.length > 0 ? (
        <ConceptStrip
          concepts={scene.keyConcepts}
          rects={conceptRects}
          theme={theme}
          revealMap={revealMap}
          handwrittenIds={handwrittenIds}
        />
      ) : null}
    </div>
  );
};
