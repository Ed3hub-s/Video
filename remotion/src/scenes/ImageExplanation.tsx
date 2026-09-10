import React from 'react';

import {ConceptStrip} from '../components/ConceptStrip';
import {ImageFrame} from '../components/ImageFrame';
import {useProgress} from '../utils/animation';
import {resolveMedia} from '../utils/media';
import type {SceneProps} from './common';

export const ImageExplanation: React.FC<SceneProps> = ({
  scene,
  theme,
  conceptRects,
  revealMap,
  handwrittenIds,
  frame,
  fps,
}) => {
  const zoomAction = scene.visualActions.find((action) => action.type === 'zoomFocus');
  const zoomProgress = zoomAction ? useProgress(frame, zoomAction.startSec, zoomAction.durationSec, fps) : 0;
  const zoom = 1 + 0.12 * zoomProgress;
  return (
    <>
      <div style={{fontSize: 30, color: theme.muted, fontWeight: 700, marginBottom: 24}}>
        {scene.title}
      </div>
      <ImageFrame
        src={scene.image ? resolveMedia(scene.image) : ''}
        theme={theme}
        zoom={zoom}
        maxWidth={1000}
      />
      {scene.screenText ? (
        <div style={{fontSize: 34, color: theme.foreground, fontWeight: 600, marginTop: 28}}>
          {scene.screenText}
        </div>
      ) : null}
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
