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
}) => {
  /*
   * When a real diagram is present, the diagram becomes the entire
   * teaching canvas.
   *
   * We intentionally do NOT render:
   *
   * - scene title
   * - screen text
   * - concept strip
   *
   * behind or around the diagram.
   *
   * The diagram's own labels are sufficient visual context.
   *
   * This keeps graphical teaching scenes clean and prevents the
   * illustrations from appearing on top of unrelated words.
   */
  if (scene.diagram) {
    return (
      <div
        style={{
          position: 'absolute',
          inset: 0,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
        }}
      >
        <div
          style={{
            position: 'absolute',
            left: 0,
            right: 0,
            top: 40,
            height: 680,
          }}
        >
          <Diagram
            diagram={scene.diagram}
            fps={fps}
            theme={theme}
            actions={scene.visualActions}
          />
        </div>
      </div>
    );
  }

  /*
   * A visualExplanation without a diagram keeps the existing
   * text-oriented fallback.
   */
  return (
    <>
      <div
        style={{
          fontSize: 34,
          color: theme.muted,
          fontWeight: 700,
          marginBottom: 24,
        }}
      >
        {scene.title}
      </div>

      <div
        style={{
          fontSize: 44,
          fontWeight: 800,
          maxWidth: 1500,
          lineHeight: 1.3,
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