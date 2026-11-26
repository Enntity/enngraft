# A clean QOA checkout on Apple Silicon

The converter for Dominic Szablewski's Quite OK Audio format once enabled optional MP3 and FLAC input by default. The headers for those formats were distributed separately. A user reported a build failure after downloading GitHub HTML pages in place of the headers. The maintainer explained the optional flags and subsequently made both decoders opt-in. We tested the clean revision immediately before that change. [Upstream issue #73](https://github.com/phoboslab/qoa/issues/73) · [Upstream fix](https://github.com/phoboslab/qoa/commit/fb57da0a3638751cfb325039a7950ea5cf0583ea)

On the untouched checkout, `make conv` failed at `dr_mp3.h`. The released Enngraft CLI read the Makefile and C sources, probed the Mac and requested a plan from DeepSeek through LLooM. With no project manifest or operator-supplied build instructions, it selected the converter target and supplied these flags.

```sh
make conv 'CFLAGS_CONV=-std=c99 -O3' 'LFLAGS_CONV=-lm'
```

That command builds the upstream WAV/QOA converter with the MP3 and FLAC input paths disabled. The standalone player is a separate target. The installation completed in 64.89 seconds in this single run. The source tree was clean before and after. The receipt records zero source edits. The adaptation happened in the build recipe.

## Watch the terminal session

We ran the released CLI again to record the film. The first take timed out waiting for DeepSeek after 90 seconds. On the second take, `enngraft .` finished in 89 seconds. This time the model selected `make qoaconv 'CFLAGS_CONV=-std=c99 -O3'`. The checkout stayed clean. The installed converter produced the same QOA file as the first field trial, byte for byte.

The film shortens the wait. The full terminal recordings preserve the original timing and output, including the install receipt. A script typed the commands into an interactive shell. To replay either recording locally, download the file and run `asciinema play` with its filename. [Film](../../enngraft-demos.mp4) · [Successful take](terminal.cast) · [Timed-out take](terminal-timeout.cast)

## Repeat the installation

Start on a Mac with Command Line Tools, Enngraft installed, and a configured model endpoint. The model can choose a different recipe on a subsequent run.

```sh
git clone https://github.com/phoboslab/qoa.git
cd qoa
git checkout --detach 52ed2d1c748e7cce7f26bdea80461049e0aa2f9f
git status --porcelain
make conv  # reproduces the missing-header failure
enngraft .
git status --porcelain
```

## Hear what the converter produced

The model-generated acceptance checks exercised usage and error paths. To independently test the actual audio path, we composed a stereo PCM score called *Signal Garden*, encoded it using the installed `qoaconv`, and used the same installed binary to decode it. FFmpeg independently decoded the QOA file. Both decoders produced identical PCM across 2,574,142 stereo frames at 44.1 kHz. QOA is lossy. The measured signal-to-noise ratio against the original PCM was 37.88 dB. The film uses the round-tripped score underneath the narration.

| Artifact | Bytes |
| --- | ---: |
| Original 16-bit stereo WAV | 10,296,612 |
| Encoded QOA | 2,079,456 |
| Decoded stereo WAV | 10,296,612 |

To verify the published QOA with your installation, set `QOACONV` to the executable path printed by Enngraft. Run the following from the directory containing the downloaded score. Comparing raw PCM avoids differences in WAV metadata.

```sh
"$QOACONV" signal-garden.qoa decoded.wav
ffmpeg -v error -i decoded.wav -f s16le qoaconv.pcm
ffmpeg -v error -i signal-garden.qoa -f s16le ffmpeg.pcm
cmp qoaconv.pcm ffmpeg.pcm
```

[Encoded score](signal-garden.qoa) · [Run receipt, sizes and hashes](evidence.json) · [Film](../../enngraft-demos.mp4)

*Signal Garden* is an original instrumental composed for this demonstration. The film uses Enntity's Living Software artwork and the Enntity Labs lockup from the SparkScore films. Narration was synthesized with Kokoro. The QOA project and its upstream fix are the work of their respective maintainers.
