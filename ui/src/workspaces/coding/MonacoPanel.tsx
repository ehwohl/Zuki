import { useRef, useState } from 'react'
import MonacoEditor, { type OnMount } from '@monaco-editor/react'
import type * as Monaco from 'monaco-editor'
import { bridge } from '../../bridge/ws'

const LANGUAGES = ['python', 'typescript', 'javascript', 'bash', 'json', 'yaml'] as const
type Lang = (typeof LANGUAGES)[number]

export default function MonacoPanel() {
  const editorRef = useRef<Monaco.editor.IStandaloneCodeEditor | null>(null)
  const [lang, setLang] = useState<Lang>('python')

  const handleMount: OnMount = (editor, monaco) => {
    editorRef.current = editor
    editor.addCommand(
      monaco.KeyMod.CtrlCmd | monaco.KeyCode.Enter,
      () => runCode(),
    )
  }

  function runCode() {
    const code = editorRef.current?.getValue() ?? ''
    if (!code.trim()) return
    bridge.send('command', {
      text: `code ${lang} run`,
      workspace: 'coding',
      tenant: 'self',
      code,
    })
  }

  return (
    <div className="flex flex-col h-full">
      {/* toolbar */}
      <div
        className="flex items-center gap-2 px-2 flex-shrink-0 border-b border-[var(--border-color)]"
        style={{ height: 28 }}
      >
        <select
          value={lang}
          onChange={(e) => setLang(e.target.value as Lang)}
          className="font-mono text-[0.6rem] bg-transparent text-[var(--text-secondary)] border border-[var(--border-color)] px-1 rounded cursor-pointer hover:border-[var(--accent-primary)] focus:outline-none focus:border-[var(--accent-primary)] transition-colors"
        >
          {LANGUAGES.map((l) => (
            <option key={l} value={l} style={{ background: 'var(--bg-elevated)' }}>
              {l}
            </option>
          ))}
        </select>

        <span className="flex-1" />

        <span className="font-mono text-[0.55rem] text-[var(--text-secondary)] opacity-40 select-none">
          CTRL+ENTER to run
        </span>

        <button
          onClick={runCode}
          className="font-mono text-[0.6rem] tracking-widest uppercase px-2 py-0.5 border border-[var(--accent-primary)] text-[var(--accent-primary)] hover:bg-[var(--accent-primary)] hover:text-[var(--bg-base)] transition-colors rounded-sm"
        >
          RUN
        </button>
      </div>

      {/* editor */}
      <div className="flex-1 min-h-0">
        <MonacoEditor
          height="100%"
          language={lang}
          theme="vs-dark"
          onMount={handleMount}
          options={{
            fontSize: 12,
            fontFamily: '"JetBrains Mono", monospace',
            minimap: { enabled: false },
            scrollBeyondLastLine: false,
            lineNumbers: 'on',
            glyphMargin: false,
            folding: false,
            lineDecorationsWidth: 8,
            lineNumbersMinChars: 3,
            renderLineHighlight: 'line',
            overviewRulerLanes: 0,
            hideCursorInOverviewRuler: true,
            scrollbar: {
              vertical: 'auto',
              horizontal: 'hidden',
              verticalScrollbarSize: 6,
            },
            padding: { top: 8, bottom: 8 },
          }}
        />
      </div>
    </div>
  )
}
