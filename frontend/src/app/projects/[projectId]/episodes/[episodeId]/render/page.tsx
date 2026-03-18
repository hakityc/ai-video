import { RenderStudio } from "@/components/render-studio";

export default async function RenderPage({ params }: { params: Promise<{ projectId: string; episodeId: string }> }) {
  const { projectId, episodeId } = await params;
  return <RenderStudio projectId={projectId} episodeId={episodeId} />;
}
