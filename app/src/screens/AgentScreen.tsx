/**
 * Tela do agente: conversa + blocos financeiros estruturados + ações rápidas
 * + feedback e denúncia da resposta (exigência do Play para conteúdo de IA).
 *
 * Os dois bugs de layout que ela resolve na raiz:
 *   teclado cobrindo o campo   -> KeyboardAvoidingView + adjustResize
 *   botão atrás da barra       -> insets.bottom no composer
 */
import React, { useCallback, useRef, useState } from 'react';
import {
  ActivityIndicator, FlatList, KeyboardAvoidingView, Platform, Pressable,
  StyleSheet, Text, TextInput, View,
} from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { BlockRenderer, type Block } from '../components/blocks';
import { ReportSheet } from '../components/ReportSheet';
import { acharAgente } from '../agents/catalog';
import { useUser } from '../lib/UserContext';

export interface Mensagem {
  id: string;
  autor: 'user' | 'agent';
  blocos: Block[];
}

interface Props {
  agentId: string;
  mensagens: Mensagem[];
  carregando: boolean;
  toolEmCurso: string | null;
  erro: string | null;
  aoEnviar: (texto: string) => void;
  aoTentarDeNovo: () => void;
  aoAvaliar: (
    messageId: string,
    veredito: 'helpful' | 'not_helpful' | 'report',
    categoria?: string,
  ) => void;
}

export function AgentScreen(p: Props) {
  const insets = useSafeAreaInsets();
  const { t, locale } = useUser();
  const [texto, setTexto] = useState('');
  const [denunciando, setDenunciando] = useState<string | null>(null);
  const lista = useRef<FlatList<Mensagem>>(null);
  const agente = acharAgente(p.agentId);

  const enviar = useCallback(() => {
    const v = texto.trim();
    if (!v || p.carregando) return;
    p.aoEnviar(v);
    setTexto('');
  }, [texto, p]);

  return (
    <KeyboardAvoidingView
      style={e.raiz}
      behavior={Platform.OS === 'ios' ? 'padding' : undefined}>
      <View style={[e.header, { paddingTop: insets.top + 8 }]}>
        <Text style={e.titulo} numberOfLines={1}>
          {agente ? t(agente.nomeChave) : p.agentId}
        </Text>
      </View>

      <FlatList
        ref={lista}
        data={p.mensagens}
        keyExtractor={(m) => m.id}
        contentContainerStyle={e.conteudo}
        onContentSizeChange={() => lista.current?.scrollToEnd({ animated: true })}
        ListEmptyComponent={<Text style={e.vazio}>{t('agent.empty')}</Text>}
        renderItem={({ item }) => (
          <View style={[e.bolha, item.autor === 'user' ? e.doUsuario : e.doAgente]}>
            {item.blocos.map((b, i) => (
              <BlockRenderer key={i} block={b} locale={locale} t={t} />
            ))}
            {item.autor === 'agent' ? (
              <View style={e.feedback}>
                <Pressable
                  onPress={() => p.aoAvaliar(item.id, 'helpful')}
                  hitSlop={10} accessibilityRole="button"
                  accessibilityLabel={t('feedback.helpful')}>
                  <Text style={e.acao}>👍</Text>
                </Pressable>
                <Pressable
                  onPress={() => p.aoAvaliar(item.id, 'not_helpful')}
                  hitSlop={10} accessibilityRole="button"
                  accessibilityLabel={t('feedback.not_helpful')}>
                  <Text style={e.acao}>👎</Text>
                </Pressable>
                {/* denúncia DENTRO do app: política do Google Play para
                    apps que geram conteúdo com IA */}
                <Pressable
                  onPress={() => setDenunciando(item.id)}
                  hitSlop={10} accessibilityRole="button"
                  accessibilityLabel={t('feedback.report')}>
                  <Text style={e.acao}>⚑ {t('feedback.report_short')}</Text>
                </Pressable>
              </View>
            ) : null}
          </View>
        )}
      />

      {p.toolEmCurso ? (
        <View style={e.status}>
          <ActivityIndicator />
          <Text style={e.statusTexto}>
            {t('agent.running_tool', { tool: p.toolEmCurso })}
          </Text>
        </View>
      ) : null}

      {p.erro ? (
        <Pressable style={e.erro} onPress={p.aoTentarDeNovo} accessibilityRole="button">
          <Text style={e.erroTexto}>
            {t(`error.${p.erro}`)} · {t('common.retry')}
          </Text>
        </Pressable>
      ) : null}

      {agente ? (
        <FlatList
          horizontal
          data={agente.acoesRapidas}
          keyExtractor={(q) => q.id}
          showsHorizontalScrollIndicator={false}
          contentContainerStyle={e.acoes}
          renderItem={({ item }) => (
            <Pressable
              style={e.chip}
              onPress={() => p.aoEnviar(t(item.chave))}
              accessibilityRole="button">
              <Text style={e.chipTexto}>{t(item.chave)}</Text>
            </Pressable>
          )}
        />
      ) : null}

      {/* insets.bottom aqui = o campo nunca fica atrás da barra de navegação,
          com gestos OU com 3 botões, sem número mágico */}
      <View style={[e.composer, { paddingBottom: insets.bottom + 8 }]}>
        <TextInput
          style={e.input}
          value={texto}
          onChangeText={setTexto}
          placeholder={t('agent.input_placeholder')}
          multiline
          accessibilityLabel={t('agent.input_a11y')}
        />
        <Pressable
          onPress={enviar}
          disabled={p.carregando || texto.trim().length === 0}
          style={[e.enviar, (p.carregando || !texto.trim()) ? e.enviarOff : null]}
          accessibilityRole="button"
          accessibilityState={{ disabled: p.carregando || !texto.trim() }}
          accessibilityLabel={t('agent.send')}>
          <Text style={e.enviarTexto}>{t('agent.send')}</Text>
        </Pressable>
      </View>

      <ReportSheet
        visivel={denunciando !== null}
        aoFechar={() => setDenunciando(null)}
        aoEnviar={(categoria) => {
          if (denunciando) p.aoAvaliar(denunciando, 'report', categoria);
          setDenunciando(null);
        }}
      />
    </KeyboardAvoidingView>
  );
}

const e = StyleSheet.create({
  raiz: { flex: 1 },
  header: { paddingHorizontal: 16, paddingBottom: 12,
            borderBottomWidth: StyleSheet.hairlineWidth },
  titulo: { fontSize: 18, fontWeight: '700' },
  conteudo: { paddingHorizontal: 16, paddingBottom: 12 },
  vazio: { fontSize: 14, opacity: 0.6, textAlign: 'center', marginTop: 32 },
  bolha: { borderRadius: 14, padding: 12, marginVertical: 6, maxWidth: '92%' },
  doUsuario: { alignSelf: 'flex-end' },
  doAgente: { alignSelf: 'flex-start' },
  feedback: { flexDirection: 'row', gap: 16, marginTop: 10, alignItems: 'center' },
  acao: { fontSize: 13, opacity: 0.7 },
  status: { flexDirection: 'row', alignItems: 'center', gap: 8,
            paddingHorizontal: 16, paddingVertical: 6 },
  statusTexto: { fontSize: 13, opacity: 0.7 },
  erro: { paddingHorizontal: 16, paddingVertical: 10 },
  erroTexto: { fontSize: 13 },
  acoes: { paddingHorizontal: 16, gap: 8, paddingVertical: 8 },
  chip: { borderWidth: 1, borderRadius: 999, paddingHorizontal: 14,
          minHeight: 36, justifyContent: 'center' },
  chipTexto: { fontSize: 13 },
  composer: { flexDirection: 'row', alignItems: 'flex-end', gap: 8,
              paddingHorizontal: 16, paddingTop: 8,
              borderTopWidth: StyleSheet.hairlineWidth },
  input: { flex: 1, borderWidth: 1, borderRadius: 12, paddingHorizontal: 12,
           minHeight: 44, maxHeight: 120, fontSize: 16 },
  enviar: { borderRadius: 12, paddingHorizontal: 16, minHeight: 44,
            justifyContent: 'center' },
  enviarOff: { opacity: 0.4 },
  enviarTexto: { fontSize: 15, fontWeight: '600' },
});
