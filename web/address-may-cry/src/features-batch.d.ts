import React from 'react';
import type { BatchItem } from './shared/contracts';

declare module '*/features/batch/BatchWorkspace' {
  export interface BatchWorkspaceProps {
    onInspect?: (item: BatchItem) => void;
  }
  const BatchWorkspace: React.FC<BatchWorkspaceProps>;
  export default BatchWorkspace;
}
