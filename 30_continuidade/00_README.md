# 30 — Continuidade Operacional

Camada independente de continuidade do Sistema Absoluto.

## Objetivo

Garantir que uma interrupção não apague o estado operacional nem quebre a capacidade de retomar o trabalho.

A camada mantém:
1. estado atual — `state.json`
2. diário causal append-only — `journal.jsonl`
3. checkpoints recuperáveis — `checkpoints/`
4. sinais de vida e posse — `heartbeat.json` / `lease.json`

O diário usa uma cadeia SHA-256: cada evento referencia o hash do evento anterior.

## Propriedades

- somente biblioteca padrão Python;
- gravação atômica do estado;
- verificável sem IA;
- recuperação pelo último checkpoint;
- retenção dos últimos 20 checkpoints;
- exportação para ZIP portátil;
- compatível com Termux/Linux;
- independente do runtime histórico.

## Uso

```bash
python3 30_continuidade/continuity.py --root ~/.sistema-absoluto/continuidade init
python3 30_continuidade/continuity.py --root ~/.sistema-absoluto/continuidade status
python3 30_continuidade/continuity.py --root ~/.sistema-absoluto/continuidade checkpoint --reason "fim de sessão"
python3 30_continuidade/continuity.py --root ~/.sistema-absoluto/continuidade verify
python3 30_continuidade/continuity.py --root ~/.sistema-absoluto/continuidade recover
python3 30_continuidade/continuity.py --root ~/.sistema-absoluto/continuidade export ~/continuidade.zip
```

## Regra arquitetural

Esta camada não substitui o ABS V1 nem declara o runtime histórico como atual. Ela fornece uma fundação portátil de continuidade que pode ser integrada ao sistema ativo após validação.

## Fluxo futuro

`iniciar → adquirir lease → carregar estado → operar → registrar eventos → checkpoint → liberar lease`

Em falha:

`detectar interrupção → verificar integridade → recuperar último checkpoint → registrar recovery → retomar`
