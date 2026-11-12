import { atom, read, update } from 'claude-code'
import type { ElementTable, EngineInterface, Register } from 'claude-code'

import type { PanelData } from '../types'

// Sancho panel, part of the sancho plugin for the Claude app (Code tab) and
// Claude Code: a band above the prompt, toasts on change, and a details pane.
// Every value comes from one read-only helper, hooks/sancho_panel.py, run in
// the session's folder:
//   status  -> skills/sancho/scripts/state.py status --json, the skill bundled
//              in this plugin (.sancho/state.json & co.)
//   zip     -> only in a repository checkout: dist/sancho.zip compared file by
//              file with skills/sancho (build.py rules)
// Nothing is written, in the plugin or in the project.

const PANE = 'sancho'
const TITLE = 'Sancho'
const REFRESH_MS = 20000

const data = atom({ plugin: 'sancho', key: 'data' } as const, null, {
  shape: 'data-1',
})

const PHASES = ['discover', 'specify', 'plan', 'tasks', 'implement', 'verify', 'release', 'evolve']
const SHORT: Record<string, string> = {
  discover: 'DIS', specify: 'SPE', plan: 'PLA', tasks: 'TAS',
  implement: 'IMP', verify: 'VER', release: 'REL', evolve: 'EVO',
}

// Theme keys for Text, hex for the SVG drawings (both readable on light and dark).
type Gate = { label: string; color?: string; hex: string; glyph: string }
const GATE: Record<string, Gate> = {
  approved: { label: 'approvata', color: 'success', hex: '#3fb950', glyph: '●' },
  skipped: { label: 'saltata', color: 'inactive', hex: '#8b949e', glyph: '◌' },
  in_progress: { label: 'in corso', color: 'warning', hex: '#d97757', glyph: '◉' },
  awaiting_approval: { label: 'attende la tua approvazione', color: 'permission', hex: '#a371f7', glyph: '◆' },
  rejected: { label: 'respinta', color: 'error', hex: '#f85149', glyph: '✕' },
  not_started: { label: 'da iniziare', color: 'inactive', hex: '#8b949e', glyph: '○' },
}
const gateOf = (status: string | undefined): Gate =>
  GATE[status ?? ''] ?? { label: String(status ?? '?'), hex: '#8b949e', glyph: '?' }

const ROLE: Record<string, string> = {
  user: 'tu',
  'analyst-pm': 'analista/PM',
  'ux-ui': 'UX/UI',
  architect: 'architetto',
  developer: 'sviluppatore',
  qa: 'QA',
  security: 'sicurezza',
  'release-manager': 'release manager',
}

const SEVERITY: Record<string, string> = { blocker: 'error', major: 'warning', minor: 'suggestion', nit: 'inactive' }

// Commands in the plugin form, `/sancho:<command>`, the one state.py speaks too.
function commandsFor(status: Record<string, any> | null) {
  if (status === null) {
    return [
      { cmd: '/sancho:discover', why: 'inizia un nuovo progetto' },
      { cmd: '/sancho:assess', why: 'valuta un progetto esistente' },
      { cmd: '/sancho:help', why: 'giro guidato' },
    ]
  }
  const list = [
    { cmd: '/sancho:status', why: 'dove siamo' },
    { cmd: '/sancho:next', why: 'il prossimo passo' },
    { cmd: '/sancho:checkpoint', why: 'salva un punto di ripresa' },
    { cmd: '/sancho:assess', why: 'controllo di coerenza' },
    { cmd: '/sancho:help', why: 'tutti i comandi' },
  ]
  const ph = status.current_phase as string | undefined
  if (ph) list.unshift({ cmd: `/sancho:${ph}`, why: `lavora su ${ph.toUpperCase()}` })
  return list
}

// Text from outside (paths, stderr) may hold escape sequences a surface refuses.
function clean<T>(value: T): T {
  if (typeof value === 'string')
    return value.replace(/\x1b\[[0-9;]*[A-Za-z]/g, '').replace(/[\u0000-\u0008\u000b-\u001f\u007f]/g, '') as T
  if (Array.isArray(value)) return value.map(clean) as T
  if (value !== null && typeof value === 'object') {
    return Object.fromEntries(Object.entries(value).map(([k, v]) => [k, clean(v)])) as T
  }
  return value
}

// `python` on Windows, often only `python3` on macOS and Linux.
async function runHelper($: EngineInterface): Promise<string> {
  let last: unknown = new Error('python non trovato')
  for (const exe of ['python', 'python3']) {
    try {
      const run = await $.process.run([exe, '-I', `${$.plugin.root}/hooks/sancho_panel.py`], { timeoutMs: 40000 })
      if (run.exitCode === 0) return run.stdout
      last = new Error(run.stderr.trim().slice(-300) || `${exe}: exit ${run.exitCode}`)
    } catch (err) {
      last = err
    }
  }
  throw last
}

async function refresh($: EngineInterface) {
  const cwd = await $.session.cwd()
  let next: PanelData
  try {
    const parsed = JSON.parse(await runHelper($))
    next = { ...parsed, checkedAt: await $.clock.now() }
  } catch (err) {
    next = {
      checkedAt: await $.clock.now(),
      status: null,
      error: `Impossibile leggere lo stato: ${String((err as Error)?.message ?? err)}`,
      cwd,
      zip: { state: 'none', detail: '' },
    }
  }
  const fresh = clean(next)
  let before: PanelData | null = null
  await update($, data, prev => {
    before = prev
    return fresh
  })
  const change = describeChange(before, fresh)
  if (change !== null) $.ui.toast(change)
}

// A toast when something the person must act on changes: the current gate,
// the next step, or the zip falling out of date. Not on the first read.
function describeChange(before: PanelData | null, after: PanelData): string | null {
  const a = before?.status ?? null
  const b = after.status
  if (a === null || b === null || before?.cwd !== after.cwd) return null
  const phaseA = a.current_phase as string | undefined
  const phaseB = b.current_phase as string | undefined
  const gateA = a.phases?.[phaseA ?? '']
  const gateB = b.phases?.[phaseB ?? '']
  if (phaseA !== phaseB || gateA !== gateB) {
    return `Sancho: ${(phaseB ?? '—').toUpperCase()} — gate ${gateOf(gateB).label}`
  }
  if (a.next?.action !== b.next?.action && b.next?.action) {
    return `Sancho, prossimo passo (${ROLE[b.next.who] ?? b.next.who}): ${b.next.action}`
  }
  if (before?.zip.state === 'ok' && after.zip.state === 'stale') {
    return 'Sancho: dist/sancho.zip non è più allineato a skills/sancho'
  }
  return null
}

// ---------------------------------------------------------------- drawings

// The eight phases as a stepper: one circle per phase, coloured by its gate.
function stepperSvg(phases: Record<string, string>, cur: string | undefined): string {
  const step = 42
  const x = (i: number) => 21 + i * step
  const parts: string[] = []
  for (let i = 0; i < PHASES.length - 1; i++) {
    const done = ['approved', 'skipped'].includes(phases[PHASES[i]!] ?? '')
    parts.push(`<line x1="${x(i) + 10}" y1="18" x2="${x(i + 1) - 10}" y2="18" stroke="${done ? '#3fb950' : '#8b949e'}" stroke-opacity="${done ? 0.8 : 0.35}" stroke-width="2"/>`)
  }
  PHASES.forEach((ph, i) => {
    const st = phases[ph] ?? 'not_started'
    const g = gateOf(st)
    const isCur = ph === cur
    const cx = x(i)
    if (isCur) parts.push(`<circle cx="${cx}" cy="18" r="13" fill="none" stroke="${g.hex}" stroke-opacity="0.45" stroke-width="2"/>`)
    if (st === 'not_started' || st === 'skipped') {
      parts.push(`<circle cx="${cx}" cy="18" r="9" fill="none" stroke="${g.hex}" stroke-width="2"${st === 'skipped' ? ' stroke-dasharray="3 2"' : ''}/>`)
    } else {
      parts.push(`<circle cx="${cx}" cy="18" r="9" fill="${g.hex}"/>`)
    }
    if (st === 'approved') parts.push(`<path d="M${cx - 4} 18 l3 3 l5 -6" fill="none" stroke="#fff" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>`)
    if (st === 'rejected') parts.push(`<path d="M${cx - 3.5} 14.5 l7 7 M${cx + 3.5} 14.5 l-7 7" stroke="#fff" stroke-width="2" stroke-linecap="round"/>`)
    if (st === 'in_progress') parts.push(`<circle cx="${cx}" cy="18" r="3.5" fill="#fff"/>`)
    if (st === 'awaiting_approval') parts.push(`<text x="${cx}" y="22" text-anchor="middle" font-size="11" font-weight="700" fill="#fff" font-family="system-ui, sans-serif">!</text>`)
    parts.push(`<text x="${cx}" y="48" text-anchor="middle" font-size="10" font-family="system-ui, sans-serif" font-weight="${isCur ? 700 : 500}" fill="${isCur ? g.hex : '#8b949e'}">${SHORT[ph]}</text>`)
  })
  return `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 336 56" width="100%">${parts.join('')}</svg>`
}

// UAT cases as one stacked bar: passed, failed, blocked, still to test.
function uatSvg(uat: Record<string, number>): string {
  const order: [string, string][] = [['pass', '#3fb950'], ['fail', '#f85149'], ['blocked', '#a371f7'], ['not_tested', '#8b949e']]
  const total = Object.values(uat).reduce((a, b) => a + b, 0) || 1
  let at = 0
  const parts = order
    .filter(([k]) => (uat[k] ?? 0) > 0)
    .map(([k, hex]) => {
      const w = ((uat[k] ?? 0) / total) * 300
      const r = `<rect x="${at}" y="0" width="${Math.max(w - 2, 1)}" height="8" rx="3" fill="${hex}"${k === 'not_tested' ? ' fill-opacity="0.4"' : ''}/>`
      at += w
      return r
    })
  return `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 300 8" width="100%">${parts.join('')}</svg>`
}

type Ui = ElementTable

function heading(ui: Ui, text: string) {
  const { Text } = ui
  return (
    <Text size="caption" weight="semibold" dimColor>
      {text.toUpperCase()}
    </Text>
  )
}

function badge(ui: Ui, text: string, color: string) {
  const { Text } = ui
  return (
    <Text backgroundColor={color} color="inverseText" weight="semibold" size="footnote">
      {` ${text} `}
    </Text>
  )
}

// ---------------------------------------------------------------- hooks

export const register: Register = on => {
  on('session.start', async ($, e, next) => {
    const started = await next(e)
    await $.command.register({ name: 'sancho-panel', description: 'Apre il pannello con i dettagli di Sancho' })
    // No pane opened unasked: the band above the prompt is the at-a-glance view,
    // its "dettagli" button (or /sancho-panel) opens the pane.
    void refresh($).catch(() => undefined)
    $.clock.every(REFRESH_MS, () => void refresh($).catch(() => undefined))
    return started
  })

  on('command.run', { command: 'sancho-panel' }, async $ => {
    await $.ui.open({ id: PANE, title: TITLE })
    await refresh($)
    return { text: 'Pannello Sancho aperto e aggiornato.' }
  })

  on('turn.complete', async ($, e, next) => {
    const done = await next(e)
    void refresh($).catch(() => undefined)
    return done
  })

  // Band above the prompt: the at-a-glance line. Silent where there is no Sancho project.
  on('ui.render', { component: 'AbovePrompt' }, async ($, e, next) => {
    if (e.props.hasSurvey) return next(e)
    const d = await read($, data)
    const s = d?.status ?? null
    if (d === null || s === null) return next(e)
    const ui = $.ui.resolve(e)
    const { Box, Text, Button } = ui
    const phases: Record<string, string> = s.phases ?? {}
    const cur = (s.current_phase as string | undefined) ?? ''
    const gate = gateOf(phases[cur])
    const nx = s.next ?? {}
    const blockers = (s.blockers?.length ?? 0) + (s.invalid_files?.length ?? 0)
    const stale = d.zip.state === 'stale' || d.zip.state === 'missing'
    return (
      <Box flexDirection="row" alignItems="center" gap={1}>
        <Text color="claude" weight="bold">✦ Sancho</Text>
        <Text>
          {PHASES.map(ph => (
            <Text color={ph === cur ? 'claude' : gateOf(phases[ph]).color}>{ph === cur ? '◉' : gateOf(phases[ph]).glyph}</Text>
          ))}
        </Text>
        <Text weight="semibold">{cur.toUpperCase() || '—'}</Text>
        <Text color={gate.color}>{gate.label}</Text>
        {blockers > 0 && badge(ui, `${blockers} blocker`, 'error')}
        {stale && badge(ui, 'zip da aggiornare', 'warning')}
        <Box flexGrow={1} flexShrink={1}>
          <Text wrap="truncate-end">
            <Text dimColor>→ </Text>
            <Text color="claude">{ROLE[nx.who] ?? nx.who ?? '?'}</Text>
            <Text dimColor>: </Text>
            {nx.action ?? '—'}
          </Text>
        </Box>
        <Button key="details" plain onPress={() => void $.ui.open({ id: PANE, title: TITLE })}>
          <Text color="suggestion">dettagli ›</Text>
        </Button>
      </Box>
    )
  })

  on('ui.render', { component: 'Pane', requestId: PANE }, async ($, e) => {
    const ui = $.ui.resolve(e)
    const { Box, Text, Button } = ui
    const Svg = e.surface === 'terminal' ? null : (ui as ElementTable<'desktop'>).Svg
    const d = await read($, data)
    const fill = (cmd: string) => () => void $.prompt.fill({ text: cmd + ' ', mode: 'replace' })
    const refreshButton = (
      <Button key="refresh" plain onPress={() => void refresh($).catch(() => undefined)}>
        <Text color="suggestion">↻ Aggiorna</Text>
      </Button>
    )

    if (d === null)
      return (
        <Box flexDirection="column" gap={1}>
          <Text dimColor>Leggo lo stato del progetto…</Text>
          {refreshButton}
        </Box>
      )

    const s = d.status
    const time = new Date(d.checkedAt).toLocaleTimeString('it-IT', { hour: '2-digit', minute: '2-digit' })
    const commands = commandsFor(s)
    const sections: any[] = []

    if (s === null) {
      // Empty state: no .sancho/ here.
      sections.push(
        <Box flexDirection="column" gap={1}>
          <Text size="heading" weight="semibold">Nessun progetto Sancho qui</Text>
          <Text size="footnote" dimColor mono wrap="truncate-middle">{d.cwd}</Text>
          {d.error !== null && <Text color="error">{d.error}</Text>}
          <Text dimColor>Avvia Sancho in questa cartella, oppure apri una sessione nella cartella di un progetto Sancho.</Text>
        </Box>,
      )
    } else {
      const proj = s.project ?? {}
      const phases: Record<string, string> = s.phases ?? {}
      const cur = s.current_phase as string | undefined
      const g = gateOf(phases[cur ?? ''])
      const nx = s.next ?? {}
      const defects = s.open_defects ?? {}
      const sec = s.security ?? null
      const blockers: string[] = s.blockers ?? []
      const invalid: any[] = s.invalid_files ?? []
      const uat: Record<string, number> = s.uat ?? {}
      const tasks: Record<string, number> = s.tasks ?? {}

      // Header
      const platforms: string[] = proj.platforms ?? []
      sections.push(
        <Box flexDirection="column">
          <Text size="title" weight="bold">{proj.name ?? 'Progetto'}</Text>
          <Text size="footnote" dimColor>
            Livello {proj.level ?? '?'}{platforms.length > 0 ? ` · ${platforms.join(', ')}` : ''}
          </Text>
          <Text size="footnote" dimColor mono wrap="truncate-middle">{d.cwd}</Text>
        </Box>,
      )

      // Phases and gate
      sections.push(
        <Box flexDirection="column" gap="sm">
          {heading(ui, 'Fasi')}
          {Svg !== null ? (
            <Svg source={stepperSvg(phases, cur)} alt={`Fasi: ${PHASES.map(p => `${p} ${gateOf(phases[p]).label}`).join(', ')}`} />
          ) : (
            <Text>
              {PHASES.map(ph => (
                <Text color={ph === cur ? 'claude' : gateOf(phases[ph]).color}>{ph === cur ? '◉' : gateOf(phases[ph]).glyph} </Text>
              ))}
            </Text>
          )}
          <Text>
            Fase attuale <Text weight="bold">{(cur ?? '—').toUpperCase()}</Text>
            <Text dimColor> · gate </Text>
            <Text color={g.color} weight="semibold">{g.label}</Text>
          </Text>
        </Box>,
      )

      // The single next step, as a card
      sections.push(
        <Box flexDirection="column" borderStyle="round" borderColor="claude" paddingX={1} paddingY="xs" gap="xs">
          {heading(ui, 'Prossimo passo')}
          <Text>
            {badge(ui, ROLE[nx.who] ?? nx.who ?? '?', 'claude')} {nx.action ?? '—'}
          </Text>
        </Box>,
      )

      // Open issues
      const rows: any[] = []
      for (const b of blockers) rows.push(<Text>{badge(ui, 'blocker', 'error')} {b}</Text>)
      for (const f of invalid) rows.push(<Text>{badge(ui, 'file non valido', 'error')} {f.path}</Text>)
      const sevBadges = (counts: Record<string, number>) =>
        ['blocker', 'major', 'minor', 'nit']
          .filter(k => (counts[k] ?? 0) > 0)
          .map(k => <Text>{badge(ui, `${counts[k]} ${k}`, SEVERITY[k]!)} </Text>)
      const defectBadges = sevBadges(defects)
      if (defectBadges.length > 0) rows.push(<Text>Difetti UAT aperti  {defectBadges}</Text>)
      if (sec !== null) {
        const secBadges = sevBadges(sec)
        const fixed = Object.values((sec.closed ?? {}) as Record<string, number>).reduce((a, b) => a + b, 0)
        if (secBadges.length > 0) rows.push(<Text>Sicurezza aperta  {secBadges}{fixed > 0 && <Text dimColor size="footnote"> {fixed} risolti</Text>}</Text>)
        for (const nr of sec.not_run ?? []) rows.push(<Text size="footnote" dimColor>⊘ Non eseguito: {nr}</Text>)
      }
      const clear = blockers.length === 0 && invalid.length === 0
      sections.push(
        <Box flexDirection="column" gap="xs">
          {heading(ui, 'Da risolvere')}
          {clear && <Text color="success">✓ Nessun blocker</Text>}
          {rows}
        </Box>,
      )

      // Progress: UAT bar and tasks
      const uatTotal = Object.values(uat).reduce((a, b) => a + b, 0)
      const taskTotal = Object.values(tasks).reduce((a, b) => a + b, 0)
      if (uatTotal > 0 || taskTotal > 0) {
        sections.push(
          <Box flexDirection="column" gap="xs">
            {heading(ui, 'Avanzamento')}
            {taskTotal > 0 && (
              <Text>
                Task <Text weight="semibold">{tasks.completed ?? 0}/{taskTotal}</Text>
                <Text dimColor> completati{(tasks.in_progress ?? 0) > 0 ? ` · ${tasks.in_progress} in corso` : ''}</Text>
              </Text>
            )}
            {uatTotal > 0 && (
              <Text>
                UAT <Text weight="semibold">{uat.pass ?? 0}/{uatTotal}</Text>
                <Text dimColor> superati</Text>
                {(uat.fail ?? 0) > 0 && <Text color="error"> · {uat.fail} falliti</Text>}
                {(uat.not_tested ?? 0) > 0 && <Text dimColor> · {uat.not_tested} da testare</Text>}
              </Text>
            )}
            {uatTotal > 0 && Svg !== null && <Svg source={uatSvg(uat)} alt={`UAT: ${uat.pass ?? 0} superati su ${uatTotal}`} />}
          </Box>,
        )
      }
    }

    // Commands: pressed, they go into the prompt (never sent on their own)
    const [first, ...rest] = commands
    sections.push(
      <Box flexDirection="column" gap="xs">
        {heading(ui, 'Comandi')}
        {first !== undefined && (
          <Button key={first.cmd} variant="primary" onPress={fill(first.cmd)}>
            {first.cmd} <Text dimColor>{first.why}</Text>
          </Button>
        )}
        {rest.map(c => (
          <Button key={c.cmd} plain onPress={fill(c.cmd)}>
            <Text mono color="suggestion">{c.cmd}</Text> <Text dimColor size="footnote">{c.why}</Text>
          </Button>
        ))}
        <Text size="caption" dimColor>Un clic scrive il comando nel prompt: poi premi Invio.</Text>
      </Box>,
    )

    // The ZIP for the Claude apps, only in a repository checkout
    if (d.zip.state === 'none') {
      // installed plugin: the skill is bundled, there is no ZIP to compare
    } else if (d.zip.state === 'ok') {
      sections.push(
        <Box flexDirection="column">
          {heading(ui, 'Zip per le app Claude')}
          <Text color="success">✓ zip allineato al repository</Text>
          <Text size="caption" dimColor>Confronta dist/sancho.zip con skills/sancho; non vede il tuo account.</Text>
        </Box>,
      )
    } else {
      sections.push(
        <Box flexDirection="column" borderStyle="round" borderColor="warning" paddingX={1} paddingY="xs" gap="xs">
          {heading(ui, 'Zip per le app Claude')}
          <Text color="warning" weight="semibold">
            ⚠ {d.zip.state === 'stale' ? 'dist/sancho.zip non è aggiornato' : 'Controllo dello zip non riuscito'}
          </Text>
          {d.zip.detail !== '' && <Text size="footnote" dimColor>{d.zip.detail}</Text>}
          {d.zip.state === 'stale' && (
            <Text size="footnote">
              Rigenera con <Text mono>python tools/build.py --zip</Text> e ricarica lo zip sul tuo account.
            </Text>
          )}
        </Box>,
      )
    }

    return (
      <Box flexDirection="column" gap="md">
        {sections}
        <Box flexDirection="row" justifyContent="space-between" alignItems="center">
          <Text size="caption" dimColor>Aggiornato alle {time}</Text>
          {refreshButton}
        </Box>
      </Box>
    )
  })
}
