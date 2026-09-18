import React from 'react';
import {interpolate} from 'remotion';

import {ConceptStrip} from '../components/ConceptStrip';
import {fitFontSize} from '../utils/layout';
import type {SceneProps} from './common';

export const Definition: React.FC<SceneProps> = ({
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
      1200,
      54,
    ),
    54,
  );

  const labelProgress = interpolate(
    frame,
    [0, 10],
    [0, 1],
    {
      extrapolateLeft: 'clamp',
      extrapolateRight: 'clamp',
    },
  );

  const textProgress = interpolate(
    frame,
    [8, 22],
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
          maxWidth: 1260,
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          textAlign: 'center',
        }}
      >
        <div
          style={{
            backgroundColor: theme.accent,
            color: '#FFFFFF',
            fontSize: 22,
            fontWeight: 800,
            letterSpacing: 4,
            padding: '10px 24px',
            borderRadius: 999,
            marginBottom: 34,

            opacity: labelProgress,

            transform: `translateY(${
              (1 - labelProgress) * 12
            }px)`,
          }}
        >
          DEFINITION
        </div>

        <div
          style={{
            width: 84,
            height: 5,
            borderRadius: 999,
            backgroundColor: theme.accent,
            marginBottom: 34,

            opacity: textProgress,
          }}
        />

        <div
          style={{
            fontSize,
            fontWeight: 760,
            lineHeight: 1.25,
            color: theme.foreground,
            maxWidth: 1200,
            letterSpacing: -0.5,

            opacity: textProgress,

            transform: `translateY(${
              (1 - textProgress) * 18
            }px)`,
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
