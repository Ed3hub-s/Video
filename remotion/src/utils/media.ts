import {staticFile} from 'remotion';

// Media staged by the Python render bridge lives in remotion/public/media/...
// and must be loaded through staticFile() rather than file:// URLs.
export const resolveMedia = (path: string): string =>
  path.startsWith('media/') ? staticFile(path) : path;
