/**
 * Shell reutilizável de agente: conversa + componentes financeiros
 * estruturados + ações rápidas + feedback/denúncia da resposta.
 *
 * Os dois bugs que esta tela resolve de raiz:
 *  1) teclado cobrindo o input  -> inset do IME, não altura chutada;
 *  2) botão atrás da barra de navegação -> inset de baixo no conteúdo.
 */
import React, { useCallback, useRef } from "react";
import {
  ActivityIndicator, FlatList, KeyboardAvoidingView, Platform, Pressable,
  StyleSheet, Text, TextInput, View,
} from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { BlockRenderer, type Block } from "./blocks/BlockRenderer";
import type { UserLocaleContext } from "./money";

export interface AgentMessage {
  id: string;
  role: "user" | "agent";
  blocks: Block[];
  pending?: boolean;
}

interface Props {
  agentName: string;
  messages: AgentMessage[];
  quickActions: Array<{ id: string; label: string }>;
  loading: boolean;
  toolRunning?: string | null;
  erro?: string | null;
  locale: UserLocaleContext;
  onSend: (texto: string) => void;
  onQuickAction: (id: string) => void;
  onRetry: () => void;
  onFeedback: (messageId: string, verdict: "helpful" | "not_helpful" | "report") => void;
  t: (chave: string, params?: Record<string, string>) => string;
}

export function AgentScreen(p: Props) {
  const insets = useSafeAreaInsets();
  const [texto, setTexto] = React.useState("");
  const lista = useRef<FlatList<AgentMessage>>(null);

  const enviar = useCallback(() => {
    const v = texto.trim();
    if (!v) return;
    p.onSend(v);
    setTexto("");
  }, [texto, p]);

  return (
    <KeyboardAvoidingView
      style={estilos.raiz}
      behavior={Platform.OS === "ios" ? "padding" : undefined}
    >
      <View style={[estilos.header, { paddingTop: insets.top + 8 }]}>
        <Text style={estilos.titulo} numberOfLines={1}>{p.agentName}</Text>
      </View>

      <FlatList
        ref={lista}
        data={p.messages}
        keyExtractor={(m) => m.id}
        contentContainerStyle={{ paddingHorizontal: 16, paddingBottom: 12 }}
        onContentSizeChange={() => lista.current?.scrollToEnd({ animated: true })}
        renderItem={({ item }) => (
          <View style={[estilos.bolha, item.role === "user" ? estilos.doUsuario : estilos.doAgente]}>
            {item.blocks.map((b, i) => (
              <BlockRenderer key={i} block={b} locale={p.locale} t={p.t} />
            ))}
            {item.role === "agent" && !item.pending && (
              <View style={estilos.feedback}>
                <Pressable onPress={() => p.onFeedback(item.id, "helpful")}
                  accessibilityLabel={p.t("feedback.helpful")} hitSlop={8}>
                  <Text style={estilos.acaoFeedback}>👍</Text>
                </Pressable>
                <Pressable onPress={() => p.onFeedback(item.id, "not_helpful")}
                  accessibilityLabel={p.t("feedback.not_helpful")} hitSlop={8}>
                  <Text style={estilos.acaoFeedback}>👎</Text>
                </Pressable>
                {/* Exigência do Google Play: denunciar conteúdo de IA DENTRO do app */}
                <Pressable onPress={() => p.onFeedback(item.id, "report")}
                  accessibilityLabel={p.t("feedback.report")} hitSlop={8}>
                  <Text style={estilos.acaoFeedback}>⚑ {p.t("feedback.report_short")}</Text>
                </Pressable>
              </View>
            )}
          </View>
        )}
      />

      {p.toolRunning ? (
        <View style={estilos.status}>
          <ActivityIndicator />
          <Text style={estilos.statusTexto}>
            {p.t("agent.running_tool", { tool: p.toolRunning })}
          </Text>
        </View>
      ) : null}

      {p.erro ? (
        <Pressable style={estilos.erro} onPress={p.onRetry} accessibilityRole="button">
          <Text style={estilos.erroTexto}>{p.erro} · {p.t("common.retry")}</Text>
        </Pressable>
      ) : null}

      {p.quickActions.length > 0 && (
        <FlatList
          horizontal
          data={p.quickActions}
          keyExtractor={(q) => q.id}
          showsHorizontalScrollIndicator={false}
          contentContainerStyle={estilos.acoes}
          renderItem={({ item }) => (
            <Pressable style={estilos.chip} onPress={() => p.onQuickAction(item.id)}>
              <Text style={estilos.chipTexto}>{item.label}</Text>
            </Pressable>
          )}
        />
      )}

      {/* insets.bottom aqui = o composer nunca fica atrás da navigation bar,
          com gestos OU com 3 botões, sem número mágico */}
      <View style={[estilos.composer, { paddingBottom: insets.bottom + 8 }]}>
        <TextInput
          style={estilos.input}
          value={texto}
          onChangeText={setTexto}
          placeholder={p.t("agent.input_placeholder")}
          multiline
          onSubmitEditing={enviar}
          accessibilityLabel={p.t("agent.input_a11y")}
        />
        <Pressable
          onPress={enviar}
          disabled={p.loading || texto.trim().length === 0}
          style={[estilos.enviar, (p.loading || !texto.trim()) && estilos.enviarOff]}
          accessibilityRole="button"
          accessibilityLabel={p.t("agent.send")}
        >
          <Text style={estilos.enviarTexto}>{p.t("agent.send")}</Text>
        </Pressable>
      </View>
    </KeyboardAvoidingView>
  );
}

const estilos = StyleSheet.create({
  raiz: { flex: 1 },
  header: { paddingHorizontal: 16, paddingBottom: 12, borderBottomWidth: StyleSheet.hairlineWidth },
  titulo: { fontSize: 18, fontWeight: "700" },
  bolha: { borderRadius: 14, padding: 12, marginVertical: 6, maxWidth: "92%" },
  doUsuario: { alignSelf: "flex-end" },
  doAgente: { alignSelf: "flex-start" },
  feedback: { flexDirection: "row", gap: 16, marginTop: 10, alignItems: "center" },
  acaoFeedback: { fontSize: 13, opacity: 0.7 },
  status: { flexDirection: "row", alignItems: "center", gap: 8, paddingHorizontal: 16, paddingVertical: 6 },
  statusTexto: { fontSize: 13, opacity: 0.7 },
  erro: { paddingHorizontal: 16, paddingVertical: 10 },
  erroTexto: { fontSize: 13 },
  acoes: { paddingHorizontal: 16, gap: 8, paddingVertical: 8 },
  chip: { borderWidth: 1, borderRadius: 999, paddingHorizontal: 14, minHeight: 36, justifyContent: "center" },
  chipTexto: { fontSize: 13 },
  composer: {
    flexDirection: "row", alignItems: "flex-end", gap: 8,
    paddingHorizontal: 16, paddingTop: 8, borderTopWidth: StyleSheet.hairlineWidth,
  },
  input: { flex: 1, borderWidth: 1, borderRadius: 12, paddingHorizontal: 12, minHeight: 44, maxHeight: 120, fontSize: 16 },
  enviar: { borderRadius: 12, paddingHorizontal: 16, minHeight: 44, justifyContent: "center" },
  enviarOff: { opacity: 0.4 },
  enviarTexto: { fontSize: 15, fontWeight: "600" },
});
