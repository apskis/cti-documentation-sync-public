<#
.SYNOPSIS
  Re-render the diagrams after editing a .mmd source.

.DESCRIPTION
  Needs the Mermaid CLI: npm install -g @mermaid-js/mermaid-cli
  The .mmd sources are the originals; the .png and .svg are generated.
#>
$ErrorActionPreference = "Stop"
$repo = Split-Path -Parent $PSScriptRoot
Set-Location (Join-Path $repo "docs\diagrams")

if (-not (Get-Command "mmdc" -ErrorAction SilentlyContinue)) {
    Write-Error "mmdc not found. Install: npm install -g @mermaid-js/mermaid-cli"
    exit 127
}

Get-ChildItem -Filter *.mmd | ForEach-Object {
    $name = $_.BaseName
    # Width by shape: the infrastructure diagram is wide, the routing one narrow.
    $width = switch -Wildcard ($name) {
        "*infrastructure"  { 1800 }
        "*bedrock-routing" { 1600 }
        default            { 1700 }
    }
    Write-Host "rendering $name"
    mmdc -i $_.Name -o "$name.png" -c mermaid-theme.json -b white -w $width
    mmdc -i $_.Name -o "$name.svg" -c mermaid-theme.json -b white
}

Write-Host "done. PNG for pasting, SVG for scaling into a deck."
