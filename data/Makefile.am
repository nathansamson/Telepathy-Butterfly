EXTRA_DIST = butterfly.service.in butterfly.manager

managerdir = $(datadir)/telepathy/managers
manager_DATA = butterfly.manager

servicedir = $(datadir)/dbus-1/services
service_DATA = org.freedesktop.Telepathy.ConnectionManager.butterfly.service

# We don't use the full filename for the .in because > 99 character filenames
# in tarballs are non-portable (and automake 1.8 doesn't let us build
# non-archaic tarballs)
org.freedesktop.Telepathy.ConnectionManager.butterfly.service: butterfly.service.in \
		Makefile
	$(AM_V_GEN)sed -e "s|[@]libexecdir[@]|$(libexecdir)|" $< > $@

CLEANFILES = $(service_DATA)
