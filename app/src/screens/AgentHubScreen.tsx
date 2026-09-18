/**
 * Home: central de especialistas. A pergunta que ela responde é
 * "com qual especialista eu falo?", não "qual número eu olho?".
 */
import React, { useMemo, useState } from 'react';
import {
  FlatList, Pressable, StyleSheet, Text, TextInput, View, useWindowDimensions,
} from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { AGENTES, type AgenteCard } from '../agents/catalog';
import { useUser } from '../lib/UserContext';

interface Props {
  userName: string;
  alertas: Array<{ id: string; texto: string; agentId: string }>;
  aoAbrirAgente: (agentId: string) => void;
  aoPerguntar: (pergunta: string) => void;
  aoAbrirAjustes: () => void;
}

export function AgentHubScreen(p: Props) {
  const insets = useSafeAreaInsets();
  const { width } = useWindowDimensions();
  const { t } = useUser();
  const [pergunta, setPergunta] = useState('');

  // Colunas pela LARGURA DA JANELA, não por "é tablet?": vale para dobrável,
  // multi-janela e paisagem sem código extra.
  const colunas = width >= 900 ? 3 : width >= 600 ? 2 : 1;
  const dados = useMemo<AgenteCard[]>(() => AGENTES, []);

  const enviar = () => {
    const v = pergunta.trim();
    if (!v) return;
    aoPerguntarSeguro(v);
    setPergunta('');
  };
  const aoPerguntarSeguro = (v: string) => p.aoPerguntar(v.slice(0, 2000));

  return (
    <View style={[e.raiz, { paddingTop: insets.top }]}>
      <FlatList
        key={`col-${colunas}`}
        data={dados}
        numColumns={colunas}
        keyExtractor={(a) => a.id}
        // insets.bottom no CONTEÚDO: o último card sobe acima da barra de
        // navegação em vez de ficar escondido atrás dela
        contentContainerStyle={{
          paddingHorizontal: 16,
          paddingBottom: insets.bottom + 24,
        }}
        ListHeaderComponent={
          <View>
            <View style={e.topo}>
              <Text style={e.marca}>{t('app.name')}</Text>
              <Pressable
                onPress={p.aoAbrirAjustes}
                hitSlop={12}
                accessibilityRole="button"
                accessibilityLabel={t('settings.title')}>
                <Text style={e.engrenagem}>⚙︎</Text>
              </Pressable>
            </View>
            <Text style={e.saudacao}>{t('home.greeting', { name: p.userName })}</Text>

            <Text style={e.pergunta}>{t('home.ask_title')}</Text>
            <TextInput
              style={e.campo}
              value={pergunta}
              onChangeText={setPergunta}
              placeholder={t('home.ask_placeholder')}
              returnKeyType="send"
              onSubmitEditing={enviar}
              accessibilityLabel={t('home.ask_a11y')}
            />
            <Text style={e.secao}>{t('home.specialists')}</Text>
          </View>
        }
        renderItem={({ item }) => (
          <Pressable
            style={({ pressed }) => [
              e.card,
              colunas > 1 ? { flex: 1 / colunas } : null,
              pressed ? e.pressionado : null,
            ]}
            onPress={() => p.aoAbrirAgente(item.id)}
            accessibilityRole="button"
            accessibilityLabel={`${t(item.nomeChave)}. ${t(item.descChave)}`}>
            <Text style={e.emoji}>{item.emoji}</Text>
            <Text style={e.cardTitulo}>{t(item.nomeChave)}</Text>
            {/* sem numberOfLines curto: idioma longo não pode cortar sentido */}
            <Text style={e.cardTexto}>{t(item.descChave)}</Text>
          </Pressable>
        )}
        ListFooterComponent={
          p.alertas.length === 0 ? null : (
            <View style={e.alertas}>
              <Text style={e.secao}>{t('home.alerts')}</Text>
              {p.alertas.map((a) => (
                <Pressable
                  key={a.id}
                  onPress={() => p.aoAbrirAgente(a.agentId)}
                  accessibilityRole="button">
                  <Text style={e.alerta}>{a.texto}</Text>
                </Pressable>
              ))}
            </View>
          )
        }
      />
    </View>
  );
}

const e = StyleSheet.create({
  raiz: { flex: 1 },
  topo: { flexDirection: 'row', justifyContent: 'space-between',
          alignItems: 'center', marginTop: 8 },
  marca: { fontSize: 14, opacity: 0.7 },
  engrenagem: { fontSize: 20, opacity: 0.7 },
  saudacao: { fontSize: 26, fontWeight: '700', marginBottom: 20 },
  pergunta: { fontSize: 15, marginBottom: 8 },
  // minHeight em vez de height: respeita font scale grande sem cortar
  campo: { borderWidth: 1, borderRadius: 12, paddingHorizontal: 14,
           minHeight: 48, fontSize: 16, marginBottom: 24 },
  secao: { fontSize: 13, textTransform: 'uppercase', opacity: 0.6, marginBottom: 10 },
  card: { borderWidth: 1, borderRadius: 16, padding: 16, margin: 6, minHeight: 112 },
  pressionado: { opacity: 0.7 },
  emoji: { fontSize: 22, marginBottom: 6 },
  cardTitulo: { fontSize: 16, fontWeight: '600', marginBottom: 4 },
  cardTexto: { fontSize: 13, opacity: 0.75 },
  alertas: { marginTop: 24 },
  alerta: { fontSize: 14, paddingVertical: 10 },
});
