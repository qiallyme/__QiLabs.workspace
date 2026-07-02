# install_housekeeping_guardrails.ps1
# QiLabs Housekeeping Guardrails v0.3
# Safe interactive installer. Backs up existing config, creates missing authority files,
# quarantines the rejected over-broad dry-run plan, and installs a conservative config.

$ErrorActionPreference = "Stop"

$ToolboxRoot = "C:\QiLabs\00_QiLabs.workspace\toolbox"
$HousekeepingRoot = Join-Path $ToolboxRoot "_housekeeping"
$ConfigPath = Join-Path $HousekeepingRoot "housekeeping_config.json"
$PatchConfig = Join-Path $ToolboxRoot "housekeeping_config.guarded.json"
$QiConfigRoot = "C:\QiLabs\_qiconfig"
$MasterTemplatePath = Join-Path $QiConfigRoot "master_template.md"
$TagsPath = Join-Path $QiConfigRoot "tags.json"
$ArchiveRoot = Join-Path $ToolboxRoot ("_archive\housekeeping-guardrails-" + (Get-Date -Format "yyyyMMdd-HHmmss"))
$RejectedRunId = "20260702-000419"

function Ask-YesNo {
    param(
        [string]$Question,
        [bool]$DefaultYes = $true
    )
    $suffix = if ($DefaultYes) { "[Y/n]" } else { "[y/N]" }
    while ($true) {
        $answer = Read-Host "$Question $suffix"
        if ([string]::IsNullOrWhiteSpace($answer)) { return $DefaultYes }
        switch ($answer.Trim().ToLowerInvariant()) {
            "y" { return $true }
            "yes" { return $true }
            "n" { return $false }
            "no" { return $false }
            default { Write-Host "Please answer y or n." }
        }
    }
}

function Backup-FileIfExists {
    param([string]$Path)
    if (Test-Path $Path -PathType Leaf) {
        $rel = $Path.Replace($ToolboxRoot, "").TrimStart("\")
        if ($Path.StartsWith($QiConfigRoot)) {
            $rel = "_qiconfig\" + (Split-Path $Path -Leaf)
        }
        $dest = Join-Path $ArchiveRoot $rel
        New-Item -ItemType Directory -Force (Split-Path $dest -Parent) | Out-Null
        Copy-Item $Path $dest -Force
        Write-Host "Backed up: $Path"
    }
}

function Move-IfExists {
    param([string]$Path, [string]$DestinationFolder)
    if (Test-Path $Path) {
        New-Item -ItemType Directory -Force $DestinationFolder | Out-Null
        $dest = Join-Path $DestinationFolder (Split-Path $Path -Leaf)
        if (Test-Path $dest) {
            $dest = Join-Path $DestinationFolder ((Split-Path $Path -Leaf) + ".moved-" + (Get-Date -Format "HHmmss"))
        }
        Move-Item $Path $dest -Force
        Write-Host "Quarantined: $Path"
    }
}

Write-Host "============================================================"
Write-Host "QiLabs Housekeeping Guardrails v0.3"
Write-Host "============================================================"
Write-Host "Toolbox root:      $ToolboxRoot"
Write-Host "Housekeeping root: $HousekeepingRoot"
Write-Host "Qi config root:    $QiConfigRoot"
Write-Host "Archive root:      $ArchiveRoot"
Write-Host ""

if (-not (Test-Path $ToolboxRoot)) {
    throw "Toolbox root not found: $ToolboxRoot"
}
if (-not (Test-Path $HousekeepingRoot)) {
    throw "Housekeeping root not found: $HousekeepingRoot"
}
if (-not (Test-Path $PatchConfig)) {
    throw "Patch config not found. Unzip package into toolbox root: $PatchConfig"
}

$install = Ask-YesNo "Install conservative housekeeping guardrails now?" $true
if (-not $install) {
    Write-Host "Cancelled. Nothing changed."
    exit 0
}

New-Item -ItemType Directory -Force $ArchiveRoot | Out-Null
New-Item -ItemType Directory -Force $QiConfigRoot | Out-Null

Write-Host ""
Write-Host "[1/5] Backing up current authority/config files..."
Backup-FileIfExists $ConfigPath
Backup-FileIfExists $MasterTemplatePath
Backup-FileIfExists $TagsPath

Write-Host ""
Write-Host "[2/5] Installing guarded housekeeping_config.json..."
Copy-Item $PatchConfig $ConfigPath -Force
Write-Host "Installed: $ConfigPath"

Write-Host ""
Write-Host "[3/5] Creating missing master template and tag registry if needed..."
if (-not (Test-Path $MasterTemplatePath)) {
@'
---
layout: page
title: "{{title}}"
slug: ""
summary: ""
status: active
created_at: "{{date}} {{time}}"
updated_at: "{{date}} {{time}}"
author: ""
owner: ""
tags: []
keywords: []
aliases: []
context: ""
sensitivity: internal
classification: business_internal
realm_label: ""

uid: ""
canonical_ref: ""
source_type: manual
template_key: master-template
---

# {{title}}

## Overview

## Key Information

## Notes / Actions
'@ | Set-Content -Path $MasterTemplatePath -Encoding UTF8
    Write-Host "Created: $MasterTemplatePath"
} else {
    Write-Host "Exists, not overwritten: $MasterTemplatePath"
}

if (-not (Test-Path $TagsPath)) {
@'
{
  "schema_version": "1.0",
  "profile_name": "qilabs_global_tag_registry",
  "allowed_tags": {
    "system": [
      "#qilabs",
      "#qispark",
      "#qiserver",
      "#qidrive",
      "#qiapps",
      "#housekeeping",
      "#template",
      "#index",
      "#ops",
      "#reference"
    ],
    "status": [
      "#active",
      "#draft",
      "#review",
      "#archive",
      "#deprecated"
    ],
    "content": [
      "#note",
      "#record",
      "#project",
      "#person",
      "#timeline",
      "#evidence",
      "#finance",
      "#health",
      "#caregiving",
      "#transport"
    ],
    "safety": [
      "#internal",
      "#private",
      "#restricted",
      "#public"
    ]
  },
  "tag_policy": {
    "always_include": [],
    "notes": "This starter registry exists so housekeeping validation has an authority file. Expand deliberately; do not auto-add every project-specific tag globally."
  }
}
'@ | Set-Content -Path $TagsPath -Encoding UTF8
    Write-Host "Created: $TagsPath"
} else {
    Write-Host "Exists, not overwritten: $TagsPath"
}

Write-Host ""
Write-Host "[4/5] Quarantining rejected over-broad dry-run plan if present..."
$reject = Ask-YesNo "Move run $RejectedRunId plans/reports/summaries/logs to rejected archive so it cannot be applied accidentally?" $true
if ($reject) {
    $RejectedRoot = Join-Path $ArchiveRoot "rejected-housekeeping-plan-$RejectedRunId"
    New-Item -ItemType Directory -Force $RejectedRoot | Out-Null

    $pathsToMove = @(
        (Join-Path $HousekeepingRoot "plans\housekeeping-plan-$RejectedRunId.json"),
        (Join-Path $HousekeepingRoot "plans\$RejectedRunId"),
        (Join-Path $HousekeepingRoot "reports\housekeeping-report-$RejectedRunId.md"),
        (Join-Path $HousekeepingRoot "reports\rename-plan-$RejectedRunId.json"),
        (Join-Path $HousekeepingRoot "reports\inventory-$RejectedRunId.json"),
        (Join-Path $HousekeepingRoot "summaries\housekeeping-summary-$RejectedRunId.md"),
        (Join-Path $HousekeepingRoot "logs\housekeeping-$RejectedRunId.jsonl")
    )

    foreach ($p in $pathsToMove) {
        Move-IfExists $p $RejectedRoot
    }

@"
# Rejected housekeeping plan

Run ID: $RejectedRunId
Rejected at: $(Get-Date)

Reason:
- Planned thousands of actions.
- Included filename renames.
- Master template and tags registry were missing at preview time.
- Git discovery was too broad.

Do not apply this plan. Keep only for audit/history.
"@ | Set-Content -Path (Join-Path $RejectedRoot "REJECTED_DO_NOT_APPLY.md") -Encoding UTF8
} else {
    Write-Host "Skipped rejected-plan quarantine. Be careful not to apply run $RejectedRunId."
}

Write-Host ""
Write-Host "[5/5] Final guidance"
Write-Host "Guardrails installed. Next safe run inside Housekeeping Console:"
Write-Host "  1. Renames unchecked"
Write-Host "  2. Push unchecked"
Write-Host "  3. Manual steps only: Preflight, Validate tags, Validate master template, Scan inventory"
Write-Host "  4. Do not approve/apply full run until that preview is clean"
Write-Host ""
Write-Host "Done."
Write-Host "============================================================"
