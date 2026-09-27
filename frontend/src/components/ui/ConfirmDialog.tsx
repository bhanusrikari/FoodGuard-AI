import { Modal } from './Modal'
import { Button } from './Button'
import { useTranslation } from '@/i18n/LanguageContext'

interface ConfirmDialogProps {
  open: boolean
  title: string
  description: string
  confirmLabel?: string
  cancelLabel?: string
  destructive?: boolean
  isLoading?: boolean
  onConfirm: () => void
  onCancel: () => void
}

export function ConfirmDialog({
  open,
  title,
  description,
  confirmLabel,
  cancelLabel,
  destructive,
  isLoading,
  onConfirm,
  onCancel,
}: ConfirmDialogProps) {
  const t = useTranslation()
  return (
    <Modal open={open} onClose={onCancel} title={title} description={description} size="sm">
      <div className="flex justify-end gap-3">
        <Button variant="outline" onClick={onCancel} disabled={isLoading}>
          {cancelLabel ?? t('common.cancel')}
        </Button>
        <Button variant={destructive ? 'danger' : 'primary'} onClick={onConfirm} isLoading={isLoading}>
          {confirmLabel ?? t('common.confirm')}
        </Button>
      </div>
    </Modal>
  )
}
