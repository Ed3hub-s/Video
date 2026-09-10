import React from 'react';

import {Reveal} from '../visual-actions/Reveal';
import type {SceneProps} from './common';

export const ChapterSummary: React.FC<SceneProps> = ({scene, theme, frame}) => {
  const takeaways = scene.screenText.split(' · ').filter((item) => item.trim());
  return (
    <div style={{display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 30}}>
      <div
        style={{
          fontSize: 30,
          fontWeight: 800,
          letterSpacing: 8,
          color: theme.accent,
        }}
      >
        KEY TAKEAWAYS
      </div>
      {takeaways.map((takeaway, index) => (
        <Reveal
          key={`${takeaway}-${index}`}
          progress={Math.min(1, Math.max(0, (frame - index * 40) / 24))}
        >
          <div
            style={{
              display: 'flex',
              alignItems: 'flex-start',
              gap: 22,
              maxWidth: 1500,
              textAlign: 'left',
            }}
          >
            <div
              style={{
                minWidth: 46,
                height: 46,
                borderRadius: 23,
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
            <div style={{fontSize: 38, fontWeight: 700, lineHeight: 1.3}}>{takeaway}</div>
          </div>
        </Reveal>
      ))}
    </div>
  );
};
