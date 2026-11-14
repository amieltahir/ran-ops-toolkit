# Mock CLI dialect (DRAFT for your review)

Written to be corrected. I do not have verified knowledge of real Ericsson
output, so every command name and output format below is a **placeholder
assumption**. You worked on Ericsson OSS-RC and ENIQ; replace anything that does
not match what you remember. Only your own recollection and public material may
be used; nothing from licensed documentation.

## Design rules

- Read-only: `set` and any write command return an error line and change nothing.
- One SSH server, multiplexed node identities (chosen by login user or host key).
- Output is plain text, line oriented, deterministic for a given seed.
- Each command's output must be derivable from the generator's truth data.

## Commands (v0.1)

| Command | Purpose | Assumed output shape | Your correction | Status |
|---|---|---|---|---|
| `st cell` | cell admin and operational state | one row per cell: cell name, admin state, operational state | _fill in_ | draft |
| `get <cell> <attr>` | read a parameter on a cell | row per matching object: object name, attribute, value | _fill in_ | draft |
| `get . <attr>` | read a node-level parameter | same as above, node scope | _fill in_ | draft |
| `alt` | list active alarms | one row per alarm: time, severity, object, specific problem | _fill in_ | draft |
| `set ...` | write | rejected: `Error: node is read-only (lab)` | n/a | fixed |

## Open questions for you

1. What do the real state values look like (words, numbers, both)?
2. How are cell and node names structured in real output?
3. Which alarm columns matter for health checks?
4. Is there a lighter command than the one I guessed for each row?

## Change log

Record each correction with the date so the parser tests follow the dialect.
