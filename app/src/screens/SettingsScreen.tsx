/**
 * Ajustes: idioma, moeda e as TRÊS ações de dados separadas, cada uma com
 * efeito claro — exigência de privacidade do Play e da spec do produto.
 *   limpar conversa  ≠  limpar memória do agente  ≠  excluir conta
 */
import React, { useState } from 'react';
import {
  Alert, Pressable, ScrollView, StyleSheet, Text, View,
} from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { useUser } from '../lib/UserContext';
import { idiomasDisponiveis } from '../i18n';

interface Props {
  agentIdAtual?: string;
  aoLimparConversa: () => Promise<void>;
  aoLimparMemoria: () => Promise<void>;
  aoExcluirConta: () => Promise<void>;
  aoAbrirPrivacidade: () => void;
}

const MOEDAS = ['BRL', 'USD', 'EUR', 'GBP', 'MXN', 'JPY'];

export function SettingsScreen(p: Props) {
  const insets = useSafeAreaInsets();
  const { t, locale, definirLocale } = useUser();
  const [ocupado, setOcupado] = useState<string | null>(null);

  const confirmar = (chaveTitulo: string, aviso: string, acao: () => Promise<void>) => {
    Alert.alert(t(chaveTitulo), aviso, [
      { text: t('common.cancel'), style: 'cancel' },
      {
        text: t('common.confirm'),
        style: 'destructive',
        onPress: async () => {
          setOcupado(chaveTitulo);
          try { await acao(); } finally { setOcupado(null); }
        },
      },
    ]);
  };

  return (
    <ScrollView
      style={e.raiz}
      contentContainerStyle={{
        paddingTop: insets.top + 16,
        paddingBottom: insets.bottom + 32,
        paddingHorizontal: 16,
      }}>
      <Text style={e.titulo}>{t('settings.title')}</Text>

      <Text style={e.secao}>{t('settings.language')}</Text>
      <View style={e.linhaChips}>
        {idiomasDisponiveis().map((i) => (
          <Pressable
            key={i}
            style={[e.chip, locale.language === i ? e.chipAtivo : null]}
            onPress={() => definirLocale({ language: i, locale: `${i}-${locale.country}` })}
            accessibilityRole="button"
            accessibilityState={{ selected: locale.language === i }}>
            <Text style={e.chipTexto}>{i.toUpperCase()}</Text>
          </Pressable>
        ))}
      </View>

      <Text style={e.secao}>{t('settings.currency')}</Text>
      <View style={e.linhaChips}>
        {MOEDAS.map((m) => (
          <Pressable
            key={m}
            style={[e.chip, locale.currency === m ? e.chipAtivo : null]}
            onPress={() => definirLocale({ currency: m })}
            accessibilityRole="button"
            accessibilityState={{ selected: locale.currency === m }}>
            <Text style={e.chipTexto}>{m}</Text>
          </Pressable>
        ))}
      </View>

      <Text style={e.secao}>{t('settings.privacy')}</Text>

      <Pressable style={e.item} onPress={p.aoAbrirPrivacidade} accessibilityRole="link">
        <Text style={e.itemTexto}>{t('settings.privacy')}</Text>
      </Pressable>

      <Pressable
        style={e.item}
        disabled={ocupado !== null}
        onPress={() => confirmar('settings.clear_thread', '', p.aoLimparConversa)}
        accessibilityRole="button">
        <Text style={e.itemTexto}>{t('settings.clear_thread')}</Text>
      </Pressable>

      <Pressable
        style={e.item}
        disabled={ocupado !== null || !p.agentIdAtual}
        onPress={() => confirmar('settings.clear_memory', '', p.aoLimparMemoria)}
        accessibilityRole="button">
        <Text style={e.itemTexto}>{t('settings.clear_memory')}</Text>
      </Pressable>

      <Pressable
        style={e.item}
        disabled={ocupado !== null}
        onPress={() => confirmar(
          'settings.delete_account', t('settings.delete_warning'), p.aoExcluirConta,
        )}
        accessibilityRole="button">
        <Text style={[e.itemTexto, e.destrutivo]}>{t('settings.delete_account')}</Text>
      </Pressable>
      <Text style={e.aviso}>{t('settings.delete_warning')}</Text>
    </ScrollView>
  );
}

const e = StyleSheet.create({
  raiz: { flex: 1 },
  titulo: { fontSize: 26, fontWeight: '700', marginBottom: 20 },
  secao: { fontSize: 13, textTransform: 'uppercase', opacity: 0.6,
           marginTop: 24, marginBottom: 10 },
  linhaChips: { flexDirection: 'row', flexWrap: 'wrap', gap: 8 },
  chip: { borderWidth: 1, borderRadius: 999, paddingHorizontal: 14,
          minHeight: 40, justifyContent: 'center' },
  chipAtivo: { borderWidth: 2 },
  chipTexto: { fontSize: 14 },
  item: { minHeight: 52, justifyContent: 'center',
          borderBottomWidth: StyleSheet.hairlineWidth },
  itemTexto: { fontSize: 15 },
  destrutivo: { color: '#b3261e', fontWeight: '600' },
  aviso: { fontSize: 12, opacity: 0.7, marginTop: 12 },
});
