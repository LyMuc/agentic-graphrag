import {
  Ellipsis,
  Folder,
  FolderOpen,
  MessageSquarePlus,
  Pencil,
  Plus,
  Trash2,
} from "lucide-react";
import { useContext, useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { toast } from "sonner";

import {
  ChainlitContext,
  ClientError,
  IThread,
  ThreadHistory,
  useChatInteract,
  useChatMessages,
} from "@chainlit/react-client";

import { ExtendedChainlitAPI } from "@/api";
import { Loader } from "@/components/Loader";
import { cn } from "@/lib/utils";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { Button, buttonVariants } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Input } from "@/components/ui/input";
import {
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
} from "@/components/ui/sidebar";
import type { Project, ThreadSummary } from "@/types/projects";

import { ThreadList } from "./ThreadList";

type Props = {
  projects: Project[];
  isLoading: boolean;
  refreshVersion: number;
  reloadProjects: () => Promise<void>;
  notifyThreadsChanged: () => void;
};

const toThread = (thread: ThreadSummary): IThread => ({
  id: thread.id,
  name: thread.name,
  createdAt: thread.createdAt,
  metadata: {
    projectId: thread.projectId,
    updatedAt: thread.updatedAt,
  },
  steps: [],
});

export function Projects({
  projects,
  isLoading,
  refreshVersion,
  reloadProjects,
  notifyThreadsChanged,
}: Props) {
  const navigate = useNavigate();
  const apiClient = useContext(ChainlitContext) as ExtendedChainlitAPI;
  const { clear } = useChatInteract();
  const { threadId: currentThreadId } = useChatMessages();
  const [expandedProjectId, setExpandedProjectId] = useState<string>();
  const [projectThreads, setProjectThreads] = useState<ThreadSummary[]>([]);
  const [pageCursor, setPageCursor] = useState<string>();
  const [hasNextPage, setHasNextPage] = useState(false);
  const [isLoadingThreads, setIsLoadingThreads] = useState(false);
  const [createOpen, setCreateOpen] = useState(false);
  const [createName, setCreateName] = useState("");
  const [renameProject, setRenameProject] = useState<Project>();
  const [renameName, setRenameName] = useState("");
  const [deleteProject, setDeleteProject] = useState<Project>();

  const loadThreads = async (projectId: string, cursor?: string) => {
    setIsLoadingThreads(true);
    try {
      const page = await apiClient.listProjectThreads(projectId, 35, cursor);
      setProjectThreads((previous) =>
        cursor ? previous.concat(page.data) : page.data,
      );
      setPageCursor(page.pageInfo.endCursor);
      setHasNextPage(page.pageInfo.hasNextPage);
    } catch (error) {
      toast.error(error instanceof Error ? error.message : String(error));
    } finally {
      setIsLoadingThreads(false);
    }
  };

  useEffect(() => {
    if (expandedProjectId) {
      loadThreads(expandedProjectId);
    }
  }, [expandedProjectId, refreshVersion]);

  useEffect(() => {
    if (
      expandedProjectId &&
      !projects.some((project) => project.id === expandedProjectId)
    ) {
      setExpandedProjectId(undefined);
      setProjectThreads([]);
    }
  }, [projects, expandedProjectId]);

  const threadHistory = useMemo<ThreadHistory>(() => {
    const threads = projectThreads.map(toThread);
    return {
      threads,
      currentThreadId,
      timeGroupedThreads: { project: threads },
    };
  }, [projectThreads, currentThreadId]);

  const handleCreate = async () => {
    const name = createName.trim();
    if (!name) return;
    try {
      const project = await apiClient.createProject(name);
      setCreateOpen(false);
      setCreateName("");
      await reloadProjects();
      setExpandedProjectId(project.id);
    } catch (error) {
      toast.error(error instanceof Error ? error.message : String(error));
    }
  };

  const handleRename = async () => {
    const name = renameName.trim();
    if (!renameProject || !name) return;
    try {
      await apiClient.renameProject(renameProject.id, name);
      setRenameProject(undefined);
      setRenameName("");
      await reloadProjects();
    } catch (error) {
      toast.error(error instanceof Error ? error.message : String(error));
    }
  };

  const handleDelete = async () => {
    if (!deleteProject) return;
    const project = deleteProject;
    try {
      const result = await apiClient.deleteProject(project.id);
      if (
        currentThreadId &&
        result.deletedThreadIds.includes(currentThreadId)
      ) {
        clear();
        navigate("/");
      }
      setDeleteProject(undefined);
      setProjectThreads([]);
      setExpandedProjectId(undefined);
      await reloadProjects();
      notifyThreadsChanged();
      toast.success("Project deleted");
    } catch (error) {
      if (error instanceof ClientError) {
        toast.error(error.message);
      } else {
        toast.error(error instanceof Error ? error.message : String(error));
      }
    }
  };

  const startProjectChat = (projectId: string) => {
    clear();
    navigate(`/?project=${projectId}`);
  };

  return (
    <>
      <Dialog open={createOpen} onOpenChange={setCreateOpen}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>New project</DialogTitle>
            <DialogDescription>
              Create a project to organize related chats.
            </DialogDescription>
          </DialogHeader>
          <Input
            value={createName}
            maxLength={100}
            autoFocus
            placeholder="Project name"
            onChange={(event) => setCreateName(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === "Enter") handleCreate();
            }}
          />
          <DialogFooter>
            <Button variant="outline" onClick={() => setCreateOpen(false)}>
              Cancel
            </Button>
            <Button onClick={handleCreate} disabled={!createName.trim()}>
              Create
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog
        open={!!renameProject}
        onOpenChange={(open) => {
          if (!open) setRenameProject(undefined);
        }}
      >
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Rename project</DialogTitle>
            <DialogDescription>Enter a new project name.</DialogDescription>
          </DialogHeader>
          <Input
            value={renameName}
            maxLength={100}
            autoFocus
            onChange={(event) => setRenameName(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === "Enter") handleRename();
            }}
          />
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setRenameProject(undefined)}
            >
              Cancel
            </Button>
            <Button onClick={handleRename} disabled={!renameName.trim()}>
              Save
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <AlertDialog
        open={!!deleteProject}
        onOpenChange={(open) => {
          if (!open) setDeleteProject(undefined);
        }}
      >
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete project?</AlertDialogTitle>
            <AlertDialogDescription>
              This permanently deletes the project and every chat inside it.
              This action cannot be undone.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction onClick={handleDelete}>Delete</AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      <SidebarGroup className="max-h-[45vh] overflow-y-auto pb-0">
        <SidebarGroupLabel>Projects</SidebarGroupLabel>
        <SidebarGroupContent>
          <SidebarMenu>
            <SidebarMenuItem>
              <SidebarMenuButton
                className="h-9"
                onClick={() => setCreateOpen(true)}
              >
                <Plus className="!size-5" />
                <span>New project</span>
              </SidebarMenuButton>
            </SidebarMenuItem>

            {isLoading ? (
              <div className="flex justify-center p-2">
                <Loader />
              </div>
            ) : null}

            {projects.map((project) => {
              const expanded = project.id === expandedProjectId;
              return (
                <div key={project.id}>
                  <SidebarMenuItem>
                    <SidebarMenuButton
                      isActive={expanded}
                      className="relative h-9 group/project"
                      onClick={() =>
                        setExpandedProjectId(expanded ? undefined : project.id)
                      }
                    >
                      {expanded ? (
                        <FolderOpen className="!size-5 shrink-0" />
                      ) : (
                        <Folder className="!size-5 shrink-0" />
                      )}
                      <span className="truncate">{project.name}</span>
                      <DropdownMenu>
                        <DropdownMenuTrigger asChild>
                          <div
                            className={cn(
                              buttonVariants({
                                variant: "ghost",
                                size: "icon",
                              }),
                              "absolute right-0 h-8 w-8 opacity-0 group-hover/project:opacity-100 data-[state=open]:opacity-100",
                            )}
                            onClick={(event) => {
                              event.preventDefault();
                              event.stopPropagation();
                            }}
                          >
                            <Ellipsis className="!size-4" />
                          </div>
                        </DropdownMenuTrigger>
                        <DropdownMenuContent align="start">
                          <DropdownMenuItem
                            onClick={() => startProjectChat(project.id)}
                          >
                            <MessageSquarePlus />
                            New chat
                          </DropdownMenuItem>
                          <DropdownMenuItem
                            onClick={() => {
                              setRenameProject(project);
                              setRenameName(project.name);
                            }}
                          >
                            <Pencil />
                            Rename
                          </DropdownMenuItem>
                          <DropdownMenuItem
                            className="text-red-500 focus:text-red-500"
                            onClick={() => setDeleteProject(project)}
                          >
                            <Trash2 />
                            Delete
                          </DropdownMenuItem>
                        </DropdownMenuContent>
                      </DropdownMenu>
                    </SidebarMenuButton>
                  </SidebarMenuItem>

                  {expanded ? (
                    <div className="ml-4 border-l pl-1">
                      <SidebarMenuItem>
                        <SidebarMenuButton
                          className="h-9"
                          onClick={() => startProjectChat(project.id)}
                        >
                          <MessageSquarePlus className="!size-4" />
                          <span>New chat</span>
                        </SidebarMenuButton>
                      </SidebarMenuItem>
                      <ThreadList
                        threadHistory={threadHistory}
                        error={undefined}
                        isFetching={isLoadingThreads && !projectThreads.length}
                        isLoadingMore={
                          isLoadingThreads && !!projectThreads.length
                        }
                        projects={projects}
                        currentProjectId={project.id}
                        hideGroupLabels
                        onThreadsChanged={notifyThreadsChanged}
                      />
                      {hasNextPage && !isLoadingThreads ? (
                        <Button
                          variant="ghost"
                          size="sm"
                          className="w-full"
                          onClick={() => loadThreads(project.id, pageCursor)}
                        >
                          Load more
                        </Button>
                      ) : null}
                    </div>
                  ) : null}
                </div>
              );
            })}
          </SidebarMenu>
        </SidebarGroupContent>
      </SidebarGroup>
    </>
  );
}
