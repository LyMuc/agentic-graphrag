import { uniqBy } from "lodash";
import { useContext, useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useRecoilState } from "recoil";

import {
  ChainlitContext,
  IThread,
  threadHistoryState,
  useChatMessages,
} from "@chainlit/react-client";

import { ExtendedChainlitAPI } from "@/api";
import {
  SidebarContent,
  SidebarGroup,
  SidebarMenu,
} from "@/components/ui/sidebar";

import { ThreadList } from "./ThreadList";
import type { Project, ThreadSummary } from "@/types/projects";

const BATCH_SIZE = 35;
let _scrollTop = 0;

type Props = {
  projects: Project[];
  refreshVersion: number;
  notifyThreadsChanged: () => void;
};

const toThread = (thread: ThreadSummary): IThread => ({
  id: thread.id,
  name: thread.name,
  createdAt: thread.createdAt,
  metadata: { updatedAt: thread.updatedAt },
  steps: [],
});

export function ThreadHistory({
  projects,
  refreshVersion,
  notifyThreadsChanged,
}: Props) {
  const navigate = useNavigate();
  const scrollRef = useRef<HTMLDivElement>(null);
  const apiClient = useContext(ChainlitContext) as ExtendedChainlitAPI;
  const { firstInteraction, messages, threadId } = useChatMessages();
  const [threadHistory, setThreadHistory] = useRecoilState(threadHistoryState);
  const [error, setError] = useState<string>();
  const [isLoadingMore, setIsLoadingMore] = useState(false);
  const [isFetching, setIsFetching] = useState(false);
  const [shouldLoadMore, setShouldLoadMore] = useState(false);
  const prevMessageCountRef = useRef(0);

  // Restore scroll position
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = _scrollTop;
    }
  }, []);

  // Handle first interaction
  useEffect(() => {
    const handleFirstInteraction = async () => {
      if (!firstInteraction) return;

      const isActualResume =
        firstInteraction === "resume" &&
        messages[0]?.output.toLowerCase() !== "resume";

      if (isActualResume) return;

      const currentPage = new URL(window.location.href);
      const projectId = currentPage.searchParams.get("project");
      if (threadId && projectId && firstInteraction !== "resume") {
        const delays = [100, 250, 500];
        let assigned = false;
        for (let attempt = 0; attempt < delays.length; attempt++) {
          try {
            await apiClient.assignThread(threadId, projectId);
            assigned = true;
            break;
          } catch (error) {
            if (attempt === delays.length - 1) throw error;
            await new Promise((resolve) =>
              setTimeout(resolve, delays[attempt]),
            );
          }
        }
        if (assigned) {
          notifyThreadsChanged();
          navigate(`/thread/${threadId}?project=${projectId}`);
          return;
        }
      }

      await fetchThreads(undefined, true);
      if (threadId && currentPage.pathname === "/") {
        navigate(`/thread/${threadId}`);
      }
    };

    handleFirstInteraction().catch((err) => {
      setError(err instanceof Error ? err.message : "Failed to assign project");
    });
  }, [firstInteraction]);

  // Reorder thread to top when a new message is sent in the current thread
  useEffect(() => {
    const currentCount = messages.length;
    const prevCount = prevMessageCountRef.current;
    prevMessageCountRef.current = currentCount;

    if (
      threadId &&
      currentCount > prevCount &&
      prevCount > 0 &&
      threadHistory?.threads
    ) {
      const lastMessage = messages[currentCount - 1];
      if (lastMessage?.type === "user_message") {
        setThreadHistory((prev) => {
          if (!prev?.threads) return prev;
          const threadIndex = prev.threads.findIndex((t) => t.id === threadId);
          if (threadIndex <= 0) return prev; // Already at top or not found
          const updatedThreads = [...prev.threads];
          updatedThreads[threadIndex] = {
            ...updatedThreads[threadIndex],
            createdAt: new Date().toISOString(),
          };
          return { ...prev, threads: updatedThreads };
        });
      }
    }
  }, [messages.length, threadId]);

  const handleScroll = () => {
    if (!scrollRef.current) return;
    const { scrollHeight, clientHeight, scrollTop } = scrollRef.current;
    const atBottom = scrollTop + clientHeight >= scrollHeight - 10;

    _scrollTop = scrollTop;
    setShouldLoadMore(atBottom);
  };

  const fetchThreads = async (
    cursor?: string | number,
    isLoadingMore = false,
  ) => {
    try {
      setIsLoadingMore(!!cursor || isLoadingMore);
      setIsFetching(!cursor && !isLoadingMore);

      const { pageInfo, data } = await apiClient.listUnassignedThreads(
        BATCH_SIZE,
        cursor ? String(cursor) : undefined,
      );
      const threads = data.map(toThread);

      setError(undefined);

      // Prevent duplicate threads
      const allThreads = uniqBy(
        cursor ? threadHistory?.threads?.concat(threads) : threads,
        "id",
      );

      if (allThreads) {
        setThreadHistory((prev) => ({
          ...prev,
          pageInfo,
          threads: allThreads,
        }));
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unknown error occurred");
    } finally {
      setShouldLoadMore(false);
      setIsLoadingMore(false);
      setIsFetching(false);
    }
  };

  // Initial fetch and refresh after project/thread mutations.
  useEffect(() => {
    fetchThreads();
  }, [refreshVersion]);

  // Handle infinite scroll
  useEffect(() => {
    if (threadHistory?.pageInfo) {
      const { hasNextPage, endCursor } = threadHistory.pageInfo;

      if (shouldLoadMore && !isLoadingMore && hasNextPage && endCursor) {
        fetchThreads(endCursor);
      }
    }
  }, [shouldLoadMore, isLoadingMore, threadHistory]);

  return (
    <SidebarContent onScroll={handleScroll} ref={scrollRef}>
      <SidebarGroup>
        <SidebarMenu>
          {threadHistory ? (
            <div id="thread-history" className="flex-grow">
              <ThreadList
                threadHistory={threadHistory}
                error={error}
                isFetching={isFetching}
                isLoadingMore={isLoadingMore}
                projects={projects}
                currentProjectId={null}
                onThreadsChanged={notifyThreadsChanged}
              />
            </div>
          ) : null}
        </SidebarMenu>
      </SidebarGroup>
    </SidebarContent>
  );
}
