# Convert ChatGPT conversations.json to CSV
# Usage: .\convert_to_csv.ps1

$jsonFile = "conversations.json"
$csvFile = "conversations.csv"

Write-Host "Reading $jsonFile..."

# Read JSON in chunks to handle large files
$json = Get-Content $jsonFile -Raw | ConvertFrom-Json

# Check if it's an array or object
if ($json -is [Array]) {
    Write-Host "Found array with $($json.Count) conversations"
    $conversations = $json
} elseif ($json.conversations) {
    Write-Host "Found conversations property"
    $conversations = $json.conversations
} else {
    Write-Host "Unknown structure. First level keys:"
    $json | Get-Member -MemberType NoteProperty | Select-Object -First 10 Name
    exit
}

# Extract conversation data
$rows = @()
$processed = 0

foreach ($conv in $conversations) {
    $processed++
    if ($processed % 10 -eq 0) {
        Write-Host "Processing conversation $processed / $($conversations.Count)..."
    }
    
    $conversationId = $conv.id
    $title = $conv.title
    $createTime = if ($conv.create_time) { [DateTimeOffset]::FromUnixTimeSeconds($conv.create_time).ToString("yyyy-MM-dd HH:mm:ss") } else { "" }
    $updateTime = if ($conv.update_time) { [DateTimeOffset]::FromUnixTimeSeconds($conv.update_time).ToString("yyyy-MM-dd HH:mm:ss") } else { "" }
    
    # Extract messages from mapping
    if ($conv.mapping) {
        # ChatGPT format with mapping (tree structure)
        $messageNodes = $conv.mapping.PSObject.Properties | ForEach-Object { $_.Value }
        
        foreach ($node in $messageNodes) {
            if ($node.message -and $node.message.id) {
                $msg = $node.message
                $msgId = $msg.id
                $role = if ($msg.author) { $msg.author.role } else { "" }
                $authorName = if ($msg.author) { $msg.author.name } else { "" }
                $msgCreateTime = if ($msg.create_time) { [DateTimeOffset]::FromUnixTimeSeconds($msg.create_time).ToString("yyyy-MM-dd HH:mm:ss") } else { "" }
                $msgUpdateTime = if ($msg.update_time) { [DateTimeOffset]::FromUnixTimeSeconds($msg.update_time).ToString("yyyy-MM-dd HH:mm:ss") } else { "" }
                
                # Extract content from parts
                $content = ""
                if ($msg.content -and $msg.content.parts) {
                    $contentParts = @()
                    foreach ($part in $msg.content.parts) {
                        if ($part.text) {
                            $contentParts += $part.text
                        } elseif ($part -is [string]) {
                            $contentParts += $part
                        }
                    }
                    $content = $contentParts -join " "
                } elseif ($msg.content -is [string]) {
                    $content = $msg.content
                }
                
                # Clean content (remove newlines, escape quotes)
                $content = $content -replace "`r`n", " " -replace "`n", " " -replace '"', '""'
                
                $rows += [PSCustomObject]@{
                    conversation_id = $conversationId
                    conversation_title = $title
                    message_id = $msgId
                    role = $role
                    author_name = $authorName
                    create_time = $msgCreateTime
                    update_time = $msgUpdateTime
                    content = $content
                }
            }
        }
    } elseif ($conv.messages) {
        # Direct messages array
        foreach ($msg in $conv.messages) {
            $content = if ($msg.content) { ($msg.content -replace "`r`n", " " -replace "`n", " " -replace '"', '""') } else { "" }
            $rows += [PSCustomObject]@{
                conversation_id = $conversationId
                conversation_title = $title
                message_id = if ($msg.id) { $msg.id } else { "" }
                role = if ($msg.role) { $msg.role } else { "" }
                author_name = if ($msg.author_name) { $msg.author_name } else { "" }
                create_time = if ($msg.create_time) { $msg.create_time } else { "" }
                update_time = if ($msg.update_time) { $msg.update_time } else { "" }
                content = $content
            }
        }
    }
}

Write-Host "`nExporting $($rows.Count) rows to $csvFile..."

# Export to CSV
$rows | Export-Csv -Path $csvFile -NoTypeInformation -Encoding UTF8

Write-Host "Done! Created $csvFile with $($rows.Count) rows."
Write-Host "File location: $(Resolve-Path $csvFile)"

