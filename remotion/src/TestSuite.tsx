import React from 'react';

import {Tutorial} from './Tutorial';
import type {ChapterManifest} from './types';

// 1x1 transparent PNG - lets imageExplanation render without staged media.
const TINY_PNG =
  'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg==';

type SceneOverrides = Partial<ChapterManifest['scenes'][number]>;

const scene = (id: string, type: string, overrides: SceneOverrides = {}) => ({
  id,
  type,
  title: type,
  screenText: '',
  voiceover: '',
  keyConcepts: [],
  visualStrategy: 'none',
  visualActions: [],
  image: null,
  diagram: null,
  audio: null,
  subtitles: [],
  durationSeconds: 2,
  sourceText: '',
  ...overrides,
});

export const testManifest: ChapterManifest = {
  courseTitle: 'Render Test',
  chapterNumber: 99,
  chapterTitle: 'All Scene Types',
  fps: 30,
  width: 1920,
  height: 1080,
  totalDurationSeconds: 16,
  scenes: [
    scene('scene-001', 'chapterIntro', {
      title: 'Chapter Intro',
      screenText: 'Chapter Intro Title',
      voiceover: 'Welcome to this chapter.',
    }),
    scene('scene-002', 'sectionIntro', {
      title: 'A Major Section',
      screenText: 'A Major Section',
      voiceover: 'This section covers one big idea.',
    }),
    scene('scene-003', 'explanation', {
      title: 'Explanation Scene',
      screenText: 'An explanation with important concepts on screen.',
      voiceover: 'Here is an explanation with two important concepts.',
      keyConcepts: [
        {id: 'c1', text: 'CONCEPT A', importance: 'high'},
        {id: 'c2', text: 'CONCEPT B', importance: 'medium'},
      ],
      visualActions: [
        {type: 'reveal', target: 'c1', startSec: 0.2, durationSec: 0.5},
        {type: 'underline', target: 'c1', startSec: 0.8, durationSec: 0.7},
        {type: 'highlight', target: 'c2', startSec: 1.0, durationSec: 0.8},
        {type: 'compare', startSec: 1.2, durationSec: 0.8},
      ],
    }),
    scene('scene-004', 'definition', {
      title: 'What is X?',
      screenText: 'X is defined as the core concept.',
      voiceover: 'X is defined as the core concept.',
      keyConcepts: [
        {id: 'd1', text: 'CORE', importance: 'high'},
        {id: 'd2', text: 'CONCEPT', importance: 'high'},
      ],
      visualActions: [
        {type: 'handwrite', target: 'd1', startSec: 0.5, durationSec: 0.9},
        {type: 'circle', target: 'd2', startSec: 1.1, durationSec: 0.8},
        {type: 'drawBox', target: 'd1', startSec: 1.5, durationSec: 0.8},
        {type: 'crossOut', target: 'd2', startSec: 1.8, durationSec: 0.7},
      ],
    }),
    scene('scene-005', 'bulletList', {
      title: 'Key Points',
      screenText: 'Point one\nPoint two\nPoint three',
      voiceover: 'Three key points follow.',
      visualActions: [
        {type: 'reveal', target: 'point-0', startSec: 0.2, durationSec: 0.4},
        {type: 'reveal', target: 'point-1', startSec: 0.8, durationSec: 0.4},
        {type: 'reveal', target: 'point-2', startSec: 1.4, durationSec: 0.4},
      ],
    }),
    scene('scene-006', 'imageExplanation', {
      title: 'Image Scene',
      screenText: 'Study this diagram carefully.',
      voiceover: 'Let us look closely at this diagram.',
      image: TINY_PNG,
      visualActions: [{type: 'zoomFocus', startSec: 0.3, durationSec: 1.2}],
    }),
    scene('scene-007', 'visualExplanation', {
      title: 'Process Explanation',
      screenText: '',
      voiceover: 'Data flows into the model and produces a prediction.',
      diagram: {
        kind: 'process',
        nodes: [
          {id: 'n1', label: 'DATA'},
          {id: 'n2', label: 'MODEL'},
          {id: 'n3', label: 'PREDICTION'},
        ],
        edges: [
          {from: 'n1', to: 'n2'},
          {from: 'n2', to: 'n3'},
        ],
      },
      visualActions: [
        {type: 'buildDiagram', startSec: 0.2, durationSec: 1.0},
        {type: 'reveal', target: 'n1', startSec: 0.4, durationSec: 0.4},
        {type: 'reveal', target: 'n2', startSec: 1.0, durationSec: 0.4},
        {type: 'reveal', target: 'n3', startSec: 1.6, durationSec: 0.4},
        {type: 'drawArrow', from: 'n1', to: 'n2', startSec: 0.9, durationSec: 0.6},
        {type: 'connect', from: 'n2', to: 'n3', startSec: 1.5, durationSec: 0.6},
      ],
    }),
    scene('scene-008', 'chapterSummary', {
      title: 'Key Takeaways',
      screenText: 'Takeaway one · Takeaway two · Takeaway three',
      voiceover: 'To summarize, these are the takeaways.',
    }),
  ],
};

export const TestSuite: React.FC = () => <Tutorial manifest={testManifest} />;
