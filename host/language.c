#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <SDL3/SDL.h>
#include "host/host.h"
#include "host/host_sdl.h"
#include "host/language.h"
#include "host/settings.h"
#include "host/sha256.h"

typedef struct {
    Uint32 id;
    Uint32 size;
    Uint8 original_sha[32];
    Uint8 translated_sha[32];
} LanguageExpected;
#include "host/language_es_manifest.inc"

static Uint8 *bundle;
static const Uint8 *translated[PAK_FILES];
static size_t translated_size[PAK_FILES];
static int available;
static int active;
static char error[160];

static Uint32 read32(const Uint8 *p) {
    return (Uint32)p[0] | (Uint32)p[1] << 8 | (Uint32)p[2] << 16 | (Uint32)p[3] << 24;
}
static Uint64 read64(const Uint8 *p) { return read32(p) | (Uint64)read32(p + 4) << 32; }

static void cleanup(void) {
    SDL_free(bundle);
    bundle = NULL;
}

static int load_bundle(const char *path, const Uint8 (*original_hashes)[32], const Uint8 exe_hash[32]) {
    const size_t count = sizeof(language_expected) / sizeof(language_expected[0]);
    size_t expected_size = 64 + count * 16;
    size_t cursor = expected_size;
    SDL_IOStream *io;
    for (size_t i = 0; i < count; i++) expected_size += language_expected[i].size;
    io = SDL_IOFromFile(path, "rb");
    if (io == NULL) { SDL_strlcpy(error, "Missing languages/es.langpak", sizeof(error)); return 0; }
    if (SDL_GetIOSize(io) != (Sint64)expected_size) {
        SDL_strlcpy(error, "Spanish package size mismatch", sizeof(error)); SDL_CloseIO(io); return 0;
    }
    bundle = SDL_malloc(expected_size);
    if (bundle == NULL || SDL_ReadIO(io, bundle, expected_size) != expected_size) {
        SDL_strlcpy(error, "Cannot read Spanish package", sizeof(error));
        SDL_CloseIO(io); cleanup(); return 0;
    }
    SDL_CloseIO(io);
    if (memcmp(bundle, "DW2ESPK\0", 8) != 0 || read32(bundle + 8) != 1 || read32(bundle + 12) != count ||
        read64(bundle + 16) != expected_size || read64(bundle + 56) != 0 ||
        memcmp(bundle + 24, exe_hash, 32) != 0 || memcmp(exe_hash, language_base_exe_sha, 32) != 0) {
        SDL_strlcpy(error, "Unsupported Spanish package header/base game", sizeof(error)); cleanup(); return 0;
    }
    for (size_t i = 0; i < count; i++) {
        const LanguageExpected *expected = &language_expected[i];
        const Uint8 *entry = bundle + 64 + i * 16;
        Sha256 hash;
        Uint8 digest[32];
        if (expected->id >= PAK_FILES || read32(entry) != expected->id || read32(entry + 4) != expected->size ||
            read64(entry + 8) != cursor || expected->size % 2048 != 0 ||
            cursor > expected_size || expected->size > expected_size - cursor ||
            memcmp(original_hashes[expected->id], expected->original_sha, 32) != 0) {
            SDL_strlcpy(error, "Spanish package resource index/base mismatch", sizeof(error)); cleanup(); return 0;
        }
        Sha256_Init(&hash);
        Sha256_Update(&hash, bundle + cursor, expected->size);
        Sha256_Final(&hash, digest);
        if (memcmp(digest, expected->translated_sha, 32) != 0) {
            snprintf(error, sizeof(error), "Spanish resource %u checksum mismatch", expected->id); cleanup(); return 0;
        }
        cursor += expected->size;
    }
    for (size_t i = 0; i < count; i++) {
        Uint32 id = language_expected[i].id;
        translated[id] = bundle + read64(bundle + 64 + i * 16 + 8);
        translated_size[id] = language_expected[i].size;
    }
    return 1;
}

void Host_LanguageInit(const Uint8 (*original_hashes)[32], const Uint8 exe_hash[32]) {
    const char *base = SDL_GetBasePath();
    char *path;
    int requested = Settings_Get(SET_LANGUAGE);
    if (base == NULL) base = "";
    path = SDL_malloc(strlen(base) + sizeof("languages/es.langpak"));
    if (path == NULL) { SDL_strlcpy(error, "Cannot allocate language path", sizeof(error)); return; }
    snprintf(path, strlen(base) + sizeof("languages/es.langpak"), "%slanguages/es.langpak", base);
    available = load_bundle(path, original_hashes, exe_hash);
    SDL_free(path);
    active = requested == SET_LANGUAGE_ES && available ? SET_LANGUAGE_ES : SET_LANGUAGE_EN;
    if (bundle != NULL) atexit(cleanup);
    if (!available && requested == SET_LANGUAGE_ES) printf("[language] %s; falling back to English\n", error);
    printf("[language] active=%s; Spanish package %s (%zu resources)\n",
           active == SET_LANGUAGE_ES ? "es" : "en", available ? "verified" : "unavailable",
           available ? sizeof(language_expected) / sizeof(language_expected[0]) : 0);
}

int Host_LanguageActive(void) { return active; }
int Host_LanguageAvailable(void) { return available; }
const char *Host_LanguageError(void) { return error; }
const Uint8 *Host_LanguageFile(int id, size_t *size) {
    *size = 0;
    if (active != SET_LANGUAGE_ES || id < 0 || id >= PAK_FILES || translated[id] == NULL) return NULL;
    *size = translated_size[id];
    return translated[id];
}
