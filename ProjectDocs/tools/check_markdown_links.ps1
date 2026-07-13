param(
    [string]$Root = (Join-Path $PSScriptRoot "..")
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$rootPath = (Resolve-Path -LiteralPath $Root).Path
$pathFailures = [System.Collections.Generic.List[object]]::new()
$anchorFailures = [System.Collections.Generic.List[object]]::new()
$anchorCache = @{}
$totalLocalLinks = 0

function Get-GfmAnchors {
    param([string]$Path)

    if ($anchorCache.ContainsKey($Path)) {
        return $anchorCache[$Path]
    }

    $seen = @{}
    $anchors = [System.Collections.Generic.List[string]]::new()

    foreach ($line in Get-Content -LiteralPath $Path -Encoding utf8) {
        if ($line -notmatch "^#{1,6}[\x20\t]+(.+?)[\x20\t]*#*[\x20\t]*$") {
            continue
        }

        $slug = $Matches[1].Trim().ToLowerInvariant()
        $slug = [regex]::Replace($slug, "<[^>]+>", "")
        $slug = [regex]::Replace($slug, "[^\p{L}\p{Nd}\s_-]", "")
        $slug = $slug.Replace(" ", "-").Replace([char]9, "-")

        if ($seen.ContainsKey($slug)) {
            $seen[$slug]++
            $slug = "$slug-$($seen[$slug])"
        }
        else {
            $seen[$slug] = 0
        }

        $anchors.Add($slug)
    }

    $anchorCache[$Path] = $anchors.ToArray()
    return $anchorCache[$Path]
}

foreach ($source in Get-ChildItem -LiteralPath $rootPath -Recurse -File -Filter "*.md") {
    $content = Get-Content -LiteralPath $source.FullName -Encoding utf8 -Raw
    $content = [regex]::Replace(
        $content,
        "(?ms)^[\x20\t]*(?<fence>\x60{3,}|~{3,})[^\r\n]*\r?\n.*?^[\x20\t]*\k<fence>[\x20\t]*\r?$",
        ""
    )

    foreach ($match in [regex]::Matches($content, "(?<!!)\[[^\]]+\]\(([^)]+)\)")) {
        $target = $match.Groups[1].Value.Trim()

        if ($target -match "^(?i:https?://|mailto:|tel:)") {
            continue
        }

        $totalLocalLinks++
        $parts = $target -split "#", 2
        $pathPart = [uri]::UnescapeDataString($parts[0].Trim("<>"))

        if ([string]::IsNullOrWhiteSpace($pathPart)) {
            $resolved = $source.FullName
        }
        else {
            $resolved = [System.IO.Path]::GetFullPath(
                (Join-Path $source.DirectoryName $pathPart)
            )
        }

        $sourceRelative = $source.FullName.Substring($rootPath.Length).TrimStart(
            [char]92,
            [char]47
        )

        if (-not (Test-Path -LiteralPath $resolved -PathType Leaf)) {
            $pathFailures.Add([pscustomobject]@{
                Source = $sourceRelative
                Target = $target
            })
            continue
        }

        if ($parts.Count -ne 2 -or [string]::IsNullOrWhiteSpace($parts[1])) {
            continue
        }

        $wantedAnchor = [uri]::UnescapeDataString($parts[1]).ToLowerInvariant()
        $anchors = Get-GfmAnchors -Path $resolved

        if ($anchors -cnotcontains $wantedAnchor) {
            $anchorFailures.Add([pscustomobject]@{
                Source = $sourceRelative
                Target = $target
            })
        }
    }
}

foreach ($failure in $pathFailures) {
    Write-Output "BROKEN_PATH $($failure.Source) -> $($failure.Target)"
}

foreach ($failure in $anchorFailures) {
    Write-Output "BROKEN_ANCHOR $($failure.Source) -> $($failure.Target)"
}

Write-Output "Local links: $totalLocalLinks"
Write-Output "Broken paths: $($pathFailures.Count)"
Write-Output "Broken anchors: $($anchorFailures.Count)"

if ($pathFailures.Count -gt 0 -or $anchorFailures.Count -gt 0) {
    exit 1
}
