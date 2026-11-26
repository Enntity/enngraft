# Works on my machine

A photo lab uses Darkroom to turn RGB digital negatives into positive prints. Its original pixel routine uses x86 SSE2 instructions. This purpose-built compatibility demo uses the same source files and the same image on x86-64 Linux and an Apple-silicon Mac.

On x86-64 Linux with a C compiler and Make installed, run this from the repository root. It builds the original program, runs it on the compressed sample, and checks every output byte against an independent implementation.

```sh
python3 docs/field-trials/darkroom/reference.py /tmp/darkroom-print
```

The test image is a 769 × 769 digital negative we made from the published NASA photograph. The sample is separate from the program source and install-time checks. Photo credit: NASA / Bill Anders. [Apollo 8’s Iconic Earthrise](https://science.nasa.gov/resource/apollo-8s-iconic-earthrise/)
