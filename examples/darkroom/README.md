# Darkroom

This small photo lab demonstration tool turns an 8-bit RGB digital negative into a positive print. The lab's original build uses x86 SSE2. Build it with `make`, then run `./darkroom negative.ppm print.ppm`. It reads binary P6 PPM with a simple header and writes the same dimensions.

Each output channel is 255 minus the corresponding input channel. The same conversion is available for one pixel.

```console
$ darkroom --pixel 0 127 255
255 128 0
$ darkroom --pixel 239 70 8
16 185 247
```
