/* Заглушки newlib — нужны для линковки с -specs=nosys.specs.
   В этом проекте ввод/вывод идёт через middleware/logger, не через stdio. */

#include <sys/stat.h>
#include <errno.h>
#include <stdint.h>

int  _close(int fd)                                { (void)fd; return -1; }
int  _fstat(int fd, struct stat *st)               { (void)fd; (void)st; return 0; }
int  _isatty(int fd)                               { (void)fd; return 1; }
int  _lseek(int fd, int off, int whence)           { (void)fd; (void)off; (void)whence; return 0; }
int  _read(int fd, char *buf, int len)             { (void)fd; (void)buf; (void)len; return 0; }
int  _write(int fd, const char *buf, int len)      { (void)fd; (void)buf; return len; }
void _exit(int rc)                                 { (void)rc; while (1) {} }
int  _getpid(void)                                 { return 1; }
int  _kill(int pid, int sig)                       { (void)pid; (void)sig; errno = EINVAL; return -1; }