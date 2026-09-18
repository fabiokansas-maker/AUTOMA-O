/**
 * Denúncia de resposta de IA, dentro do app.
 * O Google Play exige que apps que geram conteúdo com IA ofereçam um caminho
 * no próprio app para sinalizar conteúdo ofensivo — e-mail externo não conta.
 */
import React from 'react';
import { Modal, Pressable, StyleSheet, Text, View } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { useUser } from '../lib/UserContext';

const CATEGORIAS = ['incorreto', 'ofensivo', 'perigoso', 'privacidade', 'outro'] as const;

interface Props {
  visivel: boolean;
  aoFechar: () => void;
  aoEnviar: (categoria: string) => void;
}

export function ReportSheet({ visivel, aoFechar, aoEnviar }: Props) {
  const insets = useSafeAreaInsets();
  const { t } = useUser();

  return (
    <Modal
      visible={visivel}
      transparent
      animationType="slide"
      onRequestClose={aoFechar}>
      <Pressable style={e.fundo} onPress={aoFechar} accessibilityLabel={t('common.cancel')} />
      {/* o inset também vale dentro do modal: em gestos a folha não pode
          terminar embaixo da barra */}
      <View style={[e.folha, { paddingBottom: insets.bottom + 16 }]}>
        <Text style={e.titulo}>{t('report.title')}</Text>
        <Text style={e.pergunta}>{t('report.question')}</Text>
        {CATEGORIAS.map((c) => (
          <Pressable
            key={c}
            style={e.opcao}
            onPress={() => aoEnviar(c)}
            accessibilityRole="button">
            <Text style={e.opcaoTexto}>{t(`report.${c}`)}</Text>
          </Pressable>
        ))}
        <Pressable style={e.cancelar} onPress={aoFechar} accessibilityRole="button">
          <Text style={e.cancelarTexto}>{t('common.cancel')}</Text>
        </Pressable>
      </View>
    </Modal>
  );
}

const e = StyleSheet.create({
  fundo: { flex: 1, backgroundColor: '#0006' },
  folha: { borderTopLeftRadius: 20, borderTopRightRadius: 20,
           paddingHorizontal: 20, paddingTop: 20, backgroundColor: '#fff' },
  titulo: { fontSize: 18, fontWeight: '700', marginBottom: 4 },
  pergunta: { fontSize: 14, opacity: 0.7, marginBottom: 16 },
  opcao: { minHeight: 48, justifyContent: 'center',
           borderBottomWidth: StyleSheet.hairlineWidth },
  opcaoTexto: { fontSize: 15 },
  cancelar: { minHeight: 48, justifyContent: 'center', marginTop: 8 },
  cancelarTexto: { fontSize: 15, opacity: 0.7 },
});
