import { Button } from '@/components/ui/button';
import { parseLegalWarnings } from '@/types/legalWarnings';
import type { IStep } from '@chainlit/react-client';
import { AlertTriangle, GitCompare } from 'lucide-react';
import { memo, useState } from 'react';

import ConflictWarningModal from './ConflictWarningModal';
import ValidityWarningModal from './ValidityWarningModal';

interface Props {
  message: IStep;
}

const LegalWarningButtons = memo(({ message }: Props) => {
  const [validityOpen, setValidityOpen] = useState(false);
  const [conflictOpen, setConflictOpen] = useState(false);

  if (message.streaming || message.type === 'user_message') {
    return null;
  }

  const warnings = parseLegalWarnings(
    message.metadata as Record<string, unknown> | undefined
  );
  if (!warnings) {
    return null;
  }

  const hasValidity =
    (warnings.validity?.expired_rows?.length ?? 0) > 0 ||
    (warnings.validity?.future_rows?.length ?? 0) > 0;
  const hasConflict = (warnings.conflict?.items?.length ?? 0) > 0;

  if (!hasValidity && !hasConflict) {
    return null;
  }

  return (
    <>
      <div className="flex flex-wrap items-center gap-2">
        {hasValidity && warnings.validity ? (
          <Button
            type="button"
            variant="outline"
            size="sm"
            className="h-8 gap-1.5"
            onClick={() => setValidityOpen(true)}
          >
            <AlertTriangle className="h-3.5 w-3.5" />
            Chi tiết cảnh báo hiệu lực
          </Button>
        ) : null}
        {hasConflict && warnings.conflict ? (
          <Button
            type="button"
            variant="outline"
            size="sm"
            className="h-8 gap-1.5"
            onClick={() => setConflictOpen(true)}
          >
            <GitCompare className="h-3.5 w-3.5" />
            Chi tiết cảnh báo mâu thuẫn
          </Button>
        ) : null}
      </div>

      {hasValidity && warnings.validity ? (
        <ValidityWarningModal
          open={validityOpen}
          onOpenChange={setValidityOpen}
          payload={warnings.validity}
        />
      ) : null}

      {hasConflict && warnings.conflict ? (
        <ConflictWarningModal
          open={conflictOpen}
          onOpenChange={setConflictOpen}
          payload={warnings.conflict}
        />
      ) : null}
    </>
  );
});

LegalWarningButtons.displayName = 'LegalWarningButtons';

export { LegalWarningButtons };
