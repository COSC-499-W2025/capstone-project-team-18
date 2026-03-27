// Patches the Electron binary's Info.plist so the macOS menu bar shows
// "Artifact Miner" instead of "Electron" when running in dev mode.
import { readFileSync, writeFileSync } from 'fs'
import { join, dirname } from 'path'
import { fileURLToPath } from 'url'

const __dirname = dirname(fileURLToPath(import.meta.url))
const plistPath = join(
  __dirname,
  '../node_modules/electron/dist/Electron.app/Contents/Info.plist'
)

try {
  let content = readFileSync(plistPath, 'utf8')
  const updated = content
    .replace(
      /<key>CFBundleName<\/key>\s*<string>[^<]*<\/string>/,
      '<key>CFBundleName</key>\n\t<string>Artifact Miner</string>'
    )
    .replace(
      /<key>CFBundleDisplayName<\/key>\s*<string>[^<]*<\/string>/,
      '<key>CFBundleDisplayName</key>\n\t<string>Artifact Miner</string>'
    )
  if (updated !== content) {
    writeFileSync(plistPath, updated)
    console.log('Patched Electron.app name → Artifact Miner')
  }
} catch {
  // Not on macOS, or Electron not yet installed — skip silently
}
