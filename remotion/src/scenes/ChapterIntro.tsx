import React from 'react';

import {AnimatedText} from '../components/AnimatedText';
import type {SceneProps} from './common';

export const ChapterIntro: React.FC<SceneProps> = ({scene, theme, index, total}) => {
  const chapterLabel = `CHAPTER ${String(index + 1).padStart(2, '0')}`;
  return (
    <div style={{display: 'flex', flexDirection: 'column', alignItems: 'center', gap: theme.spacing}}>
      <div
        style={{
          fontSize: 30,
          fontWeight: 800,
          letterSpacing: 10,
          color: theme.accent,
        }}
      >
        {chapterLabel}
      </div>
      <div style={{width: 120, height: 6, borderRadius: 3, backgroundColor: theme.accent}} />
      <AnimatedText
        text={scene.screenText || scene.title}
        fontSize={theme.titleSize}
        color={theme.foreground}
      />
      <div style={{fontSize: 30, color: theme.muted, fontWeight: 600}}>
        {scene.voiceover.replace(`Chapter ${index + 1}.`, '').trim() || ' '}
      </div>
      <div style={{position: 'absolute', bottom: 60, fontSize: 24, color: theme.muted}}>
        Scene {index + 1} of {total}
      </div>
    </div>
  );
};
