import { useRef, useState } from 'react';
import { sendAssistantChat } from '@/services';

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  executedTools?: string[];
  clarification?: boolean;
  options?: string[];
  error?: boolean;
}

let idCounter = 0;
const newId = () => String(++idCounter);

export default function Assistant() {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: newId(),
      role: 'assistant',
      content:
        "Bonjour ! Je suis votre comptable IA. Je peux créer des clients, des contrats d'assurance, encaisser des primes ou vous renseigner sur les soldes et contrats. Comment puis-je vous aider ?",
    },
  ]);
  const [input, setInput] = useState('');
  const [pending, setPending] = useState(false);
  const sessionRef = useRef<string | null>(null);

  const pushMessage = (msg: Omit<Message, 'id'>) => setMessages(prev => [...prev, { ...msg, id: newId() }]);

  const send = async (text: string) => {
    const trimmed = text.trim();
    if (!trimmed || pending) return;
    pushMessage({ role: 'user', content: trimmed });
    setInput('');
    setPending(true);

    try {
      const reply = await sendAssistantChat({
        message: trimmed,
        session_id: sessionRef.current,
      });
      sessionRef.current = reply.session_id;
      pushMessage({
        role: 'assistant',
        content: reply.text,
        executedTools: reply.executed_tools,
        clarification: reply.clarification,
        options: reply.options,
      });
    } catch (err) {
      const detail = err instanceof Error ? err.message : 'Impossible de contacter l\'assistant.';
      pushMessage({ role: 'assistant', content: `Erreur : ${detail}`, error: true });
    } finally {
      setPending(false);
    }
  };

  const renderContent = (content: string) => {
    const lines = content.split('\n');
    return lines.map((line, i) => {
      const isBullet = /^\s*[•-]\s/.test(line);
      const isNumbered = /^\s*\d+\)/.test(line);
      const body = line.replace(/^\s*[•-]\s/, '').replace(/^\s*\d+\)\s*/, '');
      const parts = body.split(/\*\*(.+?)\*\*/g);
      const rendered = parts.map((part, j) =>
        j % 2 === 1 ? <strong key={j}>{part}</strong> : part,
      );
      if (isBullet || isNumbered) {
        return (
          <p key={i} className="mt-1 p-4 text-slate-800">
            <span className="text-navy-500 p-2">{isBullet ? '•' : '–'}</span>
            {rendered}
          </p>
        );
      }
      return (
        <p key={i} className={i > 0 && line.trim() ? 'p-2' : ''}>
          {rendered}
        </p>
      );
    });
  };

  const onOptionClick = (index: number) => {
    void send(String(index + 1));
  };

  return (
    <div className="h-full flex flex-col p-6 max-w-3xl mx-auto w-full">

      {/* Messages */}
      <div className="flex-1 overflow-y-auto space-y-4 mb-4 min-h-0">
        {messages.map(msg => (
          <div key={msg.id} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
            {msg.role === 'assistant' && (
              <div className="w-7 h-7 rounded-full bg-navy-800 flex items-center justify-center text-white text-xs shrink-0 mr-2 mt-1">✦</div>
            )}
            <div className={`max-w-[80%] rounded-2xl p-4 text-sm leading-relaxed ${msg.role === 'user'
              ? 'bg-navy-800 text-white rounded-tr-sm'
              : msg.error
                ? 'bg-red-50 border border-red-200 text-red-800 rounded-tl-sm'
                : 'bg-white border border-slate-200 text-slate-800 rounded-tl-sm'
              }`}>
              <div className="leading-relaxed">{renderContent(msg.content)}</div>

              {msg.executedTools && msg.executedTools.length > 0 && (
                <div className="mt-2 inline-flex items-center gap-1 text-xs font-semibold text-emerald-700 bg-emerald-50 border border-emerald-200 rounded-full px-2">
                  ✓ Enregistrée
                  <span className="font-normal text-emerald-600"> · {msg.executedTools.join(', ')}</span>
                </div>
              )}

              {msg.clarification && msg.options && msg.options.length > 0 && (
                <div className="flex flex-wrap p-2">
                  {msg.options.map((opt, i) => (
                    <button
                      key={i}
                      onClick={() => onOptionClick(i)}
                      disabled={pending}
                      className="text-xs bg-navy-50 border border-navy-200 text-navy-800 rounded-lg p-2 py-1 hover:bg-navy-100 disabled:opacity-40 transition-all"
                    >
                      {i + 1}. {opt}
                    </button>
                  ))}
                </div>
              )}
            </div>
          </div>
        ))}

        {pending && (
          <div className="flex justify-start">
            <div className="w-7 h-7 rounded-full bg-navy-800 flex items-center justify-center text-white text-xs shrink-0 mr-2 mt-1">✦</div>
            <div className="bg-white border border-slate-200 rounded-2xl rounded-tl-sm p-4">
              <div className="flex gap-1 items-center">
                <span className="w-1.5 h-1.5 bg-slate-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                <span className="w-1.5 h-1.5 bg-slate-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                <span className="w-1.5 h-1.5 bg-slate-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Input */}
      <div className="flex p-2 bg-white border border-slate-200 rounded-2xl focus-within:border-navy-400 transition-colors">
        <input
          type="text"
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); void send(input); } }}
          placeholder="Demander à mon comptable IA…"
          className="flex-1 px-4 py-2 text-sm text-slate-700 placeholder-slate-400 outline-none bg-transparent"
          disabled={pending}
        />
        <button
          onClick={() => void send(input)}
          disabled={!input.trim() || pending}
          className="bg-navy-800 text-white rounded-xl px-4 py-2 text-sm font-medium hover:bg-navy-700 disabled:opacity-40 disabled:cursor-not-allowed transition-all"
        >
          Envoyer
        </button>
      </div>

      <div className="text-xs text-slate-400 text-center mt-2">
        Les opérations enregistrées sont journalisées (piste d'audit).
      </div>
    </div>
  );
}