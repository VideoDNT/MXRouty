# Nur fuer die Build-Umgebung unter Wine 9: KERNEL32.CopyFile2 fehlt dort.
# shutil/pathlib pruefen beim Import per hasattr und nehmen dann den
# normalen Kopierweg. Wird NICHT in die exe gepackt.
import _winapi
if hasattr(_winapi, "CopyFile2"):
    del _winapi.CopyFile2
