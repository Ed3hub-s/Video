import React from 'react';
import {useCurrentFrame} from 'remotion';

import type {Theme} from '../theme';
import type {
  Diagram as DiagramData,
  DiagramNode,
  VisualAction,
} from '../types';
import {
  drawStrokeProps,
  useProgress,
} from '../utils/animation';


type Point = {
  x: number;
  y: number;
};

type Rect = {
  x: number;
  y: number;
  w: number;
  h: number;
};

type LayoutResult = {
  centers: Map<string, Point>;
  rects: Map<string, Rect>;
};

type IconAnimationMode =
  | 'appear'
  | 'draw'
  | 'build';

type CompatibleEdge = {
  from?: string | null;
  from_id?: string | null;
  to: string;
};

type CompatibleAction = VisualAction & {
  from_id?: string | null;
};


const CANVAS_WIDTH = 1600;
const CANVAS_HEIGHT = 680;

const NODE_WIDTH = 250;
const NODE_HEIGHT = 220;

const DIAGRAM_SIDE_PADDING = 140;


const clamp01 = (
  value: number,
): number =>
  Math.max(
    0,
    Math.min(1, value),
  );


const delayedProgress = (
  progress: number,
  start: number,
  end = 1,
): number => {
  if (end <= start) {
    return progress >= end
      ? 1
      : 0;
  }

  return clamp01(
    (progress - start) /
      (end - start),
  );
};


const edgeFromId = (
  edge: CompatibleEdge,
): string =>
  edge.from ??
  edge.from_id ??
  '';


const actionFromId = (
  action: CompatibleAction,
): string =>
  action.from ??
  action.from_id ??
  '';


const iconAnimationMode = (
  label: string,
): IconAnimationMode => {
  const value =
    label.toUpperCase();

  /*
   * BUILD:
   * The construction process itself helps explain
   * what the object represents.
   */
  if (
    value.includes('NETWORK') ||
    value.includes('BLOCKCHAIN') ||
    value.includes('PROTOCOL') ||
    value.includes('ANALYT') ||
    value.includes('DATA') ||
    value.includes('ACTIVITY') ||
    value.includes('TRANSFER')
  ) {
    return 'build';
  }

  /*
   * DRAW:
   * Tracing the symbol adds useful visual meaning.
   */
  if (
    value.includes('SMART CONTRACT') ||
    value.includes('CODE') ||
    value.includes('SECURITY') ||
    value.includes('SAFE') ||
    value.includes('PROTECTION') ||
    value.includes('LOSS') ||
    value.includes('FAIL') ||
    value.includes('PROBLEM')
  ) {
    return 'draw';
  }

  /*
   * Ordinary objects and roles should simply appear.
   */
  return 'appear';
};


const nodeRevealProgress = (
  actions: VisualAction[],
  id: string,
  frame: number,
  fps: number,
): number => {
  const reveal =
    actions.find(
      (action) =>
        action.type === 'reveal' &&
        action.target === id,
    );

  if (reveal) {
    return useProgress(
      frame,
      reveal.startSec,
      reveal.durationSec,
      fps,
    );
  }

  const build =
    actions.find(
      (action) =>
        action.type === 'buildDiagram',
    );

  if (build) {
    return useProgress(
      frame,
      build.startSec,
      build.durationSec,
      fps,
    );
  }

  return 1;
};


/*
 * IMPORTANT:
 *
 * This is deliberately separate from nodeRevealProgress().
 *
 * The Python visual planner often gives a node reveal duration
 * of only about 0.5 seconds. That is fine for a simple pop/fade,
 * but far too fast for an icon that should visibly draw itself.
 *
 * Draw and build modes therefore keep the same starting cue but
 * receive their own longer duration.
 */
const nodeIconProgress = (
  actions: VisualAction[],
  id: string,
  mode: IconAnimationMode,
  frame: number,
  fps: number,
): number => {
  const reveal =
    actions.find(
      (action) =>
        action.type === 'reveal' &&
        action.target === id,
    );

  const build =
    actions.find(
      (action) =>
        action.type === 'buildDiagram',
    );

  const startSec =
    reveal?.startSec ??
    build?.startSec ??
    0;

  if (mode === 'draw') {
    return useProgress(
      frame,
      startSec,
      1.4,
      fps,
    );
  }

  if (mode === 'build') {
    return useProgress(
      frame,
      startSec,
      1.8,
      fps,
    );
  }

  return nodeRevealProgress(
    actions,
    id,
    frame,
    fps,
  );
};


const edgeProgress = (
  actions: VisualAction[],
  from: string,
  to: string,
  frame: number,
  fps: number,
): number => {
  const compatibleActions =
    actions as CompatibleAction[];

  const arrow =
    compatibleActions.find(
      (action) =>
        action.type === 'drawArrow' &&
        actionFromId(action) === from &&
        action.to === to,
    );

  if (arrow) {
    return useProgress(
      frame,
      arrow.startSec,
      Math.max(
        0.9,
        arrow.durationSec,
      ),
      fps,
    );
  }

  const connect =
    compatibleActions.find(
      (action) =>
        action.type === 'connect' &&
        actionFromId(action) === from &&
        action.to === to,
    );

  if (connect) {
    return useProgress(
      frame,
      connect.startSec,
      Math.max(
        0.9,
        connect.durationSec,
      ),
      fps,
    );
  }

  const build =
    compatibleActions.find(
      (action) =>
        action.type === 'buildDiagram',
    );

  if (build) {
    return useProgress(
      frame,
      build.startSec + 0.65,
      1.25,
      fps,
    );
  }

  return 1;
};


const clampFontSize = (
  label: string,
): number => {
  if (label.length <= 9) {
    return 29;
  }

  if (label.length <= 15) {
    return 25;
  }

  if (label.length <= 21) {
    return 22;
  }

  return 19;
};


const layoutDiagram = (
  diagram: DiagramData,
): LayoutResult => {
  const centers =
    new Map<string, Point>();

  const rects =
    new Map<string, Rect>();

  const minCenterX =
    DIAGRAM_SIDE_PADDING +
    NODE_WIDTH / 2;

  const maxCenterX =
    CANVAS_WIDTH -
    DIAGRAM_SIDE_PADDING -
    NODE_WIDTH / 2;

  const clampCenterX = (
    value: number,
  ): number =>
    Math.max(
      minCenterX,
      Math.min(
        maxCenterX,
        value,
      ),
    );

  const place = (
    node: DiagramNode,
    x: number,
    y: number,
  ) => {
    const safeX =
      clampCenterX(x);

    centers.set(
      node.id,
      {
        x: safeX,
        y,
      },
    );

    rects.set(
      node.id,
      {
        x:
          safeX -
          NODE_WIDTH / 2,

        y:
          y -
          NODE_HEIGHT / 2,

        w:
          NODE_WIDTH,

        h:
          NODE_HEIGHT,
      },
    );
  };

  const nodes =
    diagram.nodes;

  const count =
    nodes.length;

  if (count === 0) {
    return {
      centers,
      rects,
    };
  }

  /*
   * Comparison diagrams use two intentionally separated
   * cards with a centered VS badge.
   *
   * The positions stay well inside the safe diagram canvas
   * so long labels cannot be clipped by the video edge.
   */
  if (
    diagram.kind === 'comparison'
  ) {
    if (nodes[0]) {
      place(
        nodes[0],
        CANVAS_WIDTH * 0.28,
        340,
      );
    }

    if (nodes[1]) {
      place(
        nodes[1],
        CANVAS_WIDTH * 0.72,
        340,
      );
    }

    return {
      centers,
      rects,
    };
  }

  /*
   * Relationship diagrams keep the main subject in the
   * center and place satellites around it.
   *
   * The previous 1920px layout could overflow because the
   * diagram itself is rendered inside the scene's safe
   * content area. These positions are now based on the
   * smaller centered diagram canvas.
   */
  if (
    diagram.kind === 'relationship'
  ) {
    if (nodes[0]) {
      place(
        nodes[0],
        CANVAS_WIDTH / 2,
        340,
      );
    }

    const positions: Point[] = [
      {
        x: CANVAS_WIDTH * 0.23,
        y: 200,
      },
      {
        x: CANVAS_WIDTH * 0.77,
        y: 200,
      },
      {
        x: CANVAS_WIDTH * 0.23,
        y: 505,
      },
      {
        x: CANVAS_WIDTH * 0.77,
        y: 505,
      },
    ];

    nodes
      .slice(1, 5)
      .forEach(
        (
          node,
          index,
        ) => {
          const position =
            positions[index];

          if (position) {
            place(
              node,
              position.x,
              position.y,
            );
          }
        },
      );

    return {
      centers,
      rects,
    };
  }

  /*
   * Process, cause/effect and other chain-like diagrams
   * distribute their cards only between minCenterX and
   * maxCenterX. The full card width is therefore guaranteed
   * to remain inside the local diagram canvas.
   */
  const usableWidth =
    maxCenterX -
    minCenterX;

  const spacing =
    count <= 1
      ? 0
      : usableWidth /
        (count - 1);

  nodes.forEach(
    (
      node,
      index,
    ) => {
      const x =
        count === 1
          ? CANVAS_WIDTH / 2
          : minCenterX +
            spacing * index;

      place(
        node,
        x,
        340,
      );
    },
  );

  return {
    centers,
    rects,
  };
};


const lineEndpoints = (
  from: Point,
  to: Point,
): {
  start: Point;
  end: Point;
} => {
  const dx =
    to.x - from.x;

  const dy =
    to.y - from.y;

  const distance =
    Math.sqrt(
      dx * dx +
      dy * dy,
    ) || 1;

  const ux =
    dx / distance;

  const uy =
    dy / distance;

  const radiusX =
    NODE_WIDTH / 2 + 14;

  const radiusY =
    NODE_HEIGHT / 2 + 14;

  const scale =
    Math.min(
      Math.abs(
        radiusX /
          (ux || 0.0001),
      ),
      Math.abs(
        radiusY /
          (uy || 0.0001),
      ),
    );

  const offset =
    Math.min(
      scale,
      140,
    );

  return {
    start: {
      x:
        from.x +
        ux * offset,

      y:
        from.y +
        uy * offset,
    },

    end: {
      x:
        to.x -
        ux * offset,

      y:
        to.y -
        uy * offset,
    },
  };
};


const Arrow: React.FC<{
  from: Point;
  to: Point;
  progress: number;
  theme: Theme;
}> = ({
  from,
  to,
  progress,
  theme,
}) => {
  const {
    start,
    end,
  } = lineEndpoints(
    from,
    to,
  );

  const dx =
    end.x - start.x;

  const dy =
    end.y - start.y;

  const currentEnd = {
    x:
      start.x +
      dx * progress,

    y:
      start.y +
      dy * progress,
  };

  const angle =
    Math.atan2(
      dy,
      dx,
    );

  const arrowSize =
    24;

  const arrowOpacity =
    clamp01(
      (progress - 0.72) *
        4,
    );

  const headA = {
    x:
      currentEnd.x -
      arrowSize *
        Math.cos(
          angle - 0.5,
        ),

    y:
      currentEnd.y -
      arrowSize *
        Math.sin(
          angle - 0.5,
        ),
  };

  const headB = {
    x:
      currentEnd.x -
      arrowSize *
        Math.cos(
          angle + 0.5,
        ),

    y:
      currentEnd.y -
      arrowSize *
        Math.sin(
          angle + 0.5,
        ),
  };

  return (
    <g>
      <line
        x1={start.x}
        y1={start.y}
        x2={currentEnd.x}
        y2={currentEnd.y}
        stroke={
          theme.accent
        }
        strokeWidth={6}
        strokeLinecap="round"
      />

      <circle
        cx={start.x}
        cy={start.y}
        r={7}
        fill={
          theme.accent
        }
        opacity={
          clamp01(
            progress * 2,
          )
        }
      />

      <polygon
        points={`
          ${currentEnd.x},${currentEnd.y}
          ${headA.x},${headA.y}
          ${headB.x},${headB.y}
        `}
        fill={
          theme.accent
        }
        opacity={
          arrowOpacity
        }
      />
    </g>
  );
};


const GenericIcon: React.FC<{
  theme: Theme;
}> = ({
  theme,
}) => (
  <svg
    width="86"
    height="86"
    viewBox="0 0 100 100"
  >
    <circle
      cx="50"
      cy="50"
      r="30"
      fill="none"
      stroke={
        theme.accent
      }
      strokeWidth="6"
    />

    <circle
      cx="50"
      cy="50"
      r="8"
      fill={
        theme.accent
      }
    />

    <line
      x1="50"
      y1="10"
      x2="50"
      y2="25"
      stroke={
        theme.foreground
      }
      strokeWidth="5"
      strokeLinecap="round"
    />

    <line
      x1="50"
      y1="75"
      x2="50"
      y2="90"
      stroke={
        theme.foreground
      }
      strokeWidth="5"
      strokeLinecap="round"
    />
  </svg>
);


const UserIcon: React.FC<{
  theme: Theme;
}> = ({
  theme,
}) => (
  <svg
    width="86"
    height="86"
    viewBox="0 0 100 100"
  >
    <circle
      cx="50"
      cy="29"
      r="17"
      fill="none"
      stroke={
        theme.accent
      }
      strokeWidth="6"
    />

    <path
      d="
        M20 88
        C22 62 34 52 50 52
        C66 52 78 62 80 88
      "
      fill="none"
      stroke={
        theme.foreground
      }
      strokeWidth="7"
      strokeLinecap="round"
    />
  </svg>
);


const WalletIcon: React.FC<{
  theme: Theme;
}> = ({
  theme,
}) => (
  <svg
    width="92"
    height="86"
    viewBox="0 0 110 100"
  >
    <rect
      x="14"
      y="23"
      width="82"
      height="60"
      rx="12"
      fill="none"
      stroke={
        theme.foreground
      }
      strokeWidth="6"
    />

    <path
      d="
        M18 34
        L83 34
      "
      fill="none"
      stroke={
        theme.accent
      }
      strokeWidth="6"
      strokeLinecap="round"
    />

    <rect
      x="65"
      y="45"
      width="36"
      height="25"
      rx="8"
      fill={
        theme.accent
      }
    />

    <circle
      cx="77"
      cy="57"
      r="4"
      fill={
        theme.background
      }
    />
  </svg>
);


const CoinIcon: React.FC<{
  theme: Theme;
}> = ({
  theme,
}) => (
  <svg
    width="86"
    height="86"
    viewBox="0 0 100 100"
  >
    <circle
      cx="50"
      cy="50"
      r="34"
      fill="none"
      stroke={
        theme.accent
      }
      strokeWidth="7"
    />

    <circle
      cx="50"
      cy="50"
      r="24"
      fill="none"
      stroke={
        theme.foreground
      }
      strokeWidth="4"
    />

    <line
      x1="50"
      y1="27"
      x2="50"
      y2="73"
      stroke={
        theme.foreground
      }
      strokeWidth="4"
    />

    <path
      d="
        M59 35
        C51 30 39 31 39 41
        C39 50 61 47 61 58
        C61 68 46 72 37 65
      "
      fill="none"
      stroke={
        theme.accent
      }
      strokeWidth="5"
      strokeLinecap="round"
    />
  </svg>
);


const DatabaseIcon: React.FC<{
  theme: Theme;
}> = ({
  theme,
}) => (
  <svg
    width="92"
    height="86"
    viewBox="0 0 110 100"
  >
    <ellipse
      cx="55"
      cy="24"
      rx="34"
      ry="13"
      fill="none"
      stroke={
        theme.accent
      }
      strokeWidth="6"
    />

    <path
      d="
        M21 24
        L21 73
        C21 83 89 83 89 73
        L89 24
      "
      fill="none"
      stroke={
        theme.foreground
      }
      strokeWidth="6"
    />

    <path
      d="
        M21 48
        C21 59 89 59 89 48
      "
      fill="none"
      stroke={
        theme.accent
      }
      strokeWidth="5"
    />
  </svg>
);


const CareerIcon: React.FC<{
  theme: Theme;
}> = ({
  theme,
}) => (
  <svg
    width="92"
    height="86"
    viewBox="0 0 110 100"
  >
    <rect
      x="16"
      y="32"
      width="78"
      height="51"
      rx="10"
      fill="none"
      stroke={
        theme.foreground
      }
      strokeWidth="6"
    />

    <path
      d="
        M40 32
        L40 24
        C40 17 46 14 55 14
        C64 14 70 17 70 24
        L70 32
      "
      fill="none"
      stroke={
        theme.accent
      }
      strokeWidth="6"
    />

    <path
      d="
        M16 49
        C38 62 72 62 94 49
      "
      fill="none"
      stroke={
        theme.accent
      }
      strokeWidth="5"
    />

    <rect
      x="49"
      y="50"
      width="12"
      height="12"
      rx="3"
      fill={
        theme.accent
      }
    />
  </svg>
);


const CodeDrawIcon: React.FC<{
  theme: Theme;
  progress: number;
}> = ({
  theme,
  progress,
}) => {
  const box =
    delayedProgress(
      progress,
      0,
      0.48,
    );

  const leftCode =
    delayedProgress(
      progress,
      0.28,
      0.72,
    );

  const rightCode =
    delayedProgress(
      progress,
      0.42,
      0.84,
    );

  const slash =
    delayedProgress(
      progress,
      0.58,
      1,
    );

  return (
    <svg
      width="92"
      height="86"
      viewBox="0 0 110 100"
    >
      <path
        d="
          M24 16
          H86
          Q98 16 98 28
          V74
          Q98 86 86 86
          H24
          Q12 86 12 74
          V28
          Q12 16 24 16
          Z
        "
        fill="none"
        stroke={
          theme.foreground
        }
        strokeWidth="6"
        strokeLinecap="round"
        strokeLinejoin="round"
        {...drawStrokeProps(
          box,
        )}
      />

      <path
        d="
          M43 47
          L31 58
          L43 69
        "
        fill="none"
        stroke={
          theme.accent
        }
        strokeWidth="6"
        strokeLinecap="round"
        strokeLinejoin="round"
        {...drawStrokeProps(
          leftCode,
        )}
      />

      <path
        d="
          M67 47
          L79 58
          L67 69
        "
        fill="none"
        stroke={
          theme.accent
        }
        strokeWidth="6"
        strokeLinecap="round"
        strokeLinejoin="round"
        {...drawStrokeProps(
          rightCode,
        )}
      />

      <path
        d="
          M61 42
          L49 74
        "
        fill="none"
        stroke={
          theme.foreground
        }
        strokeWidth="5"
        strokeLinecap="round"
        {...drawStrokeProps(
          slash,
        )}
      />
    </svg>
  );
};


const NetworkBuildIcon: React.FC<{
  theme: Theme;
  progress: number;
}> = ({
  theme,
  progress,
}) => {
  const firstNode =
    delayedProgress(
      progress,
      0,
      0.25,
    );

  const firstEdge =
    delayedProgress(
      progress,
      0.15,
      0.5,
    );

  const secondNode =
    delayedProgress(
      progress,
      0.32,
      0.58,
    );

  const secondEdge =
    delayedProgress(
      progress,
      0.45,
      0.78,
    );

  const thirdNode =
    delayedProgress(
      progress,
      0.62,
      0.88,
    );

  const closingEdge =
    delayedProgress(
      progress,
      0.72,
      1,
    );

  return (
    <svg
      width="92"
      height="86"
      viewBox="0 0 110 100"
    >
      <path
        d="M55 21 L25 70"
        fill="none"
        stroke={
          theme.foreground
        }
        strokeWidth="5"
        strokeLinecap="round"
        {...drawStrokeProps(
          firstEdge,
        )}
      />

      <path
        d="M55 21 L86 70"
        fill="none"
        stroke={
          theme.foreground
        }
        strokeWidth="5"
        strokeLinecap="round"
        {...drawStrokeProps(
          secondEdge,
        )}
      />

      <path
        d="M25 70 L86 70"
        fill="none"
        stroke={
          theme.foreground
        }
        strokeWidth="5"
        strokeLinecap="round"
        {...drawStrokeProps(
          closingEdge,
        )}
      />

      <circle
        cx="55"
        cy="21"
        r={
          12 *
          firstNode
        }
        fill={
          theme.accent
        }
      />

      <circle
        cx="25"
        cy="70"
        r={
          12 *
          secondNode
        }
        fill={
          theme.accent
        }
      />

      <circle
        cx="86"
        cy="70"
        r={
          12 *
          thirdNode
        }
        fill={
          theme.accent
        }
      />
    </svg>
  );
};


const AnalyticsBuildIcon: React.FC<{
  theme: Theme;
  progress: number;
}> = ({
  theme,
  progress,
}) => {
  const axis =
    delayedProgress(
      progress,
      0,
      0.25,
    );

  const barOne =
    delayedProgress(
      progress,
      0.18,
      0.48,
    );

  const barTwo =
    delayedProgress(
      progress,
      0.32,
      0.62,
    );

  const barThree =
    delayedProgress(
      progress,
      0.46,
      0.76,
    );

  const line =
    delayedProgress(
      progress,
      0.6,
      1,
    );

  return (
    <svg
      width="92"
      height="86"
      viewBox="0 0 110 100"
    >
      <path
        d="
          M18 18
          V82
          H95
        "
        fill="none"
        stroke={
          theme.foreground
        }
        strokeWidth="5"
        strokeLinecap="round"
        {...drawStrokeProps(
          axis,
        )}
      />

      <rect
        x="26"
        y={
          82 -
          31 *
            barOne
        }
        width="14"
        height={
          31 *
          barOne
        }
        rx="3"
        fill={
          theme.accent
        }
      />

      <rect
        x="49"
        y={
          82 -
          46 *
            barTwo
        }
        width="14"
        height={
          46 *
          barTwo
        }
        rx="3"
        fill={
          theme.accent
        }
      />

      <rect
        x="72"
        y={
          82 -
          61 *
            barThree
        }
        width="14"
        height={
          61 *
          barThree
        }
        rx="3"
        fill={
          theme.accent
        }
      />

      <path
        d="
          M26 48
          L50 31
          L68 37
          L88 17
        "
        fill="none"
        stroke={
          theme.foreground
        }
        strokeWidth="5"
        strokeLinecap="round"
        strokeLinejoin="round"
        {...drawStrokeProps(
          line,
        )}
      />
    </svg>
  );
};


const ShieldDrawIcon: React.FC<{
  theme: Theme;
  progress: number;
}> = ({
  theme,
  progress,
}) => {
  const shield =
    delayedProgress(
      progress,
      0,
      0.72,
    );

  const check =
    delayedProgress(
      progress,
      0.56,
      1,
    );

  return (
    <svg
      width="86"
      height="86"
      viewBox="0 0 100 100"
    >
      <path
        d="
          M50 12
          L81 24
          L77 56
          C74 74 63 84 50 91
          C37 84 26 74 23 56
          L19 24
          Z
        "
        fill="none"
        stroke={
          theme.foreground
        }
        strokeWidth="6"
        strokeLinejoin="round"
        {...drawStrokeProps(
          shield,
        )}
      />

      <path
        d="
          M35 52
          L46 63
          L68 39
        "
        fill="none"
        stroke={
          theme.accent
        }
        strokeWidth="7"
        strokeLinecap="round"
        strokeLinejoin="round"
        {...drawStrokeProps(
          check,
        )}
      />
    </svg>
  );
};


const LossDrawIcon: React.FC<{
  theme: Theme;
  progress: number;
}> = ({
  theme,
  progress,
}) => {
  const decline =
    delayedProgress(
      progress,
      0,
      0.78,
    );

  const coin =
    delayedProgress(
      progress,
      0.48,
      1,
    );

  return (
    <svg
      width="92"
      height="86"
      viewBox="0 0 110 100"
    >
      <path
        d="
          M17 25
          L38 44
          L55 37
          L86 72
          L73 71
          M86 72
          L86 58
        "
        fill="none"
        stroke={
          theme.foreground
        }
        strokeWidth="7"
        strokeLinecap="round"
        strokeLinejoin="round"
        {...drawStrokeProps(
          decline,
        )}
      />

      <circle
        cx="29"
        cy="72"
        r="16"
        fill="none"
        stroke={
          theme.accent
        }
        strokeWidth="6"
        opacity={
          coin
        }
      />

      <line
        x1="29"
        y1="63"
        x2="29"
        y2="81"
        stroke={
          theme.foreground
        }
        strokeWidth="4"
        opacity={
          coin
        }
      />
    </svg>
  );
};


const SemanticIcon: React.FC<{
  label: string;
  theme: Theme;
  progress: number;
}> = ({
  label,
  theme,
  progress,
}) => {
  const normalized =
    label.toUpperCase();

  if (
    normalized.includes(
      'NETWORK',
    ) ||
    normalized.includes(
      'BLOCKCHAIN',
    ) ||
    normalized.includes(
      'PROTOCOL',
    )
  ) {
    return (
      <NetworkBuildIcon
        theme={theme}
        progress={progress}
      />
    );
  }

  if (
    normalized.includes(
      'ANALYT',
    ) ||
    normalized.includes(
      'DATA',
    ) ||
    normalized.includes(
      'ACTIVITY',
    ) ||
    normalized.includes(
      'TRANSFER',
    )
  ) {
    return (
      <AnalyticsBuildIcon
        theme={theme}
        progress={progress}
      />
    );
  }

  if (
    normalized.includes(
      'SMART CONTRACT',
    ) ||
    normalized.includes(
      'CODE',
    )
  ) {
    return (
      <CodeDrawIcon
        theme={theme}
        progress={progress}
      />
    );
  }

  if (
    normalized.includes(
      'SECURITY',
    ) ||
    normalized.includes(
      'SAFE',
    ) ||
    normalized.includes(
      'PROTECTION',
    )
  ) {
    return (
      <ShieldDrawIcon
        theme={theme}
        progress={progress}
      />
    );
  }

  if (
    normalized.includes(
      'LOSS',
    ) ||
    normalized.includes(
      'FAIL',
    ) ||
    normalized.includes(
      'PROBLEM',
    )
  ) {
    return (
      <LossDrawIcon
        theme={theme}
        progress={progress}
      />
    );
  }

  if (
    normalized.includes(
      'USER',
    ) ||
    normalized.includes(
      'COMMUNITY',
    )
  ) {
    return (
      <UserIcon
        theme={theme}
      />
    );
  }

  if (
    normalized.includes(
      'WALLET',
    )
  ) {
    return (
      <WalletIcon
        theme={theme}
      />
    );
  }

  if (
    normalized.includes(
      'TOKEN',
    ) ||
    normalized.includes(
      'LIQUIDITY',
    ) ||
    normalized.includes(
      'FINANCE',
    ) ||
    normalized.includes(
      'MONEY',
    ) ||
    normalized.includes(
      'FUND',
    )
  ) {
    return (
      <CoinIcon
        theme={theme}
      />
    );
  }

  if (
    normalized.includes(
      'DATABASE',
    ) ||
    normalized.includes(
      'SERVER',
    ) ||
    normalized.includes(
      'INFRASTRUCTURE',
    )
  ) {
    return (
      <DatabaseIcon
        theme={theme}
      />
    );
  }

  if (
    normalized.includes(
      'DEVELOPER',
    ) ||
    normalized.includes(
      'DEV',
    ) ||
    normalized.includes(
      'DESIGN',
    ) ||
    normalized.includes(
      'MARKET',
    ) ||
    normalized.includes(
      'MANAGER',
    ) ||
    normalized.includes(
      'TECHNICAL',
    ) ||
    normalized.includes(
      'CREATIVE',
    ) ||
    normalized.includes(
      'OPERATIONAL',
    ) ||
    normalized.includes(
      'COMMUNICATION',
    ) ||
    normalized.includes(
      'CAREER',
    ) ||
    normalized.includes(
      'PROJECT',
    ) ||
    normalized.includes(
      'PRODUCT',
    ) ||
    normalized.includes(
      'RESEARCH',
    )
  ) {
    return (
      <CareerIcon
        theme={theme}
      />
    );
  }

  return (
    <GenericIcon
      theme={theme}
    />
  );
};


const DiagramCard: React.FC<{
  node: DiagramNode;
  rect: Rect;
  revealProgress: number;
  iconProgress: number;
  theme: Theme;
  isCenter: boolean;
}> = ({
  node,
  rect,
  revealProgress,
  iconProgress,
  theme,
  isCenter,
}) => {
  const mode =
    iconAnimationMode(
      node.label,
    );

  /*
   * Card establishes itself quickly.
   *
   * For draw/build icons, the canvas appears first and
   * the illustration continues animating inside it.
   */
  const cardProgress =
    mode === 'appear'
      ? revealProgress
      : clamp01(
          revealProgress *
            2.4,
        );

  const labelProgress =
    mode === 'appear'
      ? revealProgress
      : delayedProgress(
          iconProgress,
          0.62,
          1,
        );

  const lift =
    (1 - cardProgress) *
    18;

  const scale =
    0.84 +
    0.16 *
      cardProgress;

  const appearIconScale =
    0.72 +
    0.28 *
      revealProgress;

  return (
    <div
      style={{
        position:
          'absolute',

        left:
          rect.x,

        top:
          rect.y +
          lift,

        width:
          rect.w,

        height:
          rect.h,

        borderRadius:
          28,

        border:
          `${
            isCenter
              ? 5
              : 3
          }px solid ${
            theme.accent
          }`,

        backgroundColor:
          isCenter
            ? theme.background
            : 'rgba(255,255,255,0.92)',

        boxShadow:
          isCenter
            ? '0 22px 65px rgba(17,17,17,0.18)'
            : '0 16px 42px rgba(17,17,17,0.12)',

        opacity:
          cardProgress,

        transform:
          `scale(${scale})`,

        display:
          'flex',

        flexDirection:
          'column',

        alignItems:
          'center',

        justifyContent:
          'center',

        gap:
          8,

        padding:
          '16px 18px',

        boxSizing:
          'border-box',

        overflow:
          'hidden',
      }}
    >
      <div
        style={{
          height: 94,

          display:
            'flex',

          alignItems:
            'center',

          justifyContent:
            'center',

          opacity:
            mode ===
              'appear'
              ? revealProgress
              : 1,

          transform:
            mode ===
              'appear'
              ? `scale(${appearIconScale})`
              : 'scale(1)',
        }}
      >
        <SemanticIcon
          label={
            node.label
          }
          theme={
            theme
          }
          progress={
            iconProgress
          }
        />
      </div>

      <div
        style={{
          maxWidth:
            '100%',

          fontSize:
            clampFontSize(
              node.label,
            ),

          lineHeight:
            1.08,

          fontWeight:
            850,

          textAlign:
            'center',

          color:
            theme.foreground,

          letterSpacing:
            0.4,

          overflowWrap:
            'anywhere',

          opacity:
            labelProgress,

          transform:
            `translateY(${
              (1 -
                labelProgress) *
              7
            }px)`,
        }}
      >
        {node.label}
      </div>
    </div>
  );
};


const ComparisonDivider: React.FC<{
  theme: Theme;
  progress: number;
}> = ({
  theme,
  progress,
}) => (
  <div
    style={{
      position:
        'absolute',

      left:
        CANVAS_WIDTH / 2 -
        54,

      top:
        284,

      width:
        108,

      height:
        108,

      borderRadius:
        999,

      border:
        `4px solid ${
          theme.accent
        }`,

      background:
        theme.background,

      display:
        'flex',

      alignItems:
        'center',

      justifyContent:
        'center',

      color:
        theme.foreground,

      fontSize:
        28,

      fontWeight:
        900,

      opacity:
        progress,

      transform:
        `scale(${
          0.7 +
          progress *
            0.3
        })`,

      boxShadow:
        '0 12px 30px rgba(17,17,17,0.12)',
    }}
  >
    VS
  </div>
);


export const Diagram: React.FC<{
  diagram: DiagramData;
  fps: number;
  theme: Theme;
  actions: VisualAction[];
}> = ({
  diagram,
  fps,
  theme,
  actions,
}) => {
  const frame =
    useCurrentFrame();

  const {
    centers,
    rects,
  } = layoutDiagram(
    diagram,
  );

  const buildAction =
    actions.find(
      (action) =>
        action.type ===
        'buildDiagram',
    );

  const overallProgress =
    buildAction
      ? useProgress(
          frame,
          buildAction.startSec,
          buildAction.durationSec,
          fps,
        )
      : 1;

  const edges =
    diagram.edges as CompatibleEdge[];

  return (
    <div
      style={{
        position:
          'absolute',

        left: '50%',
        top: 0,

        width:
          CANVAS_WIDTH,

        height:
          CANVAS_HEIGHT,

        transform:
          'translateX(-50%)',

        overflow:
          'hidden',
      }}
    >
      <svg
        width={
          CANVAS_WIDTH
        }
        height={
          CANVAS_HEIGHT
        }
        style={{
          position:
            'absolute',

          inset: 0,

          overflow:
            'hidden',
        }}
      >
        {edges.map(
          (
            edge,
            index,
          ) => {
            const fromId =
              edgeFromId(
                edge,
              );

            const from =
              centers.get(
                fromId,
              );

            const to =
              centers.get(
                edge.to,
              );

            if (
              !from ||
              !to
            ) {
              return null;
            }

            const progress =
              edgeProgress(
                actions,
                fromId,
                edge.to,
                frame,
                fps,
              );

            return (
              <Arrow
                key={`
                  ${fromId}
                  -
                  ${edge.to}
                  -
                  ${index}
                `}
                from={from}
                to={to}
                progress={
                  progress
                }
                theme={
                  theme
                }
              />
            );
          },
        )}
      </svg>

      {diagram.kind ===
      'comparison' ? (
        <ComparisonDivider
          theme={
            theme
          }
          progress={
            overallProgress
          }
        />
      ) : null}

      {diagram.nodes.map(
        (
          node,
          index,
        ) => {
          const rect =
            rects.get(
              node.id,
            );

          if (!rect) {
            return null;
          }

          const mode =
            iconAnimationMode(
              node.label,
            );

          const revealProgress =
            nodeRevealProgress(
              actions,
              node.id,
              frame,
              fps,
            );

          const iconProgress =
            nodeIconProgress(
              actions,
              node.id,
              mode,
              frame,
              fps,
            );

          return (
            <DiagramCard
              key={
                node.id
              }
              node={
                node
              }
              rect={
                rect
              }
              revealProgress={
                revealProgress
              }
              iconProgress={
                iconProgress
              }
              theme={
                theme
              }
              isCenter={
                diagram.kind ===
                  'relationship' &&
                index === 0
              }
            />
          );
        },
      )}
    </div>
  );
};


export type {
  Point,
};