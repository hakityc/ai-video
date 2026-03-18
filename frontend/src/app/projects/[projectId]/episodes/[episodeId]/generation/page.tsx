import { GenerationStudio } from "@/components/generation-studio";

export default async function GenerationPage({ params }: { params: Promise<{ projectId: string; episodeId: string }> }) {
  const { projectId, episodeId } = await params;
  return <GenerationStudio projectId={projectId} episodeId={episodeId} />;
}
