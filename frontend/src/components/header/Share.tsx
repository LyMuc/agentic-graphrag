import { hasMessage } from '@/lib/utils';
import { Share2 } from 'lucide-react';
import { useState } from 'react';

import { useAuth, useChatMessages, useConfig } from '@chainlit/react-client';

import ShareDialog from '@/components/share/ShareDialog';
import { Button } from '@/components/ui/button';
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger
} from '@/components/ui/tooltip';

import { Translator } from '../i18n';
import { canManageConversations } from '@/lib/auth';

export default function ShareButton() {
  const { messages, threadId } = useChatMessages();
  const [isOpen, setIsOpen] = useState(false);
  const { config } = useConfig();
  const { user } = useAuth();
  const canManage = canManageConversations(config, user);
  const threadSharingReady = Boolean((config as any)?.threadSharing);

  // Only show the button if messages, persistence is on, and feature is ready
  if (
    !hasMessage(messages) ||
    !canManage ||
    !threadId ||
    !threadSharingReady
  )
    return null;

  return (
    <>
      <TooltipProvider>
        <Tooltip>
          <TooltipTrigger asChild>
            <Button
              size="icon"
              variant="ghost"
              className="text-muted-foreground hover:text-muted-foreground"
              onClick={() => setIsOpen(true)}
            >
              <Share2 className="!size-4" />
            </Button>
          </TooltipTrigger>
          <TooltipContent>
            <p>
              <Translator path="threadHistory.thread.menu.share" />
            </p>
          </TooltipContent>
        </Tooltip>
      </TooltipProvider>

      <ShareDialog open={isOpen} onOpenChange={setIsOpen} threadId={threadId} />
    </>
  );
}
