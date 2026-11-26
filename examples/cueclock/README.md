# Cueclock

Run `sh build.sh` to install the `cueclock` executable in this directory. A subtitle editor uses it to shift an SRT timestamp by a signed number of milliseconds.

```console
$ cueclock 00:00:59,900 250
00:01:00,150
```

The output retains SRT formatting, including the three millisecond digits. Carry across seconds, minutes and hours. Clamp negative times at zero.
