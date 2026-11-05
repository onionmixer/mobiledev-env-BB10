#!/usr/bin/env node
import { spawnSync } from 'node:child_process';
import { availableParallelism } from 'node:os';
import { existsSync, mkdirSync, readFileSync, writeFileSync, cpSync, statSync } from 'node:fs';
import { dirname, resolve, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { createHash } from 'node:crypto';

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const lock = JSON.parse(readFileSync(join(root, 'config/sdk.lock.json')));
const isSimulator = process.argv.includes('--simulator');
const architecture = isSimulator ? 'x86' : 'armle-v7';
const configuration = isSimulator ? 'Simulator-Debug' : 'Device-Debug';
const source = join(root, 'examples/hello-cascades');
const output = join(root, isSimulator ? 'build/hello-cascades-simulator' : 'build/hello-cascades');
const binary = join(output, 'HelloCascades');
const bar = join(output, isSimulator ? 'HelloCascades-simulator-unsigned.bar' : 'HelloCascades-unsigned.bar');
const sdkRunner = join(root, 'tools/sdk-run.sh');
const backend = process.env.BB10_BACKEND || 'container';

function run(command, args, options = {}) {
  const { capture = false, allowFailure = false, ...rest } = options;
  const result = spawnSync(command, args, {
    cwd: root, encoding: 'utf8', stdio: capture ? 'pipe' : 'inherit', ...rest,
  });
  if (result.error || result.status !== 0) {
    if (allowFailure) return result;
    throw new Error(`${command} failed (${result.error?.message || result.signal || result.status})${capture ? `\n${result.stderr || result.stdout}` : ''}`);
  }
  return result;
}

function sdk(args, options = {}) {
  return run('bash', [sdkRunner, ...args], {
    ...options, env: { ...process.env, BB10_CPUVARDIR: architecture },
  });
}
function ensureOutput() { mkdirSync(output, { recursive: true }); }

function container(task, args = []) {
  ensureOutput();
  return run('docker', [
    'run', '--rm', '--platform=linux/amd64', '--network=none', '--read-only',
    '--cap-drop=ALL', '--security-opt=no-new-privileges',
    '--user', `${process.getuid()}:${process.getgid()}`,
    '--env', `BB10_BUILD_TARGET=${isSimulator ? 'simulator' : 'device'}`,
    '--tmpfs', '/tmp:rw,exec,size=512m,mode=1777',
    '--mount', `type=bind,src=${source},dst=/input,readonly`,
    '--mount', `type=bind,src=${join(root, 'tools')},dst=/tools,readonly`,
    '--mount', `type=bind,src=${output},dst=/output`,
    '--entrypoint', '/bin/bash', lock.image,
    '/tools/container-task.sh', task, ...args,
  ]);
}

function setupSdk() {
  const inspected = run('docker', ['image', 'inspect', lock.image], { capture: true, allowFailure: true });
  if (inspected.status !== 0) run('docker', ['pull', '--platform=linux/amd64', lock.image]);
  if (!process.argv.includes('--extract')) {
    console.log('Pinned SDK image ready. No IDE is started. Run npm run doctor.');
    return;
  }
  const destination = join(root, 'sdk/bbndk');
  const marker = join(destination, '.bb10-sdk.json');
  if (existsSync(marker)) {
    const installed = JSON.parse(readFileSync(marker));
    if (installed.image !== lock.image) throw new Error('Installed SDK digest differs from config/sdk.lock.json. Choose a new SDK directory explicitly.');
    console.log('SDK already extracted. Run npm run doctor to check it.');
    return;
  }
  mkdirSync(destination, { recursive: true });
  // Explicit command, no image services, no network, no root, only SDK destination writable.
  // Copy only the compiler/sysroot and Cascades host support; exclude the IDE and JRE.
  run('docker', [
    'run', '--rm', '--platform=linux/amd64', '--network=none', '--read-only',
    '--cap-drop=ALL', '--security-opt=no-new-privileges',
    '--user', `${process.getuid()}:${process.getgid()}`,
    '--mount', `type=bind,src=${destination},dst=/export`,
    '--entrypoint', '/bin/bash', lock.image, '-c',
    'set -e; cd "$1"; cp -a --no-preserve=ownership host_10_3_1_12 target_10_3_1_995 /export/',
    'bb10-extract', lock.imageSdkRoot,
  ]);
  writeFileSync(marker, `${JSON.stringify({ ...lock, extractedAt: new Date().toISOString() }, null, 2)}\n`);
  console.log(`Extracted CLI SDK to ${destination}. Run npm run doctor.`);
}

function doctor() {
  console.log(`Host: ${process.platform}/${process.arch}, Node ${process.version}; SDK backend: ${backend}`);
  if (Number(process.versions.node.split('.')[0]) < 20) throw new Error('Host Node.js 20+ required.');
  if (process.platform !== 'linux' || process.arch !== 'x64') throw new Error('The extracted legacy SDK requires Linux x86-64.');
  if (backend === 'container') {
    container('doctor');
    console.log('Container CLI SDK ready. Device installation/signing status is a separate check.');
    return;
  }
  if (statSync(root, { bigint: true }).ino > 0xffffffffn) {
    throw new Error('Host directory inode exceeds 32 bits. Use the default container backend with tmpfs staging.');
  }
  const targets = sdk(['qcc', '-V'], { capture: true });
  if (!`${targets.stdout}${targets.stderr}`.includes('gcc_ntoarmv7le')) throw new Error('qcc ARM target not found.');
  console.log(`${targets.stdout}${targets.stderr}`);
  sdk(['qmake', '-v']);
  sdk(['java', '-version']);
  sdk(['blackberry-nativepackager', '-version']);
  console.log('CLI SDK ready. Device installation/signing status is a separate check.');
}

function build() {
  ensureOutput();
  const jobs = process.env.BB10_JOBS || Math.min(availableParallelism(), 8).toString();
  if (!/^[1-9][0-9]*$/.test(jobs)) throw new Error('BB10_JOBS must be a positive integer.');
  if (backend === 'container') {
    container('build', [jobs]);
    verifyElf(binary);
    return;
  }
  if (statSync(root, { bigint: true }).ino > 0xffffffffn) {
    throw new Error('Host inode exceeds 32 bits. Use BB10_BACKEND=container.');
  }
  sdk(['qmake', '-spec', isSimulator ? 'blackberry-x86-qcc' : 'blackberry-armv7le-qcc',
    join(source, 'HelloCascades.pro'), `CONFIG+=${isSimulator ? 'simulator' : 'device'}`, 'CONFIG+=debug',
    'CONFIG-=release', '-o', join(output, 'Makefile')], { cwd: output });
  sdk(['make', '-j', jobs], { cwd: output });
  cpSync(join(output, isSimulator ? 'o-g/HelloCascades' : 'o.le-v7-g/HelloCascades'), binary);
  verifyElf(binary);
}

function verifyElf(path) {
  const data = readFileSync(path);
  if (data.length < 52 || data.subarray(0, 4).toString('hex') !== '7f454c46' ||
      data[4] !== 1 || data[5] !== 1 || data.readUInt16LE(18) !== (isSimulator ? 3 : 40)) {
    throw new Error(`${path} is not an ELF32 little-endian ${architecture} executable.`);
  }
  const phoff = data.readUInt32LE(28);
  const phsize = data.readUInt16LE(42);
  const phcount = data.readUInt16LE(44);
  let interpreter;
  for (let i = 0; i < phcount; ++i) {
    const at = phoff + i * phsize;
    if (at + 32 > data.length) throw new Error('ELF program headers are truncated.');
    if (data.readUInt32LE(at) !== 3) continue; // PT_INTERP
    const start = data.readUInt32LE(at + 4);
    const length = data.readUInt32LE(at + 16);
    interpreter = data.subarray(start, start + length).toString().replace(/\0+$/, '');
  }
  if (interpreter !== '/usr/lib/ldqnx.so.2') throw new Error(`Unexpected ELF loader: ${interpreter}`);
  console.log(`ELF verified: ${architecture}, 32-bit, little-endian (${data.length} bytes)`);
}

function packageApp() {
  build();
  if (backend === 'container') {
    container('package');
    verify();
    console.log(`Unsigned development BAR: ${bar}`);
    return;
  }
  cpSync(join(source, 'assets'), join(output, 'assets'), { recursive: true });
  cpSync(join(source, 'bar-descriptor.xml'), join(output, 'bar-descriptor.xml'));
  sdk(['blackberry-nativepackager', '-package', bar, '-devMode',
    '-platformVersion', '10.3.1.0',
    '-configuration', configuration, join(output, 'bar-descriptor.xml')], { cwd: output });
  verify();
  console.log(`Unsigned development BAR: ${bar}`);
}

function verify() {
  verifyElf(binary);
  run('unzip', ['-t', bar]);
  const manifest = run('unzip', ['-p', bar, 'META-INF/MANIFEST.MF'], { capture: true }).stdout;
  const files = run('unzip', ['-Z1', bar], { capture: true }).stdout.split(/\r?\n/);
  for (const file of ['native/HelloCascades', 'native/assets/main.qml']) {
    if (!files.includes(file)) throw new Error(`BAR missing ${file}`);
  }
  if (!manifest.includes('Entry-Point:') || !manifest.includes('com.example.bb10.hellocascades')) {
    throw new Error('BAR manifest missing application ID or entry point.');
  }
  for (const field of [`Package-Architecture: ${architecture}`,
    'Application-Requires-System: BlackBerry 10/10.3.1.0', 'Application-Development-Mode: true']) {
    if (!manifest.includes(field)) throw new Error(`BAR missing ${field}`);
  }
  const packaged = run('unzip', ['-p', bar, 'native/HelloCascades'], { encoding: null, capture: true }).stdout;
  if (!packaged.equals(readFileSync(binary))) throw new Error('Packaged executable differs from built executable.');
  const artifact = path => {
    const content = readFileSync(path);
    return { path, bytes: content.length, sha256: createHash('sha256').update(content).digest('hex') };
  };
  writeFileSync(join(output, 'verification.json'), `${JSON.stringify({
    verifiedAt: new Date().toISOString(), hostNode: process.version,
    sdk: lock, target: isSimulator ? 'simulator' : 'device', architecture,
    executable: artifact(binary), bar: artifact(bar),
    checks: [`${architecture} ELF32 little-endian`, 'QNX loader', 'ZIP integrity',
      'BAR entry point', `${architecture} package architecture`, 'minimum OS 10.3.1.0',
      'development mode', 'QML asset', 'packaged executable matches build'],
    deviceInstallTested: false, deviceRuntimeTested: false, simulatorRuntimeTested: false,
  }, null, 2)}\n`);
  console.log('BAR verified: ZIP integrity, manifest, executable, QML assets.');
}

function deploy() {
  // No build/pull/install happens implicitly. The user invokes this command to install.
  const barPath = resolve(process.argv.slice(3).find(arg => arg !== '--simulator') || bar);
  if (!existsSync(barPath)) throw new Error('BAR missing. Run npm run package first.');
  const deviceFile = join(root, 'config/device.json');
  const host = process.env.BB10_DEVICE_HOST ||
    (isSimulator ? '127.0.0.1:2443' :
      existsSync(deviceFile) ? JSON.parse(readFileSync(deviceFile)).host : undefined);
  if (!host || !/^[A-Za-z0-9.:_-]+$/.test(host)) throw new Error('Set BB10_DEVICE_HOST or config/device.json host.');
  const password = process.env.BB10_DEVICE_PASSWORD;
  if (!password && !isSimulator) throw new Error('Set BB10_DEVICE_PASSWORD in your shell (not in source files).');
  if (backend === 'container') {
    // Override the network flag only for an explicit deploy command. Forward
    // secrets by environment name, so they aren't embedded in docker argv.
    run('docker', [
      'run', '--rm', '--network=host', '--read-only', '--cap-drop=ALL',
      '--security-opt=no-new-privileges', '--user', `${process.getuid()}:${process.getgid()}`,
      '--tmpfs', '/tmp:rw,exec,size=64m,mode=1777',
      '--env', 'BB10_DEVICE_HOST', '--env', 'BB10_DEVICE_PASSWORD',
      '--env', `BB10_BUILD_TARGET=${isSimulator ? 'simulator' : 'device'}`,
      '--mount', `type=bind,src=${join(root, 'tools')},dst=/tools,readonly`,
      '--mount', `type=bind,src=${barPath},dst=/output/deploy.bar,readonly`,
      '--entrypoint', '/bin/bash', lock.image, '/tools/container-task.sh', 'deploy',
    ], { env: { ...process.env, BB10_DEVICE_HOST: host, BB10_DEVICE_PASSWORD: password || '' } });
  } else {
    sdk(['blackberry-deploy', '-installApp', ...(isSimulator ? ['-launchApp'] : []),
      '-device', host, ...(password ? ['-password', password] : []), barPath]);
  }
}

const actions = { 'setup-sdk': setupSdk, doctor, build, package: packageApp, verify, deploy };
const action = process.argv[2];
try {
  if (!['host', 'container'].includes(backend)) throw new Error('BB10_BACKEND must be host or container.');
  if (!actions[action]) throw new Error(`Usage: node tools/bb10.mjs <${Object.keys(actions).join('|')}>`);
  actions[action]();
} catch (error) {
  console.error(`BB10: ${error.message}`);
  process.exitCode = 1;
}
