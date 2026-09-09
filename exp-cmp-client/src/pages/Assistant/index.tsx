import { useRef, useState } from 'react';
import { fetchAssistantIntents, sendAssistantChat } from '@/services';
import { useApiQuery } from '@/hooks/useApiQuery';

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  intent?: string | null;
  executed?: boolean;
  clarification?: boolean;
  options?: string[];
  error?: boolean;
}

const FALLBACK_INTENTS = [
  { operation: 'create_client', label: 'Créer un client', example: 'Créer un client Moussa Camara' },
  { operation: 'create_contract', label: 'Créer un contrat', example: 'Nouveau contrat pour Tagoun, matricule MAT-100, prime 100 000' },
  { operation: 'record_payment', label: 'Encaisser une prime', example: 'Encaisser 40 000 de Tagoun pour le contrat MAT-E2E' },
  { operation: 'get_balance', label: "Consulter le solde d'une caisse", example: 'Solde de la caisse' },
  { operation: 'get_remaining', label: "Reste à payer d'un contrat", example: 'Reste à payer du contrat MAT-E2E' },
  { operation: 'get_client_info', label: "Consulter les infos d'un client", example: 'Infos du client Tagoun' },
  { operation: 'get_contract_info', label: "Consulter les infos d'un contrat", example: 'Infos du contrat MAT-E2E' },
  { operation: 'help', label: 'Aide', example: 'aide' },
];

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

  const { data: intents } = useApiQuery(fetchAssistantIntents, []);
  const suggestions = intents && intents.length > 0 ? intents : FALLBACK_INTENTS;

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
        intent: reply.intent,
        executed: reply.executed,
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

      {/* Suggestions dynamiques */}
      <div className="mb-4">
        <div className="text-xs font-semibold text-slate-400 uppercase tracking-widest mb-2">Questions suggérées</div>
        <div className="flex flex-wrap gap-2">
          {suggestions.map(s => (
            <button
              key={s.operation}
              onClick={() => send(s.example)}
              title={s.label}
              className="text-xs bg-white border border-slate-200 text-slate-600 rounded-lg p-2 hover:border-navy-300 hover:text-navy-700 transition-all"
            >
              {s.example}
            </button>
          ))}
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto space-y-4 mb-4 min-h-0">
        {messages.map(msg => (
          <div key={msg.id} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
            {msg.role === 'assistant' && (
              <div className="w-7 h-7 rounded-full bg-navy-800 flex items-center justify-center text-white text-xs shrink-0 mr-2 mt-1">✦</div>
            )}
            <div className={`max-w-[80%] rounded-2xl p-4 text-sm leading-relaxed ${
              msg.role === 'user'
                ? 'bg-navy-800 text-white rounded-tr-sm'
                : msg.error
                  ? 'bg-red-50 border border-red-200 text-red-800 rounded-tl-sm'
                  : 'bg-white border border-slate-200 text-slate-800 rounded-tl-sm'
            }`}>
              <div className="leading-relaxed">{renderContent(msg.content)}</div>

              {msg.executed && (
                <div className="mt-2 inline-flex items-center gap-1 text-xs font-semibold text-emerald-700 bg-emerald-50 border border-emerald-200 rounded-full px-2 mt-1">
                  ✓ Enregistrée
                  {msg.intent && <span className="font-normal text-emerald-600"> · {msg.intent}</span>}
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