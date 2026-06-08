import { useCallback, useContext, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";

import { ChainlitContext } from "@chainlit/react-client";

import { ExtendedChainlitAPI } from "@/api";
import SidebarTrigger from "@/components/header/SidebarTrigger";
import { Sidebar, SidebarHeader, SidebarRail } from "@/components/ui/sidebar";
import type { Project } from "@/types/projects";

import NewChatButton from "../header/NewChat";
import { Projects } from "./Projects";
import SearchChats from "./Search";
import { ThreadHistory } from "./ThreadHistory";

export default function LeftSidebar({
  ...props
}: React.ComponentProps<typeof Sidebar>) {
  const navigate = useNavigate();
  const apiClient = useContext(ChainlitContext) as ExtendedChainlitAPI;
  const [projects, setProjects] = useState<Project[]>([]);
  const [isLoadingProjects, setIsLoadingProjects] = useState(true);
  const [refreshVersion, setRefreshVersion] = useState(0);

  const reloadProjects = useCallback(async () => {
    setIsLoadingProjects(true);
    try {
      setProjects(await apiClient.listProjects());
    } finally {
      setIsLoadingProjects(false);
    }
  }, [apiClient]);

  useEffect(() => {
    reloadProjects();
  }, [reloadProjects]);

  const notifyThreadsChanged = () => {
    setRefreshVersion((version) => version + 1);
    reloadProjects();
  };

  return (
    <Sidebar {...props} className="border-none">
      <SidebarHeader className="py-3">
        <div className="flex items-center justify-between">
          <SidebarTrigger />
          <div className="flex items-center">
            <SearchChats />
            <NewChatButton navigate={navigate} />
          </div>
        </div>
      </SidebarHeader>
      <Projects
        projects={projects}
        isLoading={isLoadingProjects}
        refreshVersion={refreshVersion}
        reloadProjects={reloadProjects}
        notifyThreadsChanged={notifyThreadsChanged}
      />
      <ThreadHistory
        projects={projects}
        refreshVersion={refreshVersion}
        notifyThreadsChanged={notifyThreadsChanged}
      />
      <SidebarRail />
    </Sidebar>
  );
}
