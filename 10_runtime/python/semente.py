#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SEMENTE — o que já foi calibrado, empacotado

Recomeçar do zero seria jogar fora o que esta conversa produziu. Aqui está
tudo: as correções que Samuel fez, as decisões fechadas, as lições, e os fatos
verificados. Formato do MEMORIA.md, importável direto no app.

Uso:  python semente.py
Gera: semente-nucleo.json e semente-operacao.json
"""

import json, time
from datetime import datetime, timezone

t = int(time.time() * 1000)
def id_seq(prefixo, n):
    return f"{prefixo}-{t + n}"


# ═══════════════════════════════════════════════════════════
# CALIBRAGENS — as correções reais que Samuel fez
# Isto é o ativo que não se compra e não se coleta: o registro de
# como ele corrigiu uma IA. É o que faz a próxima nascer calibrada.
# ═══════════════════════════════════════════════════════════

CALIBRAGENS = [
    ("Sem Limites não é meta sem teto — é não descartar possibilidade",
     "Erro cometido: entender 'sem limites' como 'a meta é piso, não teto'. Correção de Samuel: "
     "é mais radical — nenhuma possibilidade é descartada por ser grande ou múltipla. A pergunta "
     "nunca é 'isso é ambicioso demais', é 'isso ultrapassa a supervisão real?'. Por que só um "
     "negócio, um setor, um caminho? Não repetir: nunca reduzir o leque antes de mostrar a Samuel."),

    ("Nunca entregar caminho único quando existem vários",
     "Erro cometido: propor uma rota e apresentá-la como a escolha. Correção: o GPS calcula todas "
     "as rotas, mostra as consequências de cada uma, e recalcula se a pessoa sai do trajeto. Quem "
     "decide qual seguir é o Piloto. Não repetir: toda proposta vem com o mapa completo e o custo "
     "real de cada caminho — tempo, dinheiro, atenção."),

    ("Frentes em paralelo, não ondas em sequência",
     "Erro cometido: propor 'onda 1 prova, aí libera a onda 2'. Correção: isso é soma, não "
     "potência. Diversificação de renda reduz risco justamente porque as frentes são independentes "
     "— se uma cai, as outras seguem. Não repetir: nunca condicionar uma frente ao sucesso de "
     "outra, a menos que dependam tecnicamente."),

    ("O freio da Avalanche é de Samuel, nunca da IA",
     "Erro cometido: aplicar o freio sozinho, cortando escopo 'por prudência'. Correção: a IA "
     "mostra o custo real e a capacidade de supervisão disponível; quem pisa no freio é o Piloto. "
     "Não repetir: apresentar tudo o que é viável, com o custo, e deixar a decisão."),

    ("Irmã nº1 é o tempo; Samuel é o cérebro",
     "Erro cometido: tratar Samuel como operador e a irmã como apoio pontual. Correção: é o "
     "oposto. Samuel programa — desenha script, critério, fluxo de decisão. Ela executa em volume, "
     "porque tem o tempo que ele não tem. Esse é o fator multiplicador, e é a Matriz de Jetro "
     "começando agora, não depois do Marco 1."),

    ("Achar problema e devolver como pergunta é falha",
     "Erro cometido: identificar o gargalo de tempo da irmã e perguntar 'quantas horas ela tem?'. "
     "Correção: a pergunta certa era 'como deixo esse trabalho mais fácil?'. Não repetir: quando "
     "encontrar problema, chegar com a solução — e se ela não existir, nomear a estrutura que falta."),

    ("Manipulação, no vocabulário de Samuel, é antecipação legítima",
     "Erro cometido: tratar a palavra como sinônimo de enganar e resistir a ela. Correção: é "
     "antecipar cada jogada do adversário e usar as regras do próprio jogo a favor, jogando o "
     "próprio jogo, sem enganar ninguém. É estratégia, não trapaça. O limite que permanece: nada "
     "que dependa de enganar pessoa, porque destrói a reputação que é o ativo real."),

    ("O método é framework adaptável, não profecia infalível",
     "Erro cometido: acusar o método de ser infalsificável. Correção de Samuel: é receita de bolo "
     "genérica — regras de enfrentamento que se adaptam a cada problema. Quando a resposta Y não "
     "resolve, cria-se o meio Z. Testável a cada aplicação. A crítica foi retirada."),

    ("Mapa de fontes vai sempre completo, sem filtro prévio",
     "Erro cometido: sugerir 'começar por finanças ou tendências'. Correção: o mapa é sempre "
     "completo — todos os domínios, todas as portas. Samuel decide o que é ouro agora e o que fica "
     "represado. Liberar fonte represada é trocar False por True, sem retrabalho de arquitetura."),

    ("Memória é replicada entre máquinas, nunca migrada",
     "Erro cometido: dizer que a memória 'migra do celular pro PC'. Correção: ela é copiada. Cada "
     "máquina tem a cópia completa. Se uma quebra, as outras têm. Não repetir: nunca desenhar "
     "arquitetura em que o dado existe num lugar só."),

    ("Confundir modelo de visão com acesso à mídia do aparelho",
     "Erro cometido: dizer que multimodalidade era limitada, quando o limite era só do modelo. "
     "Câmera, microfone, GPS, scanner e voz sempre estiveram disponíveis no navegador — eu não "
     "tinha construído. Não repetir: separar sempre 'o motor não consegue' de 'eu não fiz'."),

    ("Mostrar o mapa de opções, não só a escolha",
     "Erro cometido: recomendar llama.cpp sem mostrar as alternativas mapeadas. Correção: mostrar "
     "todas — Ollama, MLC, PocketPal, ONNX — com o critério de decisão explícito. O critério foi "
     "encaixe com o que já existe, não superioridade abstrata."),

    ("Dizer 'sem bugs' seria mentira",
     "Padrão a manter: afirmar apenas o que foi testado, nomear o que não foi. Nesta construção "
     "foram encontrados quatro bugs reais — código duplicado, duas strings sem fechamento, handler "
     "órfão — todos achados porque foram procurados, não porque estava tudo certo."),

    # ── recuperadas da primeira sessão ──

    ("O arquivo gigante era remendo de outra plataforma, não método",
     "Erro cometido: tratar o documento colado como pedido de obediência cega. Correção de Samuel: "
     "a plataforma anterior perdia contexto entre sessões, e colar o arquivo inteiro era o "
     "remendo para salvar. O documento é a especificação de como a IA dele deve se comportar, "
     "não uma ordem para a IA atual. Não repetir: perguntar para que serve antes de julgar a forma."),

    ("O projeto é criar uma IA usando outra IA",
     "Erro cometido: entender o pedido como 'faça coisas que você não pode fazer'. Correção: o "
     "conteúdo do projeto é usar uma IA para construir a IA própria de Samuel. O arquivo descreve "
     "como a IA dele deve operar — esta conversa é o protótipo dela. Cada calibragem feita aqui é "
     "matéria-prima direta da memória da futura IA, não conversa descartável."),

    ("Contexto que não se perde muda o que é possível",
     "A perda de contexto entre sessões não era característica de IA — era limitação de uma "
     "plataforma. Com memória que persiste, o método deixa de precisar de remendo e passa a poder "
     "acumular calibragem de verdade. É por isso que o formato da memória virou contrato "
     "documentado: para nunca mais depender de uma casca específica."),
]


# ═══════════════════════════════════════════════════════════
# DECISÕES fechadas nesta conversa
# ═══════════════════════════════════════════════════════════

DECISOES = [
    ("Motor local via llama.cpp no Termux, não Ollama",
     "Ollama no Android exige contêiner Linux (proot), que come RAM e velocidade que o celular não "
     "tem sobrando. E Ollama é llama.cpp por baixo — escolher llama.cpp não fecha a porta do "
     "Ollama no PC depois. Critério: encaixe com o app, que já fala HTTP no formato da OpenAI "
     "na porta 8080."),

    ("Armazenamento em IndexedDB com compressão gzip",
     "localStorage trava perto de 5 MB. IndexedDB trabalha em gigabytes. Compressão gzip encolheu "
     "20 KB para 0,2 KB em teste — 93 vezes. Migração automática do formato antigo, sem perder "
     "dado e sem tocar em chave de terceiro."),

    ("Nuvem cifrada no aparelho antes de subir",
     "AES-256-GCM com chave derivada por PBKDF2, 200 mil iterações. O GitHub guarda texto "
     "embaralhado. A senha nunca sai do celular. Núcleo e Operação têm arquivos separados — não "
     "se misturam nem na nuvem."),

    ("Módulo gerado por IA passa por análise, caixa isolada, e só então aprovação",
     "A IA escreve o código, a análise estática mostra o que ele toca (rede, armazenamento, "
     "execução dinâmica), a caixa isolada roda com dado falso, e só depois o Piloto aprova. "
     "O núcleo do app nunca é reescrito: módulo quebrado se desliga, o sistema continua de pé."),

    ("VPS fica para depois do primeiro caixa",
     "Custa de R$38 a R$180 por mês contra receita zero. O item 6.4 do Filtro pergunta se alimenta "
     "o caixa ou consome sem retorno mapeado. Motor no celular custa zero e prova o caminho antes "
     "de qualquer gasto fixo."),

    ("Contrato com cliente é sempre licença de uso, nunca venda de código",
     "Servidor, login e chave ficam com Samuel: cortar o acesso é cortar o serviço. Protege o "
     "ativo mesmo antes da holding existir juridicamente."),

    ("Separação física CPF/CNPJ desde a primeira linha de código",
     "Chaves de armazenamento diferentes, arquivos de nuvem diferentes, e a IA de um espaço não "
     "enxerga o outro. Quando a holding formalizar, não haverá dado misturado para desenredar — "
     "que é o maior risco jurídico real."),
]


# ═══════════════════════════════════════════════════════════
# LIÇÕES — o que ficou aprendido
# ═══════════════════════════════════════════════════════════

LICOES = [
    ("Motor emprestado tem o limite de quem empresta",
     "A independência não vem de escolher a melhor API — vem de o motor ser trocável e a memória "
     "ser própria. Por isso a arquitetura tem quatro motores e um formato de memória documentado "
     "fora do código."),

    ("A casca é descartável; o que está dentro, não",
     "Código de PWA qualquer um escreve igual. O que transforma a casca no app de Samuel é a "
     "memória, as regras e as calibragens. Outra pessoa com o mesmo código tem uma casca vazia."),

    ("Cabine sem motor não anda",
     "Foram várias sessões construindo o app (P2) enquanto o Sistema Próprio (P1) não saía do "
     "papel — e o próprio arquivo diz que P1 bloqueia o resto. A ferramenta ficou pronta antes do "
     "caixa existir. Isso tem custo real e está registrado como alerta no tabuleiro."),

    ("Fonte primária vale mais que comentário sobre a fonte",
     "Para a SELIC, a fonte não é notícia sobre a SELIC — é o número saindo do Banco Central. Das "
     "dez fontes ativas do coletor, oito são primárias. Filtrar mentira depois é briga perdida; "
     "escolher a origem antes resolve."),

    ("Coletor não pesquisa, coletor assina",
     "Busca é puxar por pergunta: cara, limitada, sempre com teto. Feed é receber por assinatura: "
     "grátis, ilimitado, feito exatamente para isso. A API de busca do Google fechou para novos "
     "clientes — se o coletor dependesse dela, teria nascido morto."),

    ("Prompt grande demais no motor pequeno trunca a resposta",
     "O app monta prompt com método, memória, ferramentas e arquivos. No motor local ele encolhe "
     "sozinho pela metade, preservando método, escopo, segurança e formato. O contexto do llama.cpp "
     "também se ajusta à RAM do aparelho."),
]


# ═══════════════════════════════════════════════════════════
# FATOS VERIFICADOS — checados durante a construção
# Vão para a biblioteca marcados pelo grau da fonte.
# ═══════════════════════════════════════════════════════════

FATOS = [
    ("sistemas", 1, "Google Custom Search JSON API",
     "API de busca do Google fechada para novos clientes e com descontinuação anunciada",
     "Rota morta para o coletor: não é questão de preço, não dá nem para se cadastrar. "
     "Confirmado durante a construção, ago/2026.", ""),

    ("celular", 1, "llama.cpp — documentação oficial Android",
     "llama.cpp compila no Termux e serve API compatível com OpenAI na porta 8080",
     "Termux deve vir do F-Droid ou GitHub — a versão da Play Store foi abandonada e quebra na "
     "compilação. Backend Vulkan usa a GPU do celular sem root.", ""),

    ("computador", 2, "Verificação de capacidade de hardware",
     "RTX 4060 Ti 16GB roda modelos de 14B a 32B quantizados, não 70B",
     "Modelo de 70B exige mais de 40 GB de VRAM mesmo em quantização agressiva. Corrige premissa "
     "anterior do arquivo. Alvo realista para o PC: 14B a 32B.", ""),

    ("celular", 2, "Escolha de modelo por memória",
     "Modelo local deve ser escolhido pela RAM real do aparelho, não pelo desejo",
     "Acima de 8 GB: modelo de 3B. Entre 6 e 8 GB: 1,5B. Abaixo: 0,5B. Modelo grande demais para "
     "a memória trava o aparelho inteiro. O instalador decide sozinho.", ""),

    ("sistemas", 1, "Capacitor + GitHub Actions",
     "APK Android pode ser compilado na nuvem, sem PC, pelo próprio celular",
     "O envelope nativo carrega o mesmo index.html — nada é reescrito. iPhone exige Mac para "
     "compilar, sem contorno por software.", ""),

    ("ia", 2, "Limite de modelo pequeno",
     "Modelos de 1B a 4B servem para resumir, classificar e extrair dado estruturado",
     "Seguem instrução pior que modelo remoto e erram mais o formato JSON. O app aceita resposta "
     "fora do formato em vez de quebrar. Offline é degradado, não equivalente.", ""),

    ("sistemas", 1, "Termux job scheduler",
     "Tarefa agendada no Termux sobrevive à tela apagada e ao reinício do aparelho",
     "É o caminho viável para operação contínua sem VPS. O Android ainda pode matar o processo "
     "quando a memória aperta — rodada perdida acontece.", ""),

    ("negocios", 2, "Ordem de formalização",
     "CNPJ só no Marco 1; holding só quando o caixa justificar a manutenção",
     "Holding simples custa de R$2.000 a R$6.000 na abertura mais R$150 a R$400 por mês. Abrir "
     "antes do caixa é gasto fixo contra receita zero.", ""),
]


# ═══════════════════════════════════════════════════════════
# Montagem
# ═══════════════════════════════════════════════════════════

def montar_nucleo():
    extras, n = [], 0

    for titulo, corpo in CALIBRAGENS:
        extras.append({"id": id_seq("cal", n), "tag": "CALIBRAGEM",
                       "titulo": titulo, "corpo": corpo}); n += 1

    for titulo, corpo in DECISOES:
        extras.append({"id": id_seq("dec", n), "tag": "DECISÃO",
                       "titulo": "Aprovado: " + titulo, "corpo": corpo,
                       "criada": t - 86400000 * 3, "resultado": None}); n += 1

    for titulo, corpo in LICOES:
        extras.append({"id": id_seq("lic", n), "tag": "LIÇÃO",
                       "titulo": titulo, "corpo": corpo}); n += 1

    biblioteca = []
    hoje = datetime.now().strftime("%Y-%m-%d")
    for dominio, tier, fonte, titulo, corpo, url in FATOS:
        biblioteca.append({"dominio": dominio, "tier": tier, "fonte": fonte,
                           "titulo": titulo, "corpo": corpo, "url": url,
                           "coletado": hoje, "origem": "verificado na construção"})

    tabuleiro = {
        "alertas": [
            {"id": "al1", "nivel": "alta",
             "txt": "Nenhum cliente pagante ainda. A ferramenta ficou pronta antes do caixa existir "
                    "— essa inversão tem custo real."},
            {"id": "al2", "nivel": "alta",
             "txt": "P1 bloqueia o resto: sem sistema próprio rodando sozinho, 'IA que antecipa' "
                    "segue sendo descrição, não fato."},
            {"id": "al3", "nivel": "alta",
             "txt": "Memória vive no aparelho. Sem exportar ou subir cifrada, limpar dados do "
                    "navegador apaga tudo."},
            {"id": "al4", "nivel": "media",
             "txt": "Motor único é ponto de falha. Configure o segundo antes de precisar dele."},
        ],
        "fazer": [
            {"id": "f1", "txt": "Instalar Termux do F-Droid e rodar bash motor.sh", "ok": False},
            {"id": "f2", "txt": "Rodar o auto-teste do app antes de confiar em qualquer resposta", "ok": False},
            {"id": "f3", "txt": "Rodar o coletor e importar a biblioteca com base.py", "ok": False},
            {"id": "f4", "txt": "Sincronizar os dois celulares pela nuvem cifrada", "ok": False},
            {"id": "f5", "txt": "Fechar a primeira clínica — o primeiro caixa real", "ok": False},
        ],
        "naoFazer": [
            {"id": "n1", "txt": "Nunca subir chave de API ou memória exportada pro repositório público"},
            {"id": "n2", "txt": "Nunca aprovar módulo sem ler o código e rodar na caixa de teste"},
            {"id": "n3", "txt": "Nunca misturar dado do Núcleo com o da Operação"},
            {"id": "n4", "txt": "Nunca prometer ao cliente o que ainda não foi testado com dado real"},
            {"id": "n5", "txt": "Nunca abrir frente nova com a supervisão já no limite"},
            {"id": "n6", "txt": "Nunca subir VPS antes do primeiro cliente pago"},
            {"id": "n7", "txt": "Nunca tratar fonte agregadora como se fosse fonte primária"},
        ],
        "prazos": [],
        "ideias": [
            {"id": "i1", "criado": t,
             "txt": "Transformar lacuna reportada pelo [PESQUISA] em fonte nova no coletor — hoje "
                    "o ciclo não fecha sozinho aí."},
            {"id": "i2", "criado": t,
             "txt": "Rodada de destilação: condensar calibragens acumuladas em regras refinadas, "
                    "para o prompt não crescer sem limite."},
            {"id": "i3", "criado": t,
             "txt": "Transceptor acústico pode sincronizar dois celulares sem rede — hoje serve "
                    "para código curto, não para a memória inteira."},
        ],
        "registro": [
            {"id": "r1", "tipo": "decisão", "data": t,
             "txt": "Sistema construído: app com 9 modos, coletor de 9 domínios, base SQLite com "
                    "busca semântica, orquestrador com malha de 3 agentes, motor local, envelope nativo."},
            {"id": "r2", "tipo": "observação", "data": t,
             "txt": "Quatro bugs reais encontrados durante a construção, todos por procura ativa: "
                    "código duplicado, duas strings sem fechamento, handler órfão."},
            {"id": "r3", "tipo": "dica", "data": t,
             "txt": "O auto-teste do app é a primeira coisa a rodar quando algo parecer errado — "
                    "ele diz qual peça falhou em vez de deixar adivinhar."},
        ],
    }

    return {"espaco": "nucleo", "versao": 5,
            "data": datetime.now(timezone.utc).isoformat(),
            "extras": extras, "biblio": biblioteca,
            "tabuleiro": tabuleiro, "projetos": [], "modulos": []}


def montar_operacao():
    extras = [
        {"id": id_seq("op", 90), "tag": "ESTADO",
         "titulo": "Dor real do cliente, confirmada",
         "corpo": "Consolidar planilhas financeiras espalhadas de várias clínicas numa visão única "
                  "e clara para o chefe. Eles já têm planilha automatizada e bem feita — o problema "
                  "não é gerar relatório, é juntar o que está separado. Nenhuma automação atende "
                  "isso hoje."},
        {"id": id_seq("op", 91), "tag": "ESTRUTURA",
         "titulo": "Dois modos de entrada, uma base só",
         "corpo": "Modo A, consolidação: o app lê as planilhas que cada clínica já mantém — não "
                  "força ninguém a mudar hábito. Modo B, entrada direta: o dado é digitado no app. "
                  "Os dois alimentam a mesma base; o chefe vê um painel só, não importa a origem."},
        {"id": id_seq("op", 92), "tag": "PRINCÍPIO",
         "titulo": "O limite que não se cruza sem decisão explícita",
         "corpo": "Escopo é financeiro agregado: entrada, saída, tendência. Se o relatório passar a "
                  "detalhar procedimento por paciente, vira dado de saúde e entra em regime legal "
                  "muito mais restrito. Esse limite tem dono nomeado: Samuel."},
        {"id": id_seq("op", 93), "tag": "ESTRUTURA",
         "titulo": "A peça mais segura é a que não existe",
         "corpo": "Antes de blindar o banco de dados do cliente, a pergunta é se ele precisa "
                  "existir. Se o app processar e devolver sem guardar, a responsabilidade sobre o "
                  "dado quase desaparece. Aplicação direta do passo 2 do Algoritmo."},
        {"id": id_seq("op", 94), "tag": "ESTADO",
         "titulo": "Canal de entrada e o papel da irmã nº2",
         "corpo": "Ela não opera nada para Samuel. O ganho dela é subir de hierarquia na própria "
                  "empresa com apoio de prospecção — ela sobe, ele ganha visibilidade e a "
                  "recomendação vem de dentro, sem forçar entrada. Nunca pedir nada a ela: só "
                  "entregar valor."},
    ]
    return {"espaco": "operacao", "versao": 5,
            "data": datetime.now(timezone.utc).isoformat(),
            "extras": extras, "biblio": [], "tabuleiro": None,
            "projetos": [], "modulos": []}


if __name__ == "__main__":
    n = montar_nucleo()
    o = montar_operacao()

    with open("semente-nucleo.json", "w", encoding="utf-8") as f:
        json.dump(n, f, ensure_ascii=False, indent=1)
    with open("semente-operacao.json", "w", encoding="utf-8") as f:
        json.dump(o, f, ensure_ascii=False, indent=1)

    cal = len([x for x in n["extras"] if x["tag"] == "CALIBRAGEM"])
    dec = len([x for x in n["extras"] if x["tag"] == "DECISÃO"])
    lic = len([x for x in n["extras"] if x["tag"] == "LIÇÃO"])
    tb = n["tabuleiro"]

    print("\nSEMENTE GERADA\n")
    print(f"  semente-nucleo.json")
    print(f"    {cal} calibragens  — as correções que você fez, para não se repetirem")
    print(f"    {dec} decisões     — o que já está fechado, com o porquê")
    print(f"    {lic} lições       — o que ficou aprendido")
    print(f"    {len(n['biblio'])} fatos verificados na biblioteca")
    print(f"    tabuleiro: {len(tb['alertas'])} alertas · {len(tb['fazer'])} ações · "
          f"{len(tb['naoFazer'])} nunca-fazer · {len(tb['ideias'])} ideias")
    print(f"\n  semente-operacao.json")
    print(f"    {len(o['extras'])} blocos do cliente\n")
    print("  No app: Ajustes → Importar. Uma vez em cada espaço.")
    print("  A IA nasce sabendo, em vez de aprender tudo de novo.\n")
