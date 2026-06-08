import getRouterBasename from "@/lib/router";
import { toast } from "sonner";

import { ChainlitAPI, ClientError } from "@chainlit/react-client";

import type { Project, ThreadSummaryPage } from "@/types/projects";

const devServer =
  (import.meta.env.VITE_API_URL || "http://localhost:8000") +
  getRouterBasename();
const url = import.meta.env.DEV
  ? devServer
  : window.origin + getRouterBasename();
const serverUrl = new URL(url);

const httpEndpoint = serverUrl.toString();

const on401 = () => {
  if (window.location.pathname !== getRouterBasename() + "/login") {
    // The credentials aren't correct, remove the token and redirect to login
    window.location.href = getRouterBasename() + "/login";
  }
};

const onError = (error: ClientError) => {
  toast.error(error.toString());
};

export class ExtendedChainlitAPI extends ChainlitAPI {
  async shareThread(
    threadId: string,
    isShared: boolean,
  ): Promise<{ success: boolean }> {
    const res = await this.put(`/project/thread/share`, {
      threadId,
      isShared,
    });
    return res.json();
  }

  async listProjects(): Promise<Project[]> {
    const res = await this.post("/project/projects/list", {});
    return res.json();
  }

  async createProject(name: string): Promise<Project> {
    const res = await this.post("/project/projects", { name });
    return res.json();
  }

  async renameProject(projectId: string, name: string): Promise<Project> {
    const res = await this.put(`/project/projects/${projectId}`, { name });
    return res.json();
  }

  async deleteProject(
    projectId: string,
  ): Promise<{ success: boolean; deletedThreadIds: string[] }> {
    const res = await this.delete(`/project/projects/${projectId}`, {});
    return res.json();
  }

  async listProjectThreads(
    projectId: string,
    first = 35,
    cursor?: string,
  ): Promise<ThreadSummaryPage> {
    const res = await this.post(`/project/projects/${projectId}/threads`, {
      first,
      cursor,
    });
    return res.json();
  }

  async listUnassignedThreads(
    first = 35,
    cursor?: string,
  ): Promise<ThreadSummaryPage> {
    const res = await this.post("/project/threads/unassigned", {
      first,
      cursor,
    });
    return res.json();
  }

  async assignThread(
    threadId: string,
    projectId: string | null,
  ): Promise<{ success: boolean }> {
    const res = await this.put(`/project/threads/${threadId}/project`, {
      projectId,
    });
    return res.json();
  }

  connectStreamableHttpMCP(
    sessionId: string,
    name: string,
    url: string,
    headers?: Record<string, string>,
  ) {
    // Assumes the backend expects { clientType, name, url }
    return fetch(
      new URL(
        "mcp",
        this.httpEndpoint.endsWith("/")
          ? this.httpEndpoint
          : `${this.httpEndpoint}/`,
      ),
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...(sessionId ? { "x-session-id": sessionId } : {}),
        },
        body: JSON.stringify({
          clientType: "streamable-http",
          name,
          url,
          sessionId,
          ...(headers ? { headers } : {}),
        }),
      },
    ).then(async (res) => {
      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.detail || "Failed to connect MCP");
      }
      return { success: true, mcp: data.mcp };
    });
  }
}

export const apiClient = new ExtendedChainlitAPI(
  httpEndpoint,
  "webapp",
  {}, // Optional - additionalQueryParams property.
  on401,
  onError,
);
