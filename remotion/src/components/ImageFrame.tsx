import React from 'react';

import type {Theme} from '../theme';

export const ImageFrame: React.FC<{
  src: string;
  theme: Theme;
  zoom?: number;
  maxWidth?: number;
}> = ({src, theme, zoom = 1, maxWidth = 1250}) => (
  <div
    style={{
      width: maxWidth,
      maxWidth: '88%',
      aspectRatio: '16 / 9',
      borderRadius: theme.borderRadius,
      overflow: 'hidden',
      border: `1px solid rgba(17,17,17,0.12)`,
      backgroundColor: '#FFFFFF',
      boxShadow: '0 24px 70px rgba(17,17,17,0.16)',
    }}
  >
    <img
      src={src}
      alt=""
      style={{
        width: '100%',
        height: '100%',
        objectFit: 'contain',
        transform: `scale(${zoom})`,
      }}
    />
  </div>
);
