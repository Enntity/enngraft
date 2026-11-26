#include <ctype.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

void invert(unsigned char *samples, size_t count);

static int pixel(char **args) {
    unsigned char rgb[3];
    for (int i = 0; i < 3; ++i) {
        char *end;
        long n = strtol(args[i], &end, 10);
        if (end == args[i] || *end || n < 0 || n > 255) return 2;
        rgb[i] = (unsigned char)n;
    }
    invert(rgb, sizeof(rgb));
    printf("%u %u %u\n", (unsigned)rgb[0], (unsigned)rgb[1], (unsigned)rgb[2]);
    return 0;
}

int main(int argc, char **argv) {
    if (argc == 5 && strcmp(argv[1], "--pixel") == 0) return pixel(argv + 2);
    if (argc != 3) {
        fputs("Usage: darkroom negative.ppm print.ppm\n", stderr);
        return 2;
    }
    FILE *in = fopen(argv[1], "rb");
    if (!in) { perror(argv[1]); return 1; }
    int w, h, max;
    if (fscanf(in, "P6%d%d%d", &w, &h, &max) != 3 ||
        w < 1 || h < 1 || w > 8192 || h > 8192 || max != 255 || !isspace(fgetc(in))) {
        fputs("Expected an 8-bit binary PPM image\n", stderr);
        fclose(in);
        return 1;
    }
    size_t size = (size_t)w * h * 3;
    unsigned char *image = malloc(size);
    if (!image || fread(image, 1, size, in) != size) {
        fputs("Could not read complete image\n", stderr);
        fclose(in); free(image); return 1;
    }
    fclose(in);
    invert(image, size);
    FILE *out = fopen(argv[2], "wb");
    if (!out) { perror(argv[2]); free(image); return 1; }
    int ok = fprintf(out, "P6\n%d %d\n255\n", w, h) > 0 && fwrite(image, 1, size, out) == size;
    free(image);
    if (fclose(out) || !ok) { fputs("Could not write print\n", stderr); return 1; }
    printf("Developed %d x %d pixels.\n", w, h);
    return 0;
}
