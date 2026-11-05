#!/usr/bin/env node
import { spawnSync } from 'node:child_process';
import { accessSync, constants, existsSync, mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { createConnection } from 'node:net';

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const lock = JSON.parse(readFileSync(join(root, 'emulator/config/simulator.lock.json')));
const stateIndex = process.argv.indexOf('--state');
const state = stateIndex < 0 ? join(root, 'emulator/state/stock') : resolve(root, process.argv[stateIndex + 1] || 'emulator/state/stock');
if (!state.startsWith(join(root, 'emulator/state') + '/')) throw new Error('Simulator state must be inside workspace emulator/state/.');
const base = join(root, 'emulator/images', lock.version, 'BlackBerry10Simulator.vmdk');
const disk = join(state, 'BB10.qcow2');
const socket = join(state, 'qmp.sock');
mkdirSync(state, { recursive: true });

function run(cmd, args, capture = false) {
  const r = spawnSync(cmd, args, { cwd: root, stdio: capture ? 'pipe' : 'inherit', encoding: 'utf8' });
  if (r.error || r.status !== 0) throw new Error(`${cmd}: ${r.error?.message || r.stderr || r.status}`);
  return r.stdout;
}

function hasKvm() {
  try { accessSync('/dev/kvm', constants.R_OK | constants.W_OK); return true; }
  catch { return false; }
}

function args() {
  const accel = process.argv.includes('--tcg') || !hasKvm() ? 'tcg' : 'kvm';
  return ['-name', `BB10-${lock.version}-experimental`, '-machine', 'pc,vmport=on',
    '-accel', accel, '-cpu', accel === 'kvm' ? 'host' : 'max', '-smp', '1', '-m', '2048',
    '-vga', 'none', '-device', 'vmware-svga,vgamem_mb=128',
    '-drive', `file=${disk},if=ide,format=qcow2`,
    '-netdev', 'user,id=net0,restrict=on,hostfwd=tcp:127.0.0.1:2222-:22,hostfwd=tcp:127.0.0.1:2323-:23,hostfwd=tcp:127.0.0.1:2443-:443',
    '-device', 'pcnet,netdev=net0', '-usb', '-device', 'usb-tablet',
    '-display', 'none', '-vnc', '127.0.0.1:10',
    '-qmp', `unix:${socket},server=on,wait=off`,
    '-serial', `file:${join(state, 'serial.log')}`, '-monitor', 'none',
    '-pidfile', join(state, 'qemu.pid'), '-D', join(state, 'qemu.log'), '-daemonize'];
}

function qmp(execute, commandArgs = {}) {
  return new Promise((resolvePromise, reject) => {
    const connection = createConnection(socket);
    let buffer = '';
    const fail = error => { connection.destroy(); reject(error); };
    connection.setTimeout(5000, () => fail(new Error('QMP timeout')));
    connection.on('error', reject);
    connection.on('data', data => {
      buffer += data.toString();
      while (buffer.includes('\n')) {
        const end = buffer.indexOf('\n');
        const line = buffer.slice(0, end).trim();
        buffer = buffer.slice(end + 1);
        if (!line) continue;
        let result;
        try { result = JSON.parse(line); } catch (error) { fail(error); return; }
        if (result.QMP) connection.write(`${JSON.stringify({ execute: 'qmp_capabilities', id: 'cap' })}\n`);
        else if (result.id === 'cap') connection.write(`${JSON.stringify({ execute, arguments: commandArgs, id: 'command' })}\n`);
        else if (result.id === 'command') {
          connection.end();
          if (result.error) reject(new Error(JSON.stringify(result.error)));
          else resolvePromise(result.return);
        }
      }
    });
  });
}

try {
  switch (process.argv[2]) {
    case 'setup': run('python3', [join(root, 'emulator/tools/prepare-simulator.py')]); break;
    case 'doctor': {
      const version = run('qemu-system-i386', ['--version'], true).split('\n')[0];
      const armMachines = run('qemu-system-arm', ['-machine', 'help'], true);
      const runtimePath = join(state, 'runtime-report.json');
      const runtime = existsSync(runtimePath) ? JSON.parse(readFileSync(runtimePath)) : null;
      const compatibilityPath = join(root, 'emulator/evidence/runtime-report.json');
      const compatibility = existsSync(compatibilityPath) ? JSON.parse(readFileSync(compatibilityPath)) : null;
      const report = { checkedAt: new Date().toISOString(), qemu: version, kvmAccessible: hasKvm(),
        simulatorDiskPresent: existsSync(base), x86BarPresent: existsSync(join(root, 'build/hello-cascades-simulator/HelloCascades-simulator-unsigned.bar')),
        passportBoardInInstalledQemu: /passport|msm8974/i.test(armMachines),
        officialSimulatorArchitecture: 'x86', passportFirmwareBootTested: false,
        guiBootTested: runtime?.guiAttempted || false, guiDisplayed: runtime?.guiDisplayed ?? null,
        runtimeReport: runtime ? runtimePath : null,
        vmvgaGuiDisplayed: compatibility?.defaultProfileGuiDisplayed ?? null,
        vmvgaRuntimeReport: compatibility ? compatibilityPath : null };
      writeFileSync(join(state, 'host-check.json'), `${JSON.stringify(report, null, 2)}\n`);
      writeFileSync(join(state, 'qemu-arm-machines.txt'), armMachines);
      console.log(JSON.stringify(report, null, 2));
      break;
    }
    case 'start':
      if (process.argv.includes('--dry-run')) { console.log(JSON.stringify(['qemu-system-i386', ...args()], null, 2)); break; }
      if (!existsSync(base)) throw new Error('Simulator disk missing: run npm run setup:simulator.');
      if (existsSync(socket)) throw new Error('QMP socket already exists; check simulator status before starting another instance.');
      if (!existsSync(disk)) run('qemu-img', ['create', '-f', 'qcow2', '-F', 'vmdk', '-b', base, disk]);
      writeFileSync(join(state, 'launch-command.json'), `${JSON.stringify(args(), null, 2)}\n`);
      run('qemu-system-i386', args());
      console.log('QEMU process started. VNC: 127.0.0.1:5910. Guest GUI boot has not been verified.');
      break;
    case 'status': console.log(await qmp('query-status')); break;
    case 'display':
      console.log(JSON.stringify({ display: await qmp('query-display-options'), vnc: await qmp('query-vnc'), kvm: await qmp('query-kvm') }, null, 2));
      break;
    case 'network': console.log(await qmp('human-monitor-command', { 'command-line': 'info usernet' })); break;
    case 'pci': console.log(JSON.stringify(await qmp('query-pci'), null, 2)); break;
    case 'forward-ssh':
      console.log(await qmp('human-monitor-command', { 'command-line': 'hostfwd_add net0 tcp:127.0.0.1:2223-:22' }));
      break;
    case 'trace-net':
      console.log(await qmp('trace-event-get-state', { name: 'pcnet*' }));
      await qmp('trace-event-set-state', { name: 'pcnet*', enable: true, 'ignore-unavailable': true });
      break;
    case 'netdump':
      await qmp('object-add', { 'qom-type': 'filter-dump', id: 'bb10-netdump', netdev: 'net0', file: join(state, 'network.pcap') });
      console.log(join(state, 'network.pcap'));
      break;
    case 'pointer': {
      const [x, y] = process.argv.slice(3, 5).map(Number);
      if (![x, y].every(v => Number.isInteger(v) && v >= 0 && v <= 32767)) throw new Error('Use absolute pointer x/y in 0..32767.');
      const events = ['x', 'y'].map((axis, i) => ({ type: 'abs', data: { axis, value: i ? y : x } }));
      if (['down', 'up'].includes(process.argv[5])) events.push({ type: 'btn', data: { button: 'left', down: process.argv[5] === 'down' } });
      await qmp('input-send-event', { events });
      break;
    }
    case 'reset': await qmp('system_reset'); console.log('QEMU guest reset.'); break;
    case 'pause': await qmp('stop'); break;
    case 'resume': await qmp('cont'); break;
    case 'menu':
      if (!process.argv.includes('--no-reset')) await qmp('system_reset');
      await qmp('cont');
      {
        // OCR is optional and only used by this diagnostic command. Poll the
        // actual prompt instead of assuming the same boot timing for KVM/TCG.
        const until = Date.now() + 90000;
        let opened = false;
        while (Date.now() < until) {
          await new Promise(resolvePromise => setTimeout(resolvePromise, 500));
          await qmp('screendump', { filename: join(state, 'screen.ppm') });
          const text = run('tesseract', [join(state, 'screen.ppm'), 'stdout', '--psm', '6'], true);
          if (!/Press.*Enter.*select which device|Starting BlackBerry.*in 5 seconds/i.test(text)) continue;
          await qmp('human-monitor-command', { 'command-line': 'sendkey ret' });
          await new Promise(resolvePromise => setTimeout(resolvePromise, 500));
          await qmp('stop');
          await qmp('screendump', { filename: join(state, 'screen.ppm') });
          opened = true;
          break;
        }
        if (!opened) throw new Error('Boot menu prompt not observed within 90 seconds.');
        console.log('Guest paused after opening boot menu. Use resume, then key <name>.');
      }
      break;
    case 'stop': await qmp('quit'); console.log('QEMU instance stopped.'); break;
    case 'screenshot': {
      const path = join(state, 'screen.ppm');
      await qmp('screendump', { filename: path });
      console.log(path);
      break;
    }
    case 'key':
      if (!/^[a-z0-9_-]+$/.test(process.argv[3] || '')) throw new Error('Specify a QEMU key name, e.g. ret, 1, 2, f1.');
      await qmp('human-monitor-command', { 'command-line': `sendkey ${process.argv[3]}` });
      break;
    default: throw new Error('Usage: node tools/simulator.mjs setup|doctor|start [--tcg|--dry-run]|status|stop|screenshot|menu|pause|resume|reset|key <name>|pointer <x> <y> [down|up]|network|pci|netdump|trace-net|forward-ssh [--state emulator/state/...]');
  }
} catch (error) {
  console.error(`BB10 simulator: ${error.message}`);
  process.exitCode = 1;
}
