/**
 * Contexto do usuário: idioma, moeda, fuso e país num lugar só.
 * Nenhuma tela assume pt-BR, BRL ou America/Sao_Paulo.
 */
import React, { createContext, useContext, useMemo, useState } from 'react';
import { NativeModules, Platform } from 'react-native';
import { resolveLocaleContext, type UserLocaleContext } from './money';
import { traduzir, type Idioma } from '../i18n';

interface Valor {
  locale: UserLocaleContext;
  definirLocale: (parcial: Partial<UserLocaleContext>) => void;
  t: (chave: string, params?: Record<string, string>) => string;
}

const Ctx = createContext<Valor | null>(null);

function localeDoAparelho(): string {
  try {
    if (Platform.OS === 'ios') {
      const s = NativeModules.SettingsManager?.settings;
      return (s?.AppleLocale ?? s?.AppleLanguages?.[0] ?? 'pt-BR').replace('_', '-');
    }
    return (NativeModules.I18nManager?.localeIdentifier ?? 'pt-BR').replace('_', '-');
  } catch {
    return 'pt-BR';
  }
}

export function UserProvider(
  { children, salvo }: { children: React.ReactNode; salvo?: Partial<UserLocaleContext> },
) {
  const [locale, setLocale] = useState<UserLocaleContext>(
    () => resolveLocaleContext(localeDoAparelho(), salvo),
  );

  const valor = useMemo<Valor>(() => ({
    locale,
    definirLocale: (parcial) => setLocale((a) => ({ ...a, ...parcial })),
    t: (chave, params) => traduzir(locale.language as Idioma, chave, params),
  }), [locale]);

  return <Ctx.Provider value={valor}>{children}</Ctx.Provider>;
}

export function useUser(): Valor {
  const v = useContext(Ctx);
  if (!v) throw new Error('useUser fora do UserProvider');
  return v;
}
