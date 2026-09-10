import React from 'react';

import {ConceptStrip} from '../components/ConceptStrip';
import {fitFontSize} from '../utils/layout';
import type {SceneProps} from './common';

export const Explanation: React.FC<SceneProps> = ({
  scene,
  theme,
  conceptRects,
  revealMap,
  handwrittenIds,
}) => {
  const fontSize = fitFontSize(scene.screenText, 1650, theme.headingSize);
  return (
    <>
      <div style={{fontSize: 30, color: theme.muted, fontWeight: 700, marginBottom: 28}}>
        {scene.title}
      </div>
      <div
        style={{
          fontSize,
          fontWeight: 700,
          color: theme.foreground,
          lineHeight: 1.3,
          maxWidth: 1650,
        }}
      >
        {scene.screenText}
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
    </>
  );
};
