import React from 'react';

import type {Theme} from '../theme';
import type {KeyConcept} from '../types';
import type {Rect} from '../utils/layout';

export const ConceptLabel: React.FC<{
  concept: KeyConcept;
  rect: Rect;
  theme: Theme;
  revealProgress?: number;
  handwriting?: boolean;
}> = ({concept, rect, theme, revealProgress = 1, handwriting = false}) => {
  const high = concept.importance === 'high';
  const medium = concept.importance === 'medium';
  const borderColor = high ? theme.accent : medium ? theme.muted : `${theme.foreground}2E`;
  const background = high ? `${theme.accent}1A` : `${theme.foreground}12`;
  const fontFamily = handwriting
    ? "'Segoe Script', 'Comic Sans MS', cursive"
    : theme.fontFamily;
  return (
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
        border: `3px solid ${borderColor}`,
        borderRadius: 16,
        backgroundColor: background,
        fontFamily,
        fontSize: high ? 28 : 24,
        fontWeight: high ? 800 : 600,
        color: high ? theme.foreground : theme.foreground,
        opacity: revealProgress,
        transform: `scale(${0.85 + 0.15 * revealProgress})`,
      }}
    >
      {concept.text}
    </div>
  );
};
