/**
 * Renderizador de blocos TIPADOS. O modelo manda dados; quem decide pixel
 * é este arquivo. Bloco desconhecido nunca quebra a tela.
 */
import React from "react";
import { StyleSheet, Text, View } from "react-native";
import { formatDate, formatMoney, type Money, type UserLocaleContext } from "../lib/money";

export type Block =
  | { type: "text"; text: string }
  | { type: "money_summary"; label: string; amount: Money; hint?: string }
  | { type: "invoice_summary"; cardLabel: string; cardLast4: string; total: Money; closingDate: string; dueDate: string }
  | { type: "transaction_list"; items: Array<{ id: string; label: string; amount: Money; date: string }> }
  | { type: "goal_progress"; label: string; target: Money; saved: Money; progressPct: number }
  | { type: "budget_status"; items: Array<{ category: string; limit: Money; spent: Money; pace: string }> }
  | { type: "alert"; severity: "info" | "warning"; text: string }
  | { type: "confirmation"; question: string; confirmLabel: string }
  | { type: "chart"; series: Array<{ label: string; value: number }>; unit?: string };

interface Props {
  block: Block;
  locale: UserLocaleContext;
  t: (chave: string, params?: Record<string, string>) => string;
}

export function BlockRenderer({ block, locale, t }: Props) {
  switch (block.type) {
    case "text":
      return <Text style={e.texto}>{block.text}</Text>;

    case "money_summary":
      return (
        <View style={e.bloco}>
          <Text style={e.rotulo}>{block.label}</Text>
          <Text style={e.valorGrande}>{formatMoney(block.amount, locale)}</Text>
          {block.hint ? <Text style={e.dica}>{block.hint}</Text> : null}
        </View>
      );

    case "invoice_summary":
      return (
        <View style={e.bloco}>
          {/* nunca o número completo do cartão — nem na tela, nem em log */}
          <Text style={e.rotulo}>{block.cardLabel} ····{block.cardLast4}</Text>
          <Text style={e.valorGrande}>{formatMoney(block.total, locale)}</Text>
          <Text style={e.dica}>
            {t("invoice.closes_on", { date: formatDate(block.closingDate, locale) })} ·{" "}
            {t("invoice.due_on", { date: formatDate(block.dueDate, locale) })}
          </Text>
        </View>
      );

    case "transaction_list":
      return (
        <View style={e.bloco}>
          {block.items.slice(0, 20).map((i) => (
            <View key={i.id} style={e.linha}>
              <Text style={e.linhaTexto} numberOfLines={1}>{i.label}</Text>
              <Text style={e.linhaValor}>{formatMoney(i.amount, locale)}</Text>
            </View>
          ))}
        </View>
      );

    case "goal_progress":
      return (
        <View style={e.bloco}>
          <Text style={e.rotulo}>{block.label}</Text>
          <Text style={e.valorGrande}>
            {formatMoney(block.saved, locale)} / {formatMoney(block.target, locale)}
          </Text>
          <View style={e.barra}>
            <View style={[e.barraCheia, { width: `${Math.min(100, Math.max(0, block.progressPct))}%` }]} />
          </View>
        </View>
      );

    case "budget_status":
      return (
        <View style={e.bloco}>
          {block.items.map((i) => (
            <View key={i.category} style={e.linha}>
              <Text style={e.linhaTexto} numberOfLines={1}>{i.category}</Text>
              <Text style={e.linhaValor}>
                {formatMoney(i.spent, locale)} / {formatMoney(i.limit, locale)}
              </Text>
            </View>
          ))}
        </View>
      );

    case "alert":
      return <Text style={[e.texto, e.alerta]}>{block.text}</Text>;

    case "confirmation":
      return <Text style={e.texto}>{block.question}</Text>;

    case "chart":
      return (
        <View style={e.bloco}>
          {block.series.slice(0, 12).map((s) => (
            <View key={s.label} style={e.linha}>
              <Text style={e.linhaTexto} numberOfLines={1}>{s.label}</Text>
              <Text style={e.linhaValor}>
                {new Intl.NumberFormat(locale.locale).format(s.value)}{block.unit ?? ""}
              </Text>
            </View>
          ))}
        </View>
      );

    default:
      return null;
  }
}

const e = StyleSheet.create({
  texto: { fontSize: 15, lineHeight: 22 },
  alerta: { fontWeight: "600" },
  bloco: { marginTop: 10, borderRadius: 12, padding: 12, borderWidth: StyleSheet.hairlineWidth },
  rotulo: { fontSize: 12, opacity: 0.7, marginBottom: 2 },
  valorGrande: { fontSize: 22, fontWeight: "700" },
  dica: { fontSize: 12, opacity: 0.7, marginTop: 4 },
  linha: { flexDirection: "row", justifyContent: "space-between", gap: 12, paddingVertical: 6 },
  linhaTexto: { flex: 1, fontSize: 14 },
  linhaValor: { fontSize: 14, fontWeight: "600" },
  barra: { height: 6, borderRadius: 3, marginTop: 8, overflow: "hidden", backgroundColor: "#0002" },
  barraCheia: { height: 6, borderRadius: 3, backgroundColor: "#2e7d32" },
});
