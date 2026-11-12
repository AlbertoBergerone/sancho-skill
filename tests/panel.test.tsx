import { expect, test } from 'claude-code/testing'
import type { CommandRunInput, On } from 'claude-code'

const OPEN: CommandRunInput = {
  command: 'sancho-panel',
  args: '',
  origin: { kind: 'composer' },
  presentation: { isFullscreen: true, columns: 120 },
} as CommandRunInput

// Real output of hooks/sancho_panel.py in sancho-collaudo/fieldlog.
const FIELDLOG = {"cwd": "C:\\Users\\Utente\\Documents\\sancho-collaudo\\fieldlog", "status": {"project": {"name": "FieldLog", "summary": "Job logging for field technicians (Android, offline) with a web back-office.", "level": "L2", "platforms": ["android", "web", "api"], "repository": "https://example.invalid/fieldlog"}, "current_phase": "verify", "phases": {"discover": "approved", "specify": "approved", "plan": "approved", "tasks": "approved", "implement": "approved", "verify": "in_progress", "release": "not_started", "evolve": "not_started"}, "tasks": {"completed": 11, "in_progress": 1}, "uat": {"fail": 1, "pass": 2, "not_tested": 3}, "open_defects": {"blocker": 0, "major": 1, "minor": 0, "nit": 0}, "security": {"blocker": 0, "major": 1, "minor": 1, "nit": 0, "closed": {"fixed": 1}, "not_run": ["MobSF static analysis of the Android APK (tool not installed)"]}, "blockers": [], "approvals": 1, "last_checkpoint": "2026-10-23T17:40:00+02:00", "invalid_files": [], "next": {"who": "developer", "phase": "verify", "action": "Fix DEF-001 (major): Sign-in error reveals that an email is not registered ('User not found'), enabling account enumeration (TM-01)"}}, "error": null, "zip": {"state": "ok", "detail": "dist/sancho.zip = skills/sancho (54 file)"}}
const STALE = {"cwd": "C:\\Users\\Utente\\Documents\\sancho-collaudo\\fieldlog", "status": {"project": {"name": "FieldLog", "summary": "Job logging for field technicians (Android, offline) with a web back-office.", "level": "L2", "platforms": ["android", "web", "api"], "repository": "https://example.invalid/fieldlog"}, "current_phase": "verify", "phases": {"discover": "approved", "specify": "approved", "plan": "approved", "tasks": "approved", "implement": "approved", "verify": "in_progress", "release": "not_started", "evolve": "not_started"}, "tasks": {"completed": 11, "in_progress": 1}, "uat": {"fail": 1, "pass": 2, "not_tested": 3}, "open_defects": {"blocker": 0, "major": 1, "minor": 0, "nit": 0}, "security": {"blocker": 0, "major": 1, "minor": 1, "nit": 0, "closed": {"fixed": 1}, "not_run": ["MobSF static analysis of the Android APK (tool not installed)"]}, "blockers": [], "approvals": 1, "last_checkpoint": "2026-10-23T17:40:00+02:00", "invalid_files": [], "next": {"who": "developer", "phase": "verify", "action": "Fix DEF-001 (major): Sign-in error reveals that an email is not registered ('User not found'), enabling account enumeration (TM-01)"}}, "error": null, "zip": {"state": "stale", "detail": "1 modificati (SKILL.md)"}}
const EMPTY = {"cwd": "C:/altro", "status": null, "error": null, "zip": {"state": "ok", "detail": "ok"}}

const PANE = {
  plugin: 'sancho',
  component: 'Pane',
  requestId: 'sancho',
  props: { title: 'Sancho', isFocused: false, bodyColumns: 60, placement: 'dock', scroll: { offset: 0, bodyRows: 40 }, view: {} },
} as const

const BAND = {
  plugin: 'sancho',
  component: 'AbovePrompt',
  props: { hasSurvey: false, isWorking: false, maxRows: 6, bodyColumns: 120, scroll: { offset: 0, bodyRows: 5 }, view: {} },
} as const

function engine(on: On, payload: unknown) {
  on('process.run', () => ({ value: { exitCode: 0, stdout: JSON.stringify(payload), stderr: '', isStdoutTruncated: false, isStderrTruncated: false } }))
  on('session.cwd', () => ({ value: 'C:/progetto' }))
  on('clock.now', () => ({ value: 0 }))
  on('ui.open', () => ({ value: { isPlaced: true } }))
}

for (const surface of ['terminal', 'desktop'] as const) {
  test(`panel shows phase, next step, issues and commands (${surface})`, async ($, on) => {
    engine(on, FIELDLOG)
    const ui = await $.ui.mount({ ...PANE, surface })
    await $.command.run(OPEN)
    expect((await ui.find({ type: 'Text', text: /Fase attuale/ }))?.text).toContain('VERIFY')
    expect((await ui.find({ type: 'Text', text: /Fix DEF-001/ }))?.text).toContain('sviluppatore')
    expect((await ui.find({ type: 'Text', text: /Difetti UAT aperti/ }))?.text).toContain('1 major')
    expect(await ui.find({ type: 'Button', key: '/sancho:verify' })).toBeDefined()
    expect((await ui.find({ type: 'Text', text: /zip allineato/ }))).toBeDefined()
    await ui.unmount()
  })

  test(`installed plugin: no ZIP section (${surface})`, async ($, on) => {
    engine(on, { ...FIELDLOG, zip: { state: 'none', detail: '' } })
    const ui = await $.ui.mount({ ...PANE, surface })
    await $.command.run(OPEN)
    expect(await ui.find({ type: 'Text', text: /Fase attuale/ })).toBeDefined()
    expect(await ui.find({ type: 'Text', text: /zip/i })).toBeUndefined()
    await ui.unmount()
  })

  test(`band shows the one-line summary (${surface})`, async ($, on) => {
    engine(on, STALE)
    const pane = await $.ui.mount({ ...PANE, surface })
    await $.command.run(OPEN)
    await pane.unmount()
    const band = await $.ui.mount({ ...BAND, surface })
    const line = (await band.findAll({ type: 'Text' })).map(x => x.text).join(' ')
    expect(line).toContain('VERIFY')
    expect(line).toContain('in corso')
    expect(line).toContain('zip da aggiornare')
    expect(line).toContain('sviluppatore')
    expect(line).toContain('Fix DEF-001')
    expect(await band.find({ type: 'Button', key: 'details' })).toBeDefined()
    await band.unmount()
  })

  test(`no Sancho project: panel says so, band stays silent (${surface})`, async ($, on) => {
    engine(on, EMPTY)
    on('ui.render', ($, e) => { const { Text } = $.ui.resolve(e); return <Text>engine</Text> })
    const pane = await $.ui.mount({ ...PANE, surface })
    await $.command.run(OPEN)
    expect(await pane.find({ type: 'Text', text: /Nessun progetto Sancho/ })).toBeDefined()
    expect(await pane.find({ type: 'Button', key: '/sancho:discover' })).toBeDefined()
    await pane.unmount()
    const band = await $.ui.mount({ ...BAND, surface })
    expect((await band.find({ type: 'Text' }))?.text).toBe('engine')
    await band.unmount()
  })
}

test('session start opens no pane by itself', async ($, on) => {
  on('process.run', () => ({
    value: { exitCode: 0, stdout: JSON.stringify(FIELDLOG), stderr: '', isStdoutTruncated: false, isStderrTruncated: false },
  }))
  on('session.cwd', () => ({ value: 'C:/progetto' }))
  on('clock.now', () => ({ value: 0 }))
  const opened: string[] = []
  on('ui.open', (_, e) => {
    opened.push(e.id)
    return { value: { isPlaced: true } }
  })
  on('command.register', () => ({ value: { command: 'sancho-panel' } }))
  on('session.start', (_, e) => ({ cwd: e.cwd }))
  await $.session.start({ cwd: '/', surface: 'desktop', isInteractive: true })
  expect(opened).toEqual([])
})

test('a toast when the next step changes, none on the first read', async ($, on) => {
  let payload: any = FIELDLOG
  on('process.run', () => ({
    value: { exitCode: 0, stdout: JSON.stringify(payload), stderr: '', isStdoutTruncated: false, isStderrTruncated: false },
  }))
  on('session.cwd', () => ({ value: 'C:/progetto' }))
  on('clock.now', () => ({ value: 0 }))
  on('ui.open', () => ({ value: { isPlaced: true } }))
  const toasts: string[] = []
  on('ui.toast', (_, e) => {
    toasts.push(e.text)
    return { value: undefined }
  })
  await $.command.run(OPEN)
  expect(toasts).toEqual([])
  payload = { ...FIELDLOG, status: { ...FIELDLOG.status, next: { who: 'user', phase: 'verify', action: 'Run UAT-004 on android. Use /sancho:verify for guided steps.' } } }
  await $.command.run(OPEN)
  expect(toasts).toHaveLength(1)
  expect(toasts[0]).toContain('/sancho:verify')
  expect(toasts[0]).toContain('tu')
})
