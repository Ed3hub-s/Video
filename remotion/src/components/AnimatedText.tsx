import React from 'react';
import {interpolate, useCurrentFrame} from 'remotion';

import {clamp} from '../utils/timing';

export const AnimatedText: React.FC<{
  text: string;
  fontSize: number;
  color: string;
  fontWeight?: number;
  staggerSec?: number;
}> = ({text, fontSize, color, fontWeight = 700, staggerSec = 0.12}) => {
  const frame = useCurrentFrame();
  const words = text.split(' ');
  return (
    <span
      style={{
        fontSize,
        fontWeight,
        color,
        lineHeight: 1.18,
        display: 'inline-block',
        maxWidth: '100%',
      }}
    >
      {words.map((word, index) => {
        const start = index * staggerSec * 30;
        const opacity = clamp(interpolate(frame, [start, start + 12], [0, 1], {
          extrapolateLeft: 'clamp',
          extrapolateRight: 'clamp',
        }), 0, 1);
        return (
          <span
            key={`${word}-${index}`}
            style={{
              display: 'inline-block',
              opacity,
              transform: `translateY(${(1 - opacity) * 14}px)`,
            }}
          >
            {word}
            {index < words.length - 1 ? '\u00A0' : ''}
          </span>
        );
      })}
    </span>
  );
};
