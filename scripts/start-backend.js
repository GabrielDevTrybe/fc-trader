const { spawn } = require('child_process');
const fs = require('fs');
const path = require('path');

const rootDir = path.resolve(__dirname, '..');
const backendDir = path.join(rootDir, 'backend');

// Find the appropriate python executable
let pythonCmd = 'python';

const winVenvPython = path.join(backendDir, '.venv', 'Scripts', 'python.exe');
const unixVenvPython = path.join(backendDir, '.venv', 'bin', 'python');

if (process.platform === 'win32' && fs.existsSync(winVenvPython)) {
  pythonCmd = winVenvPython;
} else if (fs.existsSync(unixVenvPython)) {
  pythonCmd = unixVenvPython;
}

console.log(`[FC Trader] Starting Backend with Python: ${pythonCmd}`);

const uvicornArgs = [
  '-m',
  'uvicorn',
  'app.main:app',
  '--reload',
  '--port',
  '8000',
  '--host',
  '127.0.0.1'
];

const proc = spawn(pythonCmd, uvicornArgs, {
  cwd: backendDir,
  stdio: 'inherit'
});

proc.on('exit', (code) => {
  process.exit(code || 0);
});

// Handle termination signals
['SIGINT', 'SIGTERM'].forEach((sig) => {
  process.on(sig, () => {
    if (!proc.killed) {
      proc.kill(sig);
    }
  });
});
