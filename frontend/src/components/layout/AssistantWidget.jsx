import { useRef, useState } from "react"
import { askAssistant } from "../../services/api"

const SUGGESTIONS = [
  "Which place is riskiest?",
  "How many active alerts?",
  "Is Uttarakhand safe?",
]

/**
 * A small, globally-mounted Q&A widget backed entirely by real database
 * queries (GET /assistant/ask) — no LLM, no external API key. It only
 * ever shows answers the backend actually returned; it never invents
 * text client-side. Kept out of the way (a floating button) rather than
 * a permanent panel, matching this app's dense, data-first layout.
 */
export default function AssistantWidget() {
  const [open, setOpen] = useState(false)
  const [input, setInput] = useState("")
  const [messages, setMessages] = useState([])
  const [loading, setLoading] = useState(false)
  const listRef = useRef(null)

  function scrollToBottom() {
    requestAnimationFrame(() => {
      listRef.current?.scrollTo({ top: listRef.current.scrollHeight })
    })
  }

  async function send(question) {
    const text = (question ?? input).trim()
    if (!text || loading) return
    setInput("")
    setMessages((prev) => [...prev, { role: "user", text }])
    setLoading(true)
    scrollToBottom()
    try {
      const result = await askAssistant(text)
      setMessages((prev) => [...prev, { role: "assistant", text: result.answer }])
    } catch {
      setMessages((prev) => [
        ...prev,
        { role: "assistant", text: "Couldn't reach the backend to answer that — check System Status." },
      ])
    } finally {
      setLoading(false)
      scrollToBottom()
    }
  }

  return (
    <>
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
        aria-label={open ? "Close assistant" : "Open assistant"}
        className="fixed bottom-5 right-5 z-[1500] flex h-12 w-12 items-center justify-center rounded-full bg-slate-900 text-white shadow-lg hover:bg-slate-800 dark:bg-slate-100 dark:text-slate-900 dark:hover:bg-white"
      >
        {open ? (
          <span aria-hidden="true" className="text-xl leading-none">×</span>
        ) : (
          <span aria-hidden="true" className="text-lg leading-none">?</span>
        )}
      </button>

      {open && (
        <div className="fixed bottom-20 right-5 z-[1500] flex h-[28rem] w-80 flex-col overflow-hidden rounded-lg border border-slate-200 bg-white shadow-xl dark:border-slate-700 dark:bg-slate-900">
          <div className="border-b border-slate-200 px-3 py-2.5 dark:border-slate-700">
            <div className="text-sm font-semibold text-slate-800 dark:text-slate-200">Ask BHUSURAKSHA</div>
            <div className="text-[11px] text-slate-400 dark:text-slate-500">
              Answers come only from this system's real data — never guessed.
            </div>
          </div>

          <div ref={listRef} className="flex-1 space-y-2 overflow-y-auto px-3 py-2.5">
            {messages.length === 0 && (
              <div className="space-y-1.5">
                <p className="text-xs text-slate-500 dark:text-slate-400">Try asking:</p>
                {SUGGESTIONS.map((s) => (
                  <button
                    key={s}
                    type="button"
                    onClick={() => send(s)}
                    className="block w-full rounded-md border border-slate-200 bg-slate-50 px-2.5 py-1.5 text-left text-xs text-slate-600 hover:bg-slate-100 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-300 dark:hover:bg-slate-700"
                  >
                    {s}
                  </button>
                ))}
              </div>
            )}
            {messages.map((m, i) => (
              <div
                key={i}
                className={`max-w-[85%] whitespace-pre-line rounded-lg px-2.5 py-1.5 text-xs ${
                  m.role === "user"
                    ? "ml-auto bg-slate-900 text-white dark:bg-slate-100 dark:text-slate-900"
                    : "bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-300"
                }`}
              >
                {m.text}
              </div>
            ))}
            {loading && <div className="text-xs text-slate-400 dark:text-slate-500">Thinking…</div>}
          </div>

          <form
            onSubmit={(e) => {
              e.preventDefault()
              send()
            }}
            className="flex items-center gap-1.5 border-t border-slate-200 p-2 dark:border-slate-700"
          >
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Ask a question…"
              aria-label="Ask the assistant a question"
              className="flex-1 rounded-md border border-slate-200 bg-white px-2.5 py-1.5 text-xs text-slate-700 focus:outline-none focus:ring-1 focus:ring-slate-400 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-300"
            />
            <button
              type="submit"
              disabled={loading || !input.trim()}
              className="rounded-md bg-slate-900 px-2.5 py-1.5 text-xs font-medium text-white disabled:cursor-not-allowed disabled:opacity-50 dark:bg-slate-100 dark:text-slate-900"
            >
              Ask
            </button>
          </form>
        </div>
      )}
    </>
  )
}
