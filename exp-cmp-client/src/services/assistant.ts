// ─────────────────────────────────────────────────────────────
// Service Assistant — interpréteur IA hybride (intents + chat)
// ─────────────────────────────────────────────────────────────

import { api } from '../lib/api';
import type { AssistantReply, IntentMeta } from '../types/api';

export async function fetchAssistantIntents(): Promise<IntentMeta[]> {
  const data = await api.get<IntentMeta[]>('/assistant/intents');
  return data ?? [];
}

export interface AssistantChatPayload {
  message: string;
  session_id?: string | null;
}

export async function sendAssistantChat(payload: AssistantChatPayload): Promise<AssistantReply> {
  return api.post<AssistantReply>('/assistantv2/chat', payload);
}