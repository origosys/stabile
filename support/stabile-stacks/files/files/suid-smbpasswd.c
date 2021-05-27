#include <unistd.h>
#include <stdio.h>
#include <errno.h>

int main( int argc, char * argv[], char ** envp )
{
      if( setgid(getegid()) ) perror( "setgid" );
      if( setuid(geteuid()) ) perror( "setuid" );

/*      char cmdLine[4096];
      sprintf(cmdLine, "/opt/samba4/bin/smbpasswd %s %s %s %s", argv[1], argv[2], argv[3], argv[4]);
      system(cmdLine); */

      argv[0] = "/usr/bin/smbpasswd";
      execv( argv[0], argv );

      /* blocks IFS attack on non-bash shells */
/*      envp = 0;
      system( "/opt/samba4/bin/smbpasswd", argv, envp ); */

      perror( argv[0] );
      return errno;
}

/* gcc -o suid-smbpasswd suid-smbpasswd.c ; chmod 6755 suid-smbpasswd */
