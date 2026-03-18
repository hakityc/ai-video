import { CharacterStudio } from "@/components/character-studio";

export default async function CharactersPage({ params }: { params: Promise<{ projectId: string }> }) {
  const { projectId } = await params;
  return <CharacterStudio projectId={projectId} />;
}
