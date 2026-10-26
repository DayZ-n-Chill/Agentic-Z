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
  // The question an ask or deep dive answered, for Deep dive and Continue in chat.
  question?: string
} | null

// The ask card's picks: citations to read, lines per excerpt, words in the answer.
export type AskSettings = { topK: string; excerptLines: string; words: string }

// The pane's tabs: the buttons, the last vanilla answer, and the API keys.
export type PanelTab = 'panel' | 'answer' | 'keys'

// Where each key the Keys tab knows comes from, and its last four characters.
// The keys themselves never go in the session state, only in the panel's store.
export type KeyStatus = Record<string, { source: 'panel' | 'environment'; tail: string } | null>

declare module 'claude-code' {
  interface PluginState {
    'agentic-z-panel': {
      status: PanelStatus | null
      lastRun: PanelRun
      busy: string | null
      newVersion: string | null
      askSettings: AskSettings
      lastAnswer: PanelRun
      tab: PanelTab
      keys: KeyStatus
    }
  }
}
