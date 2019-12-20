# Use release 0 for prerelease version.
%define release 1
%define version 2017.2
%define buildid %{nil}
%define venv %{buildroot}/opt/inmanta
%define _p3 %{venv}/bin/python3
%define _unique_build_ids 0
%define _debugsource_packages 0
%define _debuginfo_subpackages 0
%define _enable_debug_packages 0
%define debug_package %{nil}


%define sourceversion %{version}%{?buildid}

Name:           python3-inmanta
Version:        %{version}

Release:        %{release}%{?buildid}%{?tag}%{?dist}
Summary:        Inmanta automation and orchestration tool

Group:          Development/Languages
License:        ASL 2
URL:            http://inmanta.com
Source0:        inmanta-%{sourceversion}.tar.gz
Source1:        deps-%{sourceversion}.tar.gz
Source2:        inmanta-dashboard.tar.gz
BuildRoot:      %{_tmppath}/%{name}-%{version}-%{release}-root-%(%{__id_u} -n)

BuildRequires:  systemd
BuildRequires:  sed
BuildRequires:  libffi-devel
BuildRequires:  openssl-devel

Requires:       git
Requires:       gcc
Requires:       openssl
Requires:       logrotate
Requires:       libffi
Requires(pre):  shadow-utils

%if 0%{?rhel}
BuildRequires:  python36-devel
Requires:       python36
Requires:       python36-devel
%define __python3 /usr/bin/python3
%else
%if 0%{?fedora} >= 29
BuildRequires:  gcc
BuildRequires:  python36
BuildRequires:  python3-devel
Requires:       python36
Requires:       python3-devel
%define __python3 /usr/bin/python3.6
%else
BuildRequires:  python3-devel
Requires:       python3
Requires:       python3-devel
%endif
%endif

%package server
Summary:        The configuration and service files to start the Inmanta server
Requires:       python3-inmanta

%package agent
Summary:        The configuration and service files to start the Inmanta agent
Requires:       python3-inmanta

%description

%description server

%description agent

%prep
%setup -q -n inmanta-%{sourceversion}
%setup -T -D -a 1 -n inmanta-%{sourceversion}
%setup -T -D -a 2 -n inmanta-%{sourceversion}

%build

%install
rm -rf %{buildroot}
mkdir -p %{buildroot}/opt/inmanta
%{__python3} -m venv --symlinks %{venv}
%{_p3} -m pip install -U --no-index --find-links deps-%{sourceversion} wheel setuptools pip
%{_p3} -m pip install --no-index --find-links deps-%{sourceversion} inmanta
%{_p3} -m inmanta.app

# Use the correct python for bycompiling
%define __python %{_p3}

# Fix shebang
find %{venv}/bin/ -type f | xargs sed -i "s|%{buildroot}||g"
find %{venv} -name RECORD | xargs sed -i "s|%{buildroot}||g"

# Put symlinks
mkdir -p %{buildroot}%{_bindir}
ln -s /opt/inmanta/bin/inmanta %{buildroot}%{_bindir}/inmanta
ln -s /opt/inmanta/bin/inmanta-cli %{buildroot}%{_bindir}/inmanta-cli

# Additional dirs and config
chmod -x LICENSE
mkdir -p %{buildroot}%{_localstatedir}/lib/inmanta
mkdir -p %{buildroot}/etc/inmanta
mkdir -p %{buildroot}/etc/inmanta/inmanta.d
mkdir -p %{buildroot}/var/log/inmanta
mkdir -p %{buildroot}/etc/logrotate.d
install -p -m 644 misc/inmanta.cfg %{buildroot}/etc/inmanta/inmanta.cfg
install -p -m 644 misc/logrotation_config %{buildroot}/etc/logrotate.d/inmanta

# Setup systemd
mkdir -p %{buildroot}%{_unitdir}
install -p -m 644 misc/inmanta-agent.service $RPM_BUILD_ROOT%{_unitdir}/inmanta-agent.service
install -p -m 644 misc/inmanta-server.service $RPM_BUILD_ROOT%{_unitdir}/inmanta-server.service
mkdir -p %{buildroot}/etc/sysconfig
touch %{buildroot}/etc/sysconfig/inmanta-server
touch %{buildroot}/etc/sysconfig/inmanta-agent

# Install the dashboard
cp -a dist %{venv}/dashboard

%clean
rm -rf %{buildroot}

%files
%defattr(-,root,root,-)
%doc LICENSE docs/*
/opt/inmanta/bin
/opt/inmanta/lib
/opt/inmanta/lib64
/opt/inmanta/include
/opt/inmanta/pyvenv.cfg
%{_bindir}/inmanta
%{_bindir}/inmanta-cli
%attr(-, inmanta, inmanta) %{_localstatedir}/lib/inmanta
%attr(-, inmanta, inmanta) /var/log/inmanta
%config %attr(-, root, root)/etc/inmanta
%config(noreplace) %attr(-, root, root)/etc/inmanta/inmanta.cfg
%config %attr(-, root, root)/etc/inmanta/inmanta.d
%config(noreplace) %attr(-, root, root)/etc/logrotate.d/inmanta
%config(noreplace) %attr(-, root, root)/etc/sysconfig/inmanta-server
%config(noreplace) %attr(-, root, root)/etc/sysconfig/inmanta-agent

%files server
/opt/inmanta/dashboard
%attr(-,root,root) %{_unitdir}/inmanta-server.service

%files agent
%attr(-,root,root) %{_unitdir}/inmanta-agent.service

%post agent
%systemd_post inmanta-agent.service

%preun agent
%systemd_preun inmanta-agent.service

%postun agent
%systemd_postun_with_restart inmanta-agent.service

%post server
%systemd_post inmanta-server.service

# Move server.cfg file for backward compatibility
if [ -e "/etc/inmanta/server.cfg" ]; then
  mv /etc/inmanta/server.cfg /etc/inmanta/inmanta.d/
fi

%preun server
%systemd_preun inmanta-server.service

%postun server
%systemd_postun_with_restart inmanta-server.service

%pre
getent group inmanta >/dev/null || groupadd -r inmanta
getent passwd inmanta >/dev/null || \
    useradd -r -g inmanta -d /var/lib/inmanta -s /bin/bash \
    -c "Account used by the Inmanta daemons" inmanta
exit

%changelog
* Mon May 30 2016 Bart Vanbrabant <bart.vanbrabant@inmanta.com> - 2016.3
- Rename to Inmanta

* Thu Jan 08 2015 Bart Vanbrabant <bart.vanbrabant@inmanta.com> - 0.1
- Initial release

