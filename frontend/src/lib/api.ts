import type { Episode, Project, Task } from "./types";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8080/api/v1";

async function handle<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const message = await response.text();
    throw new Error(message || `Request failed with ${response.status}`);
  }
  return response.json() as Promise<T>;
}

export async function apiGet<T>(path: string): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, { cache: "no-store" });
  return handle<T>(response);
}

export async function apiRequest<T>(path: string, init: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init.headers ?? {}),
    },
  });
  return handle<T>(response);
}

export async function uploadAsset(projectId: string, file: File, kind: string) {
  const formData = new FormData();
  formData.append("file", file);
  formData.append("kind", kind);
  const response = await fetch(`${API_BASE}/projects/${projectId}/assets:upload`, {
    method: "POST",
    body: formData,
  });
  return handle<{ id: string; url: string; kind: string }>(response);
}

export async function listProjects() {
  return apiGet<{ items: Project[] }>("/projects");
}

export async function getProject(projectId: string) {
  return apiGet<Project>(`/projects/${projectId}`);
}

export async function getEpisode(episodeId: string) {
  return apiGet<Episode>(`/episodes/${episodeId}`);
}

export async function getTask(taskId: string) {
  return apiGet<Task>(`/tasks/${taskId}`);
}
