-*- mode: m4 -*-
AC_PREREQ(2.59c)

dnl If not 1, append datestamp to the version number
m4_define(telepathy_butterfly_released, 1)
dnl The telepathy-python version number (must actually be numeric at the moment)
m4_define(telepathy_butterfly_major_version, 0)
m4_define(telepathy_butterfly_minor_version, 5)
m4_define(telepathy_butterfly_micro_version, 8)

m4_define(telepathy_butterfly_maybe_datestamp,
          m4_esyscmd([if test x]telepathy_butterfly_released[ != x1; then date +.%Y%m%d | tr -d '\n\r'; fi]))

m4_define(telepathy_butterfly_version, telepathy_butterfly_major_version.telepathy_butterfly_minor_version.telepathy_butterfly_micro_version[]telepathy_butterfly_maybe_datestamp)

AC_INIT(telepathy-butterfly, telepathy_butterfly_version,
        [http://bugs.freedesktop.org/enter_bug.cgi?product=Telepathy&component=butterfly])
AM_INIT_AUTOMAKE

m4_ifdef([AM_SILENT_RULES], [AM_SILENT_RULES])

AM_PATH_PYTHON(2.4.0)

AC_CONFIG_FILES(
  Makefile
  butterfly/Makefile
  butterfly/channel/Makefile
  butterfly/util/Makefile
  butterfly/media/Makefile
  data/Makefile)
AC_OUTPUT
