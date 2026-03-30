// Renames the Electron.app bundle and patches Info.plist so macOS shows
// "Artifact Miner" in the dock instead of "Electron" in dev mode.
import { execSync } from 'child_process'
import { existsSync, readFileSync, writeFileSync, renameSync } from 'fs'
import { join, dirname } from 'path'
import { fileURLToPath } from 'url'

if (process.platform !== 'darwin') process.exit(0)

const __dirname = dirname(fileURLToPath(import.meta.url))
const distDir = join(__dirname, '../node_modules/electron/dist')
const oldApp = join(distDir, 'Electron.app')
const newApp = join(distDir, 'Artifact Miner.app')
const pathTxt = join(__dirname, '../node_modules/electron/path.txt')

// Rename Electron.app → Artifact Miner.app if not already done
if (existsSync(oldApp)) {
  renameSync(oldApp, newApp)
  console.log('Renamed Electron.app → Artifact Miner.app')
} else if (!existsSync(newApp)) {
  console.error('Could not find Electron.app or Artifact Miner.app in', distDir)
  process.exit(1)
}

// Update electron/path.txt so vite-plugin-electron finds the binary
const currentPath = readFileSync(pathTxt, 'utf8').trim()
const newPath = currentPath.replace('Electron.app', 'Artifact Miner.app')
writeFileSync(pathTxt, newPath)
console.log('Updated electron/path.txt')

// Patch Info.plist
const pb = '/usr/libexec/PlistBuddy'
const plistPath = join(newApp, 'Contents/Info.plist')
execSync(`${pb} -c "Set :CFBundleName 'Artifact Miner'" "${plistPath}"`)
execSync(`${pb} -c "Set :CFBundleDisplayName 'Artifact Miner'" "${plistPath}"`)
console.log('Patched Info.plist → Artifact Miner')
