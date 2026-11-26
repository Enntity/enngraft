# hoststamp

Build with `sh build.sh`. The resulting `hoststamp` executable accepts two commands.

- `hoststamp --arch` prints the machine architecture reported by the current system, followed by a newline.
- `hoststamp --bytes TEXT` prints the byte length of TEXT followed by a newline. For example, `hoststamp --bytes hello` prints `5`. Empty input prints `0`.

Invalid arguments produce a usage message on stderr and exit with status 2.

```console
$ hoststamp --bytes hello
5
```
