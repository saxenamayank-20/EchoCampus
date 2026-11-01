import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { BookOpen, FilePlus2, Send, Sparkles } from "lucide-react";
import { api } from "../../api/client";
import { PageHeader } from "../../components/Feedback";

const EXAMPLES = ["When does the hostel gate close on weekends?", "How much is the revaluation fee?",
  "What is the late fee for paying fees after the deadline?"];

// "ask before you complain": answers come only from the college policy pdfs, with page numbers
export default function Assistant() {
  const navigate = useNavigate();
  const [question, setQuestion] = useState("");
  const [chat, setChat] = useState([]);       // [{ q, a: response | null, error }]
  const [busy, setBusy] = useState(false);
  const end = useRef(null);
  useEffect(() => end.current?.scrollIntoView({ behavior: "smooth" }), [chat]);

  async function ask(q) {
    const text = (q ?? question).trim();
    if (text.length < 3 || busy) return;
    setQuestion("");
    setBusy(true);
    setChat((c) => [...c, { q: text, a: null }]);
    try {
      const a = await api("/assistant/ask", { method: "POST", body: { question: text } });
      setChat((c) => c.map((m, i) => (i === c.length - 1 ? { ...m, a } : m)));
    } catch (e) {
      setChat((c) => c.map((m, i) => (i === c.length - 1 ? { ...m, error: e.message } : m)));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="mx-auto flex max-w-3xl flex-col">
      <PageHeader title="Ask a question" subtitle="Answers come only from the college policy documents, with the page they're from." />

      <div className="card min-h-[24rem] space-y-5 p-5">
        {chat.length === 0 && (
          <div className="py-8 text-center">
            <Sparkles className="mx-auto mb-3 text-indigo-500" />
            <p className="text-sm text-slate-500">Try one of these:</p>
            <div className="mt-3 flex flex-wrap justify-center gap-2">
              {EXAMPLES.map((e) => <button key={e} onClick={() => ask(e)} className="btn-secondary px-3 py-1.5 text-xs">{e}</button>)}
            </div>
          </div>
        )}
        {chat.map((m, i) => (
          <div key={i} className="space-y-2">
            <p className="ml-auto w-fit max-w-[85%] rounded-2xl rounded-br-sm bg-indigo-600 px-4 py-2 text-sm text-white">{m.q}</p>
            <div className="max-w-[90%] rounded-2xl rounded-bl-sm bg-slate-100 px-4 py-3 text-sm dark:bg-slate-800">
              {!m.a && !m.error && <span className="animate-pulse text-slate-500">Looking in the policies…</span>}
              {m.error && <span className="text-red-600">{m.error}</span>}
              {m.a && (
                <>
                  <p className="whitespace-pre-wrap">{m.a.answer}</p>
                  {m.a.answered && (
                    <div className="mt-3 flex flex-wrap gap-1.5">
                      {m.a.sources.map((s) => (
                        <span key={s.n} title={s.snippet} className="inline-flex items-center gap-1 rounded-full bg-white px-2.5 py-1 text-xs text-slate-600 dark:bg-slate-900 dark:text-slate-300">
                          <BookOpen size={12} /> {s.document}, page {s.page}
                        </span>
                      ))}
                    </div>
                  )}
                  {!m.a.answered && (
                    <button className="btn-primary mt-3 px-3 py-1.5 text-xs"
                      onClick={() => navigate("/student/new", { state: { title: m.a.suggested_title } })}>
                      <FilePlus2 size={14} /> Raise a complaint about this
                    </button>
                  )}
                </>
              )}
            </div>
          </div>
        ))}
        <div ref={end} />
      </div>

      <form onSubmit={(e) => { e.preventDefault(); ask(); }} className="mt-4 flex gap-2">
        <input className="input" value={question} onChange={(e) => setQuestion(e.target.value)} maxLength={500}
          placeholder="Ask about hostel rules, exams, fees…" aria-label="Your question" />
        <button className="btn-primary" disabled={busy || question.trim().length < 3}><Send size={16} /></button>
      </form>
      <p className="mt-2 text-xs text-slate-500">The assistant never guesses: if the answer isn't in the documents, it says so.</p>
    </div>
  );
}
