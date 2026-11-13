export type ZipCheck = {
  // none: no repository checkout to compare (the plugin as installed)
  state: 'ok' | 'stale' | 'missing' | 'unknown' | 'none'
  detail: string
}

export type PanelData = {
  checkedAt: number
  // the output of `state.py status --json`, or null when the folder has no Sancho project
  status: Record<string, any> | null
  error: string | null
  cwd: string
  zip: ZipCheck
  // team mode: `state.py since --json --peek` (what the others did since you last looked)
  since?: Record<string, any> | null
}

declare module 'claude-code' {
  interface PluginState {
    sancho: { data: Shaped<PanelData | null> }
  }
}
