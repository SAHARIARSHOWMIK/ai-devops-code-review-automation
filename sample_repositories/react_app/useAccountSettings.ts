export async function saveSettings(input: any) {
  const response = await fetch('/api/settings', {
    method: 'POST',
    body: JSON.stringify(input),
  })
  return response.json()
}
