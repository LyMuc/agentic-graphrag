import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle
} from '@/components/ui/dialog';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow
} from '@/components/ui/table';
import type { ValidityWarningPayload } from '@/types/legalWarnings';

interface Props {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  payload: ValidityWarningPayload;
}

function ContentLink({ url }: { url?: string | null }) {
  if (!url) {
    return <span className="text-muted-foreground">—</span>;
  }
  return (
    <a
      href={url}
      target="_blank"
      rel="noopener noreferrer"
      className="text-primary hover:underline"
    >
      Xem trên thuvienphapluat.vn
    </a>
  );
}

export default function ValidityWarningModal({
  open,
  onOpenChange,
  payload
}: Props) {
  const expiredRows = payload.expired_rows ?? [];
  const futureRows = payload.future_rows ?? [];

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-4xl max-h-[85vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Chi tiết cảnh báo hiệu lực</DialogTitle>
        </DialogHeader>

        {expiredRows.length > 0 ? (
          <section className="space-y-3">
            <h3 className="text-sm font-semibold">
              Căn cứ hết hiệu lực / được thay thế
            </h3>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Tên căn cứ pháp lý</TableHead>
                  <TableHead>Ngày hết hiệu lực</TableHead>
                  <TableHead>Tên căn cứ thay thế</TableHead>
                  <TableHead>Ngày có hiệu lực (thay thế)</TableHead>
                  <TableHead>Nội dung căn cứ thay thế</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {expiredRows.map((row) => (
                  <TableRow key={row.basis_id}>
                    <TableCell className="font-medium">{row.basis_name}</TableCell>
                    <TableCell>{row.expiry_date}</TableCell>
                    <TableCell>{row.replacement_name}</TableCell>
                    <TableCell>{row.replacement_effective_date}</TableCell>
                    <TableCell>
                      <ContentLink url={row.replacement_content_url} />
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </section>
        ) : null}

        {futureRows.length > 0 ? (
          <section className="space-y-3">
            <h3 className="text-sm font-semibold">
              Văn bản đã ban hành, chưa có hiệu lực
            </h3>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Tên căn cứ</TableHead>
                  <TableHead>Ngày ban hành</TableHead>
                  <TableHead>Ngày hiệu lực</TableHead>
                  <TableHead>Loại tác động</TableHead>
                  <TableHead>Căn cứ bị tác động</TableHead>
                  <TableHead>Nội dung</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {futureRows.map((row) => (
                  <TableRow
                    key={`${row.source_id}-${row.impacted_basis_id}-${row.impact_type}`}
                  >
                    <TableCell className="font-medium">{row.basis_name}</TableCell>
                    <TableCell>{row.issued_date}</TableCell>
                    <TableCell>{row.effective_date}</TableCell>
                    <TableCell>{row.impact_type}</TableCell>
                    <TableCell>{row.impacted_basis_name}</TableCell>
                    <TableCell>
                      <ContentLink url={row.content_url} />
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </section>
        ) : null}
      </DialogContent>
    </Dialog>
  );
}
