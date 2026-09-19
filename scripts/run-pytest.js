const { spawn } = require('child_process');
const fs = require('fs');
const path = require('path');

const rootDir = path.resolve(__dirname, '..');
const backendDir = path.join(rootDir, 'backend');

let pythonCmd = 'python';
const winVenvPython = path.join(backendDir, '.venv', 'Scripts', 'python.exe');
const unixVenvPython = path.join(backendDir, '.venv', 'bin', 'python');

if (process.platform === 'win32' && fs.existsSync(winVenvPython)) {
  pythonCmd = winVenvPython;
} else if (fs.existsSync(unixVenvPython)) {
  pythonCmd = unixVenvPython;
}

const args = ['-m', 'pytest', ...process.argv.slice(2)];

const proc = spawn(pythonCmd, args, {
  cwd: backendDir,
  stdio: 'inherit'
});

proc.on('exit', (code) => {
  process.exit(code || 0);
});
