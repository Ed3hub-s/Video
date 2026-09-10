import React from 'react';

export const Reveal: React.FC<{
  progress: number;
  children?: React.ReactNode;
  style?: React.CSSProperties;
}> = ({progress, children, style}) => (
  <div
    style={{
      opacity: progress,
      transform: `scale(${0.9 + 0.1 * progress}) translateY(${(1 - progress) * 18}px)`,
      ...style,
    }}
  >
    {children}
  </div>
);
