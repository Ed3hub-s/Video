import React from 'react';

import {Reveal} from '../visual-actions/Reveal';
import type {SceneProps} from './common';

export const BulletList: React.FC<SceneProps> = ({scene, theme, revealMap, frame}) => {
  const items = scene.screenText.split('\n').filter((item) => item.trim());
  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        gap: 30,
        alignItems: 'flex-start',
        width: 1500,
        maxWidth: '92%',
      }}
    >
      {items.map((item, index) => {
        const progress = revealMap.get(`point-${index}`) ?? Math.min(
          1,
          Math.max(0, (frame - index * 30) / 18),
        );
        return (
          <Reveal key={`${item}-${index}`} progress={progress} style={{width: '100%'}}>
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 26,
                backgroundColor: `${theme.foreground}12`,
                border: `2px solid ${theme.foreground}24`,
                borderRadius: 18,
                padding: '22px 34px',
              }}
            >
              <div
                style={{
                  width: 42,
                  height: 42,
                  borderRadius: 12,
                  backgroundColor: theme.accent,
                  color: '#FFFFFF',
                  fontWeight: 800,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  fontSize: 24,
                }}
              >
                {index + 1}
              </div>
              <div style={{fontSize: 36, fontWeight: 700, lineHeight: 1.25}}>{item}</div>
            </div>
          </Reveal>
        );
      })}
    </div>
  );
};
