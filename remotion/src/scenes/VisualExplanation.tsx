import React from 'react';

import {ConceptStrip} from '../components/ConceptStrip';
import {Diagram} from '../visual-actions/Diagram';
import type {SceneProps} from './common';

export const VisualExplanation: React.FC<SceneProps> = ({
  scene,
  theme,
  conceptRects,
  revealMap,
  handwrittenIds,
  fps,
}) => (
  <>
    <div style={{fontSize: 34, color: theme.muted, fontWeight: 700, marginBottom: 24}}>
      {scene.title}
    </div>
    {scene.diagram ? (
      <div style={{position: 'absolute', top: 100, left: 0, right: 0, height: 680}}>
        <Diagram diagram={scene.diagram} fps={fps} theme={theme} actions={scene.visualActions} />
      </div>
    ) : (
      <div style={{fontSize: 44, fontWeight: 800, maxWidth: 1500, lineHeight: 1.3}}>
        {scene.screenText}
      </div>
    )}
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
