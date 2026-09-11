// ─────────────────────────────────────────────────────────────
// Service Assistant v2 — moteur d'orchestration multi-tool-call
// (endpoints /assistantv2/* : liste des outils + chat)
// ─────────────────────────────────────────────────────────────

import { api } from '../lib/api';
import type { AssistantReply, ToolMeta } from '../types/api';

export async function fetchAssistantTools(): Promise<ToolMeta[]> {
  const data = await api.get<ToolMeta[]>('/assistantv2/tools');
  return data ?? [];
}

export interface AssistantChatPayload {
  message: string;
  session_id?: string | null;
}

export async function sendAssistantChat(payload: AssistantChatPayload): Promise<AssistantReply> {
  return api.post<AssistantReply>('/assistantv2/chat', payload);
}