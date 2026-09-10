import React from 'react';

import {ConceptStrip} from '../components/ConceptStrip';
import {fitFontSize} from '../utils/layout';
import type {SceneProps} from './common';

export const Definition: React.FC<SceneProps> = ({
  scene,
  theme,
  conceptRects,
  revealMap,
  handwrittenIds,
}) => {
  const fontSize = fitFontSize(scene.screenText, 1550, 44);
  return (
    <>
      <div
        style={{
          backgroundColor: theme.accent,
          color: '#FFFFFF',
          fontSize: 26,
          fontWeight: 800,
          letterSpacing: 6,
          padding: '10px 30px',
          borderRadius: 999,
          marginBottom: 36,
        }}
      >
        DEFINITION
      </div>
      <div style={{fontSize: 40, fontWeight: 800, color: theme.accent, marginBottom: 24}}>
        {scene.title}
      </div>
      <div
        style={{
          fontSize,
          fontWeight: 700,
          lineHeight: 1.32,
          maxWidth: 1550,
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
