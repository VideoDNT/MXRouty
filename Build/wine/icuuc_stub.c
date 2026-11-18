/* Nur fuer die Build-Umgebung unter Wine: Qt6Core.dll importiert 20
   ucnv_*-Funktionen aus der Windows-System-ICU (icuuc.dll), die Wine nicht
   mitbringt. Echte Windows-Rechner (ab Win10 1903) haben die DLL selbst;
   dieser Stub landet NICHT im Paket. */
#define U_UNSUPPORTED_ERROR 16
#define EXP __declspec(dllexport)
EXP void *ucnv_open(const char *name, int *err) { if (err) *err = U_UNSUPPORTED_ERROR; return 0; }
EXP int ucnv_countAvailable(void) { return 0; }
EXP const char *ucnv_getAvailableName(int n) { (void)n; return 0; }
EXP const char *ucnv_getStandardName(const char *n, const char *s, int *err) { (void)n; (void)s; if (err) *err = U_UNSUPPORTED_ERROR; return 0; }
EXP const char *ucnv_getName(void *c, int *err) { (void)c; if (err) *err = U_UNSUPPORTED_ERROR; return 0; }
EXP void ucnv_close(void *c) { (void)c; }
EXP void ucnv_reset(void *c) { (void)c; }
EXP int ucnv_getMaxCharSize(void *c) { (void)c; return 1; }
EXP int ucnv_fromUCountPending(void *c, int *err) { (void)c; if (err) *err = U_UNSUPPORTED_ERROR; return 0; }
EXP int ucnv_toUCountPending(void *c, int *err) { (void)c; if (err) *err = U_UNSUPPORTED_ERROR; return 0; }
EXP void ucnv_fromUnicode(void) {}
EXP void ucnv_toUnicode(void) {}
EXP void ucnv_setFromUCallBack(void) {}
EXP void ucnv_setToUCallBack(void) {}
EXP void ucnv_getFromUCallBack(void) {}
EXP void ucnv_getToUCallBack(void) {}
EXP void ucnv_cbFromUWriteUChars(void) {}
EXP void ucnv_cbToUWriteUChars(void) {}
EXP void UCNV_FROM_U_CALLBACK_SUBSTITUTE(void) {}
EXP void UCNV_TO_U_CALLBACK_SUBSTITUTE(void) {}
