import { StoryboardStudio } from "@/components/storyboard-studio";

export default async function StoryboardPage({ params }: { params: Promise<{ projectId: string; episodeId: string }> }) {
  const { projectId, episodeId } = await params;
  return <StoryboardStudio projectId={projectId} episodeId={episodeId} />;
}
