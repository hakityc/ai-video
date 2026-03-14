export async function fetchJson<T>(url: string, init?: RequestInit): Promise<T> {
  const response = await fetch(url, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {}),
    },
  })

  if (!response.ok) {
    const responseText = await response.text()
    try {
      const payload = JSON.parse(responseText) as { detail?: string }
      if (payload.detail) {
        throw new Error(payload.detail)
      }
    } catch (error) {
       // Ignore JSON parse errors and throw original text
    }
    throw new Error(responseText || `请求失败: ${response.status}`)
  }

  return response.json() as Promise<T>
}
