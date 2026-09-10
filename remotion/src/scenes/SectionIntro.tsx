import React from 'react';

import {AnimatedText} from '../components/AnimatedText';
import type {SceneProps} from './common';

export const SectionIntro: React.FC<SceneProps> = ({scene, theme}) => (
  <div style={{display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 36}}>
    <div
      style={{
        fontSize: 28,
        fontWeight: 800,
        letterSpacing: 8,
        color: theme.accent,
      }}
    >
      SECTION
    </div>
    <div style={{width: 90, height: 5, borderRadius: 3, backgroundColor: theme.accent}} />
    <AnimatedText
      text={scene.screenText || scene.title}
      fontSize={theme.headingSize}
      color={theme.foreground}
    />
  </div>
);
