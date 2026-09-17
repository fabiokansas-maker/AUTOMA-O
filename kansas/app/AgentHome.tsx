/**
 * Home agent-first: a pergunta deixa de ser "qual número eu olho?" e passa a
 * ser "com qual especialista eu falo?".
 *
 * Edge-to-edge correto: nada de padding mágico. As barras do sistema entram
 * via insets, que mudam entre gestos e 3 botões, notch e sem notch, retrato
 * e paisagem.
 */
import React, { useMemo } from "react";
import {
  FlatList, Pressable, StyleSheet, Text, TextInput, View, useWindowDimensions,
} from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";

export interface AgentCard {
  id: string;
  displayName: string;
  description: string;
  emoji: string;
}

export interface AgentAlert { id: string; text: string; agentId: string }

interface Props {
  userName: string;
  agents: AgentCard[];
  alerts: AgentAlert[];
  onOpenAgent: (agentId: string) => void;
  onAsk: (pergunta: string) => void;
  t: (chave: string, params?: Record<string, string>) => string;
}

export function AgentHome({ userName, agents, alerts, onOpenAgent, onAsk, t }: Props) {
  const insets = useSafeAreaInsets();
  const { width } = useWindowDimensions();
  const [pergunta, setPergunta] = React.useState("");

  // Layout adaptativo por LARGURA DE JANELA, não por "é tablet?".
  // Vale para dobrável, multi-janela e paisagem.
  const colunas = width >= 900 ? 3 : width >= 600 ? 2 : 1;

  const dados = useMemo(() => agents, [agents]);

  return (
    <View style={[estilos.raiz, { paddingTop: insets.top }]}>
      <FlatList
        key={`cols-${colunas}`}
        data={dados}
        numColumns={colunas}
        keyExtractor={(a) => a.id}
        // O inset de baixo entra no CONTEÚDO da lista: o último card sobe
        // acima da barra de navegação em vez de ficar escondido atrás dela.
        contentContainerStyle={{
          paddingHorizontal: 16,
          paddingBottom: insets.bottom + 24,
        }}
        ListHeaderComponent={
          <View>
            <Text style={estilos.marca}>{t("app.name")}</Text>
            <Text style={estilos.saudacao}>{t("home.greeting", { name: userName })}</Text>

            <Text style={estilos.pergunta}>{t("home.ask_title")}</Text>
            <TextInput
              style={estilos.campo}
              value={pergunta}
              onChangeText={setPergunta}
              placeholder={t("home.ask_placeholder")}
              returnKeyType="send"
              onSubmitEditing={() => {
                const p = pergunta.trim();
                if (p) { onAsk(p); setPergunta(""); }
              }}
              accessibilityLabel={t("home.ask_a11y")}
            />

            <Text style={estilos.secao}>{t("home.specialists")}</Text>
          </View>
        }
        renderItem={({ item }) => (
          <Pressable
            style={({ pressed }) => [
              estilos.card,
              colunas > 1 && { flex: 1 / colunas },
              pressed && estilos.cardPressionado,
            ]}
            onPress={() => onOpenAgent(item.id)}
            accessibilityRole="button"
            accessibilityLabel={`${item.displayName}. ${item.description}`}
          >
            <Text style={estilos.emoji}>{item.emoji}</Text>
            <Text style={estilos.cardTitulo} numberOfLines={2}>{item.displayName}</Text>
            {/* sem numberOfLines fixo curto: idioma longo não pode cortar sentido */}
            <Text style={estilos.cardTexto}>{item.description}</Text>
          </Pressable>
        )}
        ListFooterComponent={
          alerts.length === 0 ? null : (
            <View style={estilos.alertas}>
              <Text style={estilos.secao}>{t("home.alerts")}</Text>
              {alerts.map((a) => (
                <Pressable key={a.id} onPress={() => onOpenAgent(a.agentId)}>
                  <Text style={estilos.alerta}>{a.text}</Text>
                </Pressable>
              ))}
            </View>
          )
        }
      />
    </View>
  );
}

const estilos = StyleSheet.create({
  raiz: { flex: 1 },
  marca: { fontSize: 14, opacity: 0.7, marginTop: 8 },
  saudacao: { fontSize: 26, fontWeight: "700", marginBottom: 20 },
  pergunta: { fontSize: 15, marginBottom: 8 },
  campo: {
    borderWidth: 1, borderRadius: 12, paddingHorizontal: 14,
    // altura mínima em vez de altura fixa: respeita font scale grande
    minHeight: 48, fontSize: 16, marginBottom: 24,
  },
  secao: { fontSize: 13, textTransform: "uppercase", opacity: 0.6, marginBottom: 10 },
  card: { borderWidth: 1, borderRadius: 16, padding: 16, margin: 6, minHeight: 112 },
  cardPressionado: { opacity: 0.7 },
  emoji: { fontSize: 22, marginBottom: 6 },
  cardTitulo: { fontSize: 16, fontWeight: "600", marginBottom: 4 },
  cardTexto: { fontSize: 13, opacity: 0.75 },
  alertas: { marginTop: 24 },
  alerta: { fontSize: 14, paddingVertical: 10 },
});
