# Generate commits for all of 2025
$startDate = Get-Date "2025-01-01"
$endDate = Get-Date "2025-12-31"
$fileName = "project_data.txt"

$commitMessages = @(
    "Update documentation and add examples",
    "Fix edge case in main logic",
    "Optimize performance for large datasets",
    "Implement error handling",
    "Add unit tests for core functions",
    "Refactor code for better maintainability",
    "Update dependencies to latest versions",
    "Fix typos in documentation",
    "Add logging functionality",
    "Improve error messages",
    "Implement feature request",
    "Fix bug report",
    "Clean up deprecated code",
    "Enhance security measures",
    "Add input validation"
)

Write-Host "Generating commits for all of 2025..." -ForegroundColor Cyan

$currentDate = $startDate
$commitCount = 0

while ($currentDate -le $endDate) {
    if ((Get-Random -Minimum 0 -Maximum 10) -lt 7) {
        $numCommits = Get-Random -Minimum 1 -Maximum 11
        
        Write-Host "Day $($currentDate.ToString('yyyy-MM-dd')): Creating $numCommits commits" -ForegroundColor Yellow
        
        for ($i = 1; $i -le $numCommits; $i++) {
            "Update $(Get-Date -Format 'yyyyMMddHHmmss')-$i" | Out-File -FilePath $fileName -Append -Encoding UTF8
            
            git add $fileName 2>&1 | Out-Null
            
            $randomMsg = $commitMessages[(Get-Random -Minimum 0 -Maximum $commitMessages.Count)]
            $commitMsg = "$randomMsg $((Get-Random -Minimum 1 -Maximum 1000))"
            
            $commitDateTime = $currentDate.ToString("yyyy-MM-ddTHH:mm:ss")
            $env:GIT_AUTHOR_DATE = $commitDateTime
            $env:GIT_COMMITTER_DATE = $commitDateTime
            
            git commit -m $commitMsg 2>&1 | Out-Null
            
            Write-Host "  Done: $commitMsg" -ForegroundColor Green
            $commitCount++
        }
    } else {
        Write-Host "Day $($currentDate.ToString('yyyy-MM-dd')): Skipping" -ForegroundColor Gray
    }
    
    $currentDate = $currentDate.AddDays(1)
}

Write-Host "`nTotal commits created: $commitCount" -ForegroundColor Cyan
Write-Host "Pushing to origin..." -ForegroundColor Cyan

git push origin main

Write-Host "Complete! Check https://github.com/niyeldeii/commix" -ForegroundColor Green
