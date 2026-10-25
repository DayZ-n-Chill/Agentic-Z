export type PanelStatus = {
  root: string | null
  mod: string | null
  isPMounted: boolean
  isDiagRunning: boolean
  checkedAt: number
}

export type PanelRun = {
  action: string
  ok: boolean
  outcome: 'done' | 'failed' | 'nothing found'
  detail: string
  // The ask field's plain-English answer, in markdown; absent when the model gave none.
  answer?: string
} | null

declare module 'claude-code' {
  interface PluginState {
    'agentic-z-panel': { status: PanelStatus | null; lastRun: PanelRun; busy: string | null }
  }
}
