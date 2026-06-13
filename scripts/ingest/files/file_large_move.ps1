# Script to move large files to quarantine for Google Drive upload
# This will preserve the files while keeping git repository lean

Write-Host "🧹 Moving large files to quarantine..." -ForegroundColor Yellow

# Create quarantine subdirectories
$quarantinePath = "C:\Users\codyr\Documents\QiOne\QUARANTINE_LARGE_FILES"
New-Item -ItemType Directory -Path "$quarantinePath\ZaitullahJan_Legal_Docs" -Force
New-Item -ItemType Directory -Path "$quarantinePath\EmpowerQNow713_Assets" -Force
New-Item -ItemType Directory -Path "$quarantinePath\Other_Large_Files" -Force

# Move ZaitullahJan legal documents
$zaitullahFiles = @(
    "4_Clients\ZaitullahJan-OS\50_Legal\60_Immigration\50_Form_Filings\10_I-589 (Asylum)\11_FINAL-AUDIT\zjk_09122025_Main_Filing_v01.pdf",
    "4_Clients\ZaitullahJan-OS\50_Legal\60_Immigration\50_Form_Filings\10_I-589 (Asylum)\12-Cover\zjk_From_Checklist_to_Compelling_Crafting_a_Winning_Asylum_Applica_v01.m4a",
    "4_Clients\ZaitullahJan-OS\50_Legal\60_Immigration\50_Form_Filings\10_I-589 (Asylum)\C.04-Exhibits\EX-B_Persecution-Threats-Conditions\zjk_09122025_C.00.00_Articles_v01.pdf",
    "4_Clients\ZaitullahJan-OS\50_Legal\60_Immigration\50_Form_Filings\10_I-589 (Asylum)\C.04-Exhibits\EX-C_Government-Actions-Notices\zjk_EXC115_Uscischicago_v01.pdf",
    "4_Clients\ZaitullahJan-OS\50_Legal\60_Immigration\50_Form_Filings\10_I-589 (Asylum)\C.04-Exhibits\EX-E_Community-Residence-Integration\zjk_EXE212_From_Afghan_Frontlines_To_Asylum_v01.m4a",
    "4_Clients\ZaitullahJan-OS\50_Legal\60_Immigration\50_Form_Filings\10_I-589 (Asylum)\PDF PAGES\zjk_09122025_C.00.00_Extract_v01.pdf",
    "4_Clients\ZaitullahJan-OS\50_Legal\60_Immigration\50_Form_Filings\10_I-589 (Asylum)\PDF PAGES\zjk_09122025_C.00.00_Main_Filing_v01.pdf",
    "4_Clients\ZaitullahJan-OS\50_Legal\60_Immigration\50_Form_Filings\20_I-360 (Special Immigrant)\D.I360.Packet\zjk_D.I360packet_v01.pdf"
)

foreach ($file in $zaitullahFiles) {
    if (Test-Path $file) {
        $fileName = Split-Path $file -Leaf
        Move-Item $file "$quarantinePath\ZaitullahJan_Legal_Docs\$fileName" -Force
        Write-Host "Moved: $fileName" -ForegroundColor Green
    }
}

# Move EmpowerQNow713 assets
$empowerFiles = @(
    "5_Apps\dev\EmpowerQNow713\assets\html\chat.html",
    "5_Apps\dev\EmpowerQNow713\assets\json\conversations.json",
    "5_Apps\dev\EmpowerQNow713\assets\srv1.cody chatgpt export\chat.html",
    "5_Apps\dev\EmpowerQNow713\assets\srv1.cody chatgpt export\conversations.json",
    "5_Apps\dev\EmpowerQNow713\assets\trainingdata\pus.traineddata"
)

foreach ($file in $empowerFiles) {
    if (Test-Path $file) {
        $fileName = Split-Path $file -Leaf
        Move-Item $file "$quarantinePath\EmpowerQNow713_Assets\$fileName" -Force
        Write-Host "Moved: $fileName" -ForegroundColor Green
    }
}

# Move other large files
$otherFiles = @(
    "4_Clients\ZaitullahJan-OS\50_Legal\60_Immigration\50_Form_Filings\C.04-Exhibits\EX-B_Persecution-Threats-Conditions\zjk_09122025_C.00.00_Articles_v01.pdf",
    "4_Clients\ZaitullahJan-OS\50_Legal\60_Immigration\50_Form_Filings\C.04-Exhibits\EX-C_Government-Actions-Notices\zjk_EXC115_Uscischicago_v01.pdf",
    "4_Clients\ZaitullahJan-OS\50_Legal\60_Immigration\50_Form_Filings\C.04-Exhibits\EX-E_Community-Residence-Integration\zjk_EXE212_From_Afghan_Frontlines_To_Asylum_v01.m4a",
    "4_Clients\ZaitullahJan-OS\50_Legal\60_Immigration\90_Archive\10_Emails\zjk_NVCSIV2022250581_Attn_Bailey_CRM_0953846_v01_v01.eml"
)

foreach ($file in $otherFiles) {
    if (Test-Path $file) {
        $fileName = Split-Path $file -Leaf
        Move-Item $file "$quarantinePath\Other_Large_Files\$fileName" -Force
        Write-Host "Moved: $fileName" -ForegroundColor Green
    }
}

Write-Host ""
Write-Host "✅ Large files moved to quarantine!" -ForegroundColor Green
Write-Host "📁 Location: $quarantinePath" -ForegroundColor Blue
Write-Host ""
Write-Host "📋 Next steps:" -ForegroundColor Cyan
Write-Host "1. Upload QUARANTINE_LARGE_FILES folder to Google Drive" -ForegroundColor White
Write-Host "2. Add .gitignore rules to prevent these files from being tracked" -ForegroundColor White
Write-Host "3. Push the cleaned repository" -ForegroundColor White
