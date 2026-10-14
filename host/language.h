#ifndef HOST_LANGUAGE_H
#define HOST_LANGUAGE_H
#include <SDL3/SDL.h>
#ifdef __cplusplus
extern "C" {
#endif

/* Fixed for this process; F1 changes the saved setting for the next start. */
void Host_LanguageInit(const Uint8 (*original_hashes)[32], const Uint8 exe_hash[32]);
int Host_LanguageActive(void);
int Host_LanguageAvailable(void);
const char *Host_LanguageError(void);
/* Immutable translated data, or NULL when English/no override is active. */
const Uint8 *Host_LanguageFile(int id, size_t *size);

#ifdef __cplusplus
}
#endif
#endif
