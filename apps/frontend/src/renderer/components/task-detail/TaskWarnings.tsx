import { AlertTriangle, Play, RotateCcw, Loader2 } from 'lucide-react';
import { Button } from '../ui/button';

const EXIT_REASON_LABELS: Record<string, { label: string; description: string }> = {
  complete: { label: 'Completed', description: 'All subtasks finished successfully.' },
  rate_limit: { label: 'Rate Limited', description: 'API rate limit exceeded. Wait and restart.' },
  concurrency_limit: { label: 'Concurrency Error', description: 'Agent hit tool concurrency limit repeatedly.' },
  max_iterations: { label: 'Max Iterations', description: 'Reached iteration limit. Restart to continue.' },
};

interface TaskWarningsProps {
  isStuck: boolean;
  isIncomplete: boolean;
  isRecovering: boolean;
  taskProgress: { completed: number; total: number };
  exitReason?: { reason: string; subtask_id?: string; details?: string; timestamp?: string };
  onRecover: () => void;
  onResume: () => void;
}

export function TaskWarnings({
  isStuck,
  isIncomplete,
  isRecovering,
  taskProgress,
  exitReason,
  onRecover,
  onResume
}: TaskWarningsProps) {
  if (!isStuck && !isIncomplete) return null;

  const reasonInfo = exitReason ? EXIT_REASON_LABELS[exitReason.reason] : null;

  return (
    <>
      {/* Stuck Task Warning */}
      {isStuck && (
        <div className="rounded-xl border border-warning/30 bg-warning/10 p-4">
          <div className="flex items-start gap-3">
            <AlertTriangle className="h-5 w-5 text-warning shrink-0 mt-0.5" />
            <div className="flex-1">
              <h3 className="font-medium text-sm text-foreground mb-1">
                {reasonInfo ? `Agent Stopped: ${reasonInfo.label}` : 'Task Appears Stuck'}
              </h3>
              <p className="text-sm text-muted-foreground mb-3">
                {reasonInfo ? reasonInfo.description : 'This task is marked as running but no active process was found. This can happen if the app crashed or the process was terminated unexpectedly.'}
                {exitReason?.subtask_id && (
                  <span className="block mt-1 text-xs font-mono text-muted-foreground/70">
                    Last subtask: {exitReason.subtask_id}
                  </span>
                )}
                {exitReason?.details && (
                  <span className="block mt-0.5 text-xs text-muted-foreground/70">
                    {exitReason.details}
                  </span>
                )}
              </p>
              <Button
                variant="warning"
                size="sm"
                onClick={onRecover}
                disabled={isRecovering}
                className="w-full"
              >
                {isRecovering ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    Recovering...
                  </>
                ) : (
                  <>
                    <RotateCcw className="mr-2 h-4 w-4" />
                    Recover & Restart Task
                  </>
                )}
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* Incomplete Task Warning */}
      {isIncomplete && !isStuck && (
        <div className="rounded-xl border border-orange-500/30 bg-orange-500/10 p-4">
          <div className="flex items-start gap-3">
            <AlertTriangle className="h-5 w-5 text-orange-400 shrink-0 mt-0.5" />
            <div className="flex-1">
              <h3 className="font-medium text-sm text-foreground mb-1">
                Task Incomplete
              </h3>
              <p className="text-sm text-muted-foreground mb-3">
                This task has a spec and implementation plan but never completed any subtasks ({taskProgress.completed}/{taskProgress.total}).
                The process likely crashed during spec creation. Click Resume to continue implementation.
              </p>
              <Button
                variant="default"
                size="sm"
                onClick={onResume}
                className="w-full"
              >
                <Play className="mr-2 h-4 w-4" />
                Resume Task
              </Button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
