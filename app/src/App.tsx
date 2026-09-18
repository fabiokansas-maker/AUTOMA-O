/**
 * Raiz do app. Navegação mínima: hub de agentes -> agente -> ajustes.
 *
 * SafeAreaProvider no topo é o que faz os insets existirem em todas as telas;
 * sem ele, o edge-to-edge do Android 15+ engole menu e botão.
 */
import React, { useCallback, useState } from 'react';
import { StatusBar, useColorScheme } from 'react-native';
import { SafeAreaProvider } from 'react-native-safe-area-context';
import { UserProvider, useUser } from './lib/UserContext';
import { AgentHubScreen } from './screens/AgentHubScreen';
import { AgentScreen, type Mensagem } from './screens/AgentScreen';
import { SettingsScreen } from './screens/SettingsScreen';
import { api, ApiError, type Sessao } from './lib/api';
import { routeBySignals } from './lib/router';

type Tela =
  | { nome: 'hub' }
  | { nome: 'agente'; agentId: string }
  | { nome: 'ajustes' };

const BASE_URL = 'https://kansas.functions.supabase.co';

function Raiz({ sessao, userName }: { sessao: Sessao; userName: string }) {
  const esquema = useColorScheme();
  const { t } = useUser();
  const [tela, setTela] = useState<Tela>({ nome: 'hub' });
  const [mensagens, setMensagens] = useState<Record<string, Mensagem[]>>({});
  const [threads, setThreads] = useState<Record<string, string>>({});
  const [carregando, setCarregando] = useState(false);
  const [toolEmCurso, setTool] = useState<string | null>(null);
  const [erro, setErro] = useState<string | null>(null);
  const [ultimaPergunta, setUltima] = useState<{ agentId: string; texto: string } | null>(null);

  const perguntar = useCallback(async (agentId: string, texto: string) => {
    setErro(null);
    setCarregando(true);
    setUltima({ agentId, texto });
    const idLocal = `local-${Date.now()}`;
    setMensagens((m) => ({
      ...m,
      [agentId]: [...(m[agentId] ?? []),
                  { id: idLocal, autor: 'user', blocos: [{ type: 'text', text: texto }] }],
    }));
    try {
      const r = await api.perguntar(sessao, {
        agentId, message: texto, threadId: threads[agentId],
      });
      setThreads((x) => ({ ...x, [agentId]: r.threadId }));
      setMensagens((m) => ({
        ...m,
        [agentId]: [...(m[agentId] ?? []),
                    { id: r.messageId, autor: 'agent', blocos: r.blocks }],
      }));
      const pendente = r.tools.find((x) => !x.ok);
      setTool(pendente ? pendente.name : null);
    } catch (ex) {
      setErro(ex instanceof ApiError ? ex.message : 'erro_servidor');
    } finally {
      setCarregando(false);
      setTool(null);
    }
  }, [sessao, threads]);

  const abrirPorPergunta = useCallback((pergunta: string) => {
    // o roteador escolhe QUEM responde; ele não ganha acesso a dado nenhum
    const decisao = routeBySignals(pergunta);
    const agentId = decisao?.primaryAgent ?? 'planning';
    setTela({ nome: 'agente', agentId });
    void perguntar(agentId, pergunta);
  }, [perguntar]);

  if (tela.nome === 'ajustes') {
    return (
      <SettingsScreen
        agentIdAtual={undefined}
        aoAbrirPrivacidade={() => { /* abre a política publicada */ }}
        aoLimparConversa={async () => {
          await api.apagar(sessao, { scope: 'threads' });
          setMensagens({});
          setThreads({});
          setTela({ nome: 'hub' });
        }}
        aoLimparMemoria={async () => { await api.apagar(sessao, { scope: 'memories' }); }}
        aoExcluirConta={async () => {
          await api.apagar(sessao, { scope: 'all' });
          setMensagens({});
          setThreads({});
          setTela({ nome: 'hub' });
        }}
      />
    );
  }

  if (tela.nome === 'agente') {
    const agentId = tela.agentId;
    return (
      <AgentScreen
        agentId={agentId}
        mensagens={mensagens[agentId] ?? []}
        carregando={carregando}
        toolEmCurso={toolEmCurso}
        erro={erro}
        aoEnviar={(texto) => void perguntar(agentId, texto)}
        aoTentarDeNovo={() => {
          if (ultimaPergunta) void perguntar(ultimaPergunta.agentId, ultimaPergunta.texto);
        }}
        aoAvaliar={(messageId, veredito, categoria) => {
          void api.feedback(sessao, { messageId, verdict: veredito, category: categoria })
            .catch(() => { /* feedback não pode derrubar a tela do usuário */ });
        }}
      />
    );
  }

  return (
    <>
      <StatusBar barStyle={esquema === 'dark' ? 'light-content' : 'dark-content'}
                 backgroundColor="transparent" translucent />
      <AgentHubScreen
        userName={userName}
        alertas={[]}
        aoAbrirAgente={(agentId) => setTela({ nome: 'agente', agentId })}
        aoPerguntar={abrirPorPergunta}
        aoAbrirAjustes={() => setTela({ nome: 'ajustes' })}
      />
    </>
  );
}

export default function App() {
  // a sessão real vem do login; aqui só o formato do que a raiz espera
  const sessao: Sessao = { accessToken: '', baseUrl: BASE_URL };
  return (
    <SafeAreaProvider>
      <UserProvider>
        <Raiz sessao={sessao} userName="" />
      </UserProvider>
    </SafeAreaProvider>
  );
}
