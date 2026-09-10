import React from 'react';
import {AbsoluteFill} from 'remotion';

import type {Theme} from '../theme';
import type {BackgroundTreatment} from '../styles';

const backgroundStyle = (theme: Theme, treatment: BackgroundTreatment) => {
  switch (treatment) {
    case 'flat':
      return {backgroundColor: theme.background};
    case 'soft':
      return {
        backgroundColor: theme.background,
        backgroundImage:
          'radial-gradient(ellipse at 50% 35%, rgba(255,255,255,0.9) 0%, rgba(255,255,255,0) 70%)',
      };
    case 'dark-glow':
      return {
        backgroundColor: theme.background,
        backgroundImage:
          'radial-gradient(ellipse at 50% 38%, rgba(255,255,255,0.08) 0%, rgba(255,255,255,0) 65%)',
      };
    case 'sunset':
      return {
        backgroundColor: theme.background,
        backgroundImage: 'linear-gradient(165deg, #FFF7E8 0%, #FFE9D2 55%, #FFDDB8 100%)',
      };
    case 'paper':
      return {
        backgroundColor: theme.background,
        backgroundImage:
          'linear-gradient(135deg, rgba(255,255,255,0.5) 0%, rgba(255,255,255,0) 60%)',
      };
    default:
      return {backgroundColor: theme.background};
  }
};

export const SceneContainer: React.FC<{
  theme: Theme;
  background?: BackgroundTreatment;
  children: React.ReactNode;
}> = ({theme, background = 'soft', children}) => (
  <AbsoluteFill
    style={{
      fontFamily: theme.fontFamily,
      color: theme.foreground,
      padding: `${theme.safeMarginY}px ${theme.safeMarginX}px`,
      ...backgroundStyle(theme, background),
    }}
  >
    <div
      style={{
        position: 'relative',
        flex: 1,
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        textAlign: 'center',
      }}
    >
      {children}
    </div>
  </AbsoluteFill>
);
