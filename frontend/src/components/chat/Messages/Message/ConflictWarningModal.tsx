import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle
} from '@/components/ui/dialog';
import { Separator } from '@/components/ui/separator';
import type { ConflictWarningPayload } from '@/types/legalWarnings';

interface Props {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  payload: ConflictWarningPayload;
}

export default function ConflictWarningModal({
  open,
  onOpenChange,
  payload
}: Props) {
  const items = payload.items ?? [];

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-3xl max-h-[85vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Chi tiết cảnh báo mâu thuẫn</DialogTitle>
        </DialogHeader>

        <div className="space-y-6">
          {items.map((item, index) => (
            <section key={index} className="space-y-4">
              {index > 0 ? <Separator /> : null}

              <div>
                <h3 className="text-sm font-semibold mb-2">
                  Các điều khoản có xung đột
                </h3>
                <ul className="list-disc pl-5 space-y-1 text-sm">
                  {item.provisions.map((p) => (
                    <li key={p.id}>{p.name}</li>
                  ))}
                </ul>
              </div>

              <Separator />

              <div>
                <h3 className="text-sm font-semibold mb-2">
                  Mô tả ngắn về sự mâu thuẫn
                </h3>
                <p className="text-sm whitespace-pre-wrap">{item.summary}</p>
              </div>

              <Separator />

              <div>
                <h3 className="text-sm font-semibold mb-2">
                  Nội dung chi tiết các điều luật mâu thuẫn
                </h3>
                <div className="space-y-4">
                  {item.details.map((detail) => (
                    <div key={detail.id} className="space-y-1">
                      <p className="text-sm font-medium">{detail.name}</p>
                      <pre className="text-xs whitespace-pre-wrap font-mono bg-muted/50 rounded-md p-3 overflow-x-auto">
                        {detail.content}
                      </pre>
                    </div>
                  ))}
                </div>
              </div>
            </section>
          ))}
        </div>
      </DialogContent>
    </Dialog>
  );
}
