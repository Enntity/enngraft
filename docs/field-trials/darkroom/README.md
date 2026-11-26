# Works on my machine

A photo lab uses Darkroom to turn RGB digital negatives into positive prints. Its original pixel routine uses x86 SSE2 instructions. This purpose-built compatibility demo uses the same source files and the same image on x86-64 Linux and an Apple-silicon Mac.

[Watch the film](darkroom.mp4), narrated by Jinx with music from Enntity’s original score, *Signal Garden*. The Mac footage comes from a real terminal recording with the model wait shortened. The finished prints shown in the comparison come from the three executables.

| Target | What happened | Evidence |
| --- | --- | --- |
| x86-64 Linux, GitHub-hosted runner | The original build developed the negative. | [Build log](x86-linux.txt) · [CI and original print artifact](https://github.com/Enntity/enngraft/actions/runs/45863971977) |
| Apple-silicon Mac, native | The original build failed. Enngraft’s first candidate still targeted x86 and failed its run checks. Enngraft then removed the forced architecture flags and rewrote the inversion loop in portable C. The resulting Mach-O executable is ARM64. | [Terminal recording](mac.cast) · [Local source changes](mac.patch) |
| ARM64 Linux, Docker on the same Mac | Enngraft independently replaced the x86 routine after the compiler rejected it. It installed a Linux ARM64 ELF executable. | [Terminal recording](arm-linux.cast) · [Local source changes](arm-linux.patch) |

The lab supplied the source and two worked pixel examples in its README. Enngraft inferred the build, tested the candidates and selected the passing local releases. Both source directories remained byte-identical to the fixture. Each executable then developed the photograph, which was outside the project inventory during installation. All three files matched the independent reference byte for byte. [Hashes and repair evidence](evidence.json)

## Reproduce it

On x86-64 Linux with a C compiler and Make installed, run this from the repository root. It builds the original program, runs it on the compressed sample, and checks every output byte against an independent implementation.

```sh
python3 docs/field-trials/darkroom/reference.py /tmp/darkroom-print
```

The test image is a 769 × 769 digital negative we made from the published NASA photograph. The sample is separate from the program source and install-time checks. Photo credit: NASA / Bill Anders. [Apollo 8’s Iconic Earthrise](https://science.nasa.gov/resource/apollo-8s-iconic-earthrise/)

For the Mac run, install Enngraft, configure your model endpoint and start from the repo root. The public fixture intentionally retains the x86-only implementation for the baseline.

```sh
gzip -dc docs/field-trials/darkroom/negative.ppm.gz > /tmp/darkroom-negative.ppm
cd examples/darkroom
make  # reproduces the ARM compiler error
enngraft .
~/.local/share/enngraft/darkroom/current/darkroom /tmp/darkroom-negative.ppm /tmp/darkroom-mac.ppm
shasum -a 256 /tmp/darkroom-mac.ppm
```

For ARM Linux, use an ARM64 Docker image containing Make and a C compiler. In a fresh working directory, unpack the negative as `negative.ppm`, set `GRAFT_IMAGE` to your local image and run `enngraft /path/to/examples/darkroom`. Copy the printed Docker command and append `negative.ppm print.ppm`. The recorded trials used a 300-second model response timeout.
