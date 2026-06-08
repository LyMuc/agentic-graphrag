import { IPageInfo } from "@chainlit/react-client";

export type Project = {
  id: string;
  name: string;
  createdAt: string;
  updatedAt: string;
  threadCount: number;
};

export type ThreadSummary = {
  id: string;
  name?: string;
  createdAt: string;
  updatedAt: string;
  projectId: string | null;
};

export type ThreadSummaryPage = {
  pageInfo: IPageInfo;
  data: ThreadSummary[];
};
