#include <windows.h>
#include <stdio.h>
#include <string.h>

/* Print the running machine architecture or the byte length of an argument. */
int main(int argc, char **argv) {
    if (argc == 2 && strcmp(argv[1], "--arch") == 0) {
        SYSTEM_INFO sys;
        GetNativeSystemInfo(&sys);
        puts(sys.wProcessorArchitecture == PROCESSOR_ARCHITECTURE_AMD64 ? "x86_64" : "unknown");
        return 0;
    }
    if (argc == 3 && strcmp(argv[1], "--bytes") == 0) {
        printf("%zu\n", strlen(argv[2]));
        return 0;
    }
    fprintf(stderr, "usage: hoststamp --arch | --bytes TEXT\n");
    return 2;
}
